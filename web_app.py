from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from namma.config import (
    FULL_ASSISTANT_LANGUAGES, GNANI_AUTO_DETECT_ENABLED, GNANI_STT_MODEL,
    LANGUAGES, LANGUAGE_CODE_MAP, PROJECT_ROOT, get_gnani_api_key,
    get_gnani_key_source,
)
from namma.language_utils import detect_script_language, normalize_language_code
from namma.translation_service import TranslationServiceError, translate_text, translation_is_configured
from namma.gnani_client import GnaniAPIError, synthesize_speech_detailed, transcribe_audio
from namma.market_service import MarketDataError, save_mandi_csv, default_mandi_csv_path, mandi_api_is_configured
from namma.storage import get_farmer_profile, init_db, list_tickets, save_farmer_profile
from namma.voice_assistant import handle_turn

load_dotenv(PROJECT_ROOT / ".env", override=False, encoding="utf-8-sig")
init_db()

app = FastAPI(title="NammaVaani Farm Companion", version="4.0.0")
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")

SESSIONS: dict[str, dict[str, Any]] = {}
LANG_MAP = {code: (name, name) for code, name in LANGUAGE_CODE_MAP.items()}
BETA_LANGUAGE_MESSAGES = {
    "bn": "আপনার ভাষা শনাক্ত করেছি। এখন NammaVaani-এর সম্পূর্ণ কৃষি-সংক্রান্ত কথোপকথন কন্নড়, তেলুগু ও ইংরেজিতে উপলভ্য। অনুগ্রহ করে এই ভাষাগুলোর একটি বেছে নিন।",
    "gu": "તમારી ભાષા ઓળખાઈ છે. હાલમાં NammaVaani ની સંપૂર્ણ ખેતી સંબંધિત વાતચીત કન્નડ, તેલુગુ અને અંગ્રેજીમાં ઉપલબ્ધ છે. કૃપા કરીને આમાંથી એક ભાષા પસંદ કરો.",
    "hi": "मैंने आपकी भाषा पहचान ली है। इस समय NammaVaani की पूरी खेती संबंधी बातचीत कन्नड़, तेलुगु और अंग्रेज़ी में उपलब्ध है। कृपया इनमें से एक भाषा चुनें।",
    "ml": "നിങ്ങളുടെ ഭാഷ തിരിച്ചറിഞ്ഞു. ഇപ്പോൾ NammaVaaniയുടെ പൂർണ്ണ കാർഷിക സംഭാഷണങ്ങൾ കന്നഡ, തെലുങ്ക്, ഇംഗ്ലീഷ് ഭാഷകളിൽ മാത്രമാണ് ലഭ്യം. ദയവായി അവയിൽ ഒന്ന് തിരഞ്ഞെടുക്കുക.",
    "mr": "तुमची भाषा ओळखली आहे. सध्या NammaVaani मधील संपूर्ण शेतीविषयक संवाद कन्नड, तेलुगू आणि इंग्रजीमध्ये उपलब्ध आहेत. कृपया यापैकी एक भाषा निवडा.",
    "pa": "ਤੁਹਾਡੀ ਭਾਸ਼ਾ ਪਛਾਣ ਲਈ ਹੈ। ਇਸ ਵੇਲੇ NammaVaani ਦੀ ਪੂਰੀ ਖੇਤੀਬਾੜੀ ਗੱਲਬਾਤ ਕੰਨੜ, ਤੇਲਗੂ ਅਤੇ ਅੰਗਰੇਜ਼ੀ ਵਿੱਚ ਉਪਲਬਧ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਇਹਨਾਂ ਵਿੱਚੋਂ ਇੱਕ ਭਾਸ਼ਾ ਚੁਣੋ।",
    "ta": "உங்கள் மொழியை அடையாளம் கண்டுள்ளோம். தற்போது NammaVaani-யின் முழுமையான விவசாய உரையாடல்கள் கன்னடம், தெலுங்கு, ஆங்கிலத்தில் மட்டுமே கிடைக்கின்றன. அவற்றில் ஒன்றைத் தேர்ந்தெடுக்கவும்.",
}


class TextTurn(BaseModel):
    text: str
    language: str = "kn"
    session_id: str


class ProfileUpdate(BaseModel):
    # The location labels are farmer-entered names; GPS is optional and opt-in.
    location: str | None = None  # legacy field kept for older clients
    state: str | None = None
    district: str | None = None
    taluk: str | None = None
    hobli: str | None = None
    village: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    gps_consent: bool = False
    land_acres: float | None = None
    soil_type: str | None = None
    irrigation: str | None = None
    current_crop: str | None = None
    preferred_language: str | None = None


def session_for(session_id: str) -> dict[str, Any]:
    if not session_id or len(session_id) > 100:
        raise HTTPException(400, "Invalid session identifier.")
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {"flow": None, "history": []}
    return SESSIONS[session_id]


def _speech_language(code: str) -> tuple[str, dict[str, str] | None]:
    if code == "auto":
        return "Auto detect", None
    name = LANGUAGE_CODE_MAP.get(code, "Kannada")
    return name, LANGUAGES[name]


def _build_response(
    text: str,
    language: str,
    state: dict[str, Any],
    source: str,
    detected_language: str | None = None,
) -> dict[str, Any]:
    detected_code = normalize_language_code(detected_language)
    script_language = detect_script_language(text)
    if not detected_code:
        if language == "auto":
            detected_code = script_language
        elif script_language and script_language not in {"en", language}:
            # If the transcript visibly came back in another Indic script,
            # prefer that script for the reply instead of speaking the wrong language.
            detected_code = script_language
    input_language = detected_code or (language if language != "auto" else "en")
    if input_language not in LANGUAGE_CODE_MAP:
        input_language = "en"

    # Core workflows are directly localised in Kannada, Telugu and English.
    # Other languages can use the optional multilingual bridge: translate only
    # the user turn to English, run the same deterministic/data-backed service,
    # then translate the verified answer back before Timbre speaks it.
    reply_language = input_language
    support_status = "full"
    translator_used = False
    if input_language in FULL_ASSISTANT_LANGUAGES:
        result = handle_turn(text, input_language, state)
        answer = result.pop("answer", "")
    elif translation_is_configured():
        try:
            english_request = translate_text(text, LANG_MAP[input_language][0], "English")
            result = handle_turn(english_request, "en", state)
            answer = result.pop("answer", "")
            answer = translate_text(answer, "English", LANG_MAP[input_language][0])
            if result.get("letter_text"):
                result["letter_text"] = translate_text(
                    result["letter_text"], "English", LANG_MAP[input_language][0]
                )
            support_status = "translated"
            translator_used = True
        except TranslationServiceError:
            answer = BETA_LANGUAGE_MESSAGES.get(input_language) or (
                f"I recognised this as {LANG_MAP[input_language][0]}. Full farming conversations "
                "are currently available in Kannada, Telugu and English. Please choose one of these."
            )
            result = {"intent": "language_beta"}
            support_status = "speech-beta"
    else:
        # Give a short, honest beta notice in the detected language rather than
        # speaking English through a mismatched regional voice.
        answer = BETA_LANGUAGE_MESSAGES.get(input_language) or (
            f"I recognised this as {LANG_MAP[input_language][0]}. Full farming conversations "
            "are currently available in Kannada, Telugu and English. Please choose one of these."
        )
        result = {"intent": "language_beta"}
        support_status = "speech-beta"

    reply_name, reply_cfg = _speech_language(reply_language)
    detected_name = LANG_MAP.get(input_language, ("English (India)", "English"))[0]
    result_payload: dict[str, Any] = {
        "ok": True,
        "transcript": text,
        "answer": answer,
        "intent": result.pop("intent", "general"),
        "source": source,
        "gnani_stt": source.startswith("Gnani Prisma"),
        "gnani_tts": False,
        "selected_language": language,
        "detected_language": input_language,
        "detected_language_name": detected_name,
        "reply_language": reply_language,
        "reply_language_name": reply_name,
        "language_support": support_status,
        "translation_model_used": translator_used,
        **result,
    }
    api_key = get_gnani_api_key()
    if api_key and answer and reply_cfg:
        try:
            audio, tts_meta = synthesize_speech_detailed(
                answer, api_key, reply_cfg["tts"], reply_cfg["voice"]
            )
            result_payload["audio_base64"] = base64.b64encode(audio).decode("ascii")
            result_payload["audio_mime"] = tts_meta["content_type"] or "audio/wav"
            result_payload["gnani_tts"] = True
            result_payload["gnani_tts_model"] = tts_meta["model"]
            result_payload["gnani_tts_http_status"] = tts_meta["http_status"]
            result_payload["gnani_tts_audio_bytes"] = tts_meta["audio_bytes"]
        except GnaniAPIError as exc:
            result_payload["tts_error"] = str(exc)
    state.setdefault("history", []).append({
        "question": text,
        "answer": answer,
        "intent": result_payload["intent"],
        "source": source,
        "language": input_language,
    })
    state["history"] = state["history"][-30:]
    return result_payload


@app.get("/")
def home() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    csv_path = default_mandi_csv_path()
    return {
        "ok": True,
        "gnani_configured": bool(get_gnani_api_key()),
        "gnani_key_source": get_gnani_key_source(),
        "stt_endpoint": "https://api.vachana.ai/stt/v3",
        "tts_endpoint": "https://api.vachana.ai/api/v1/tts/inference",
        "tts_model": "timbre-v2.5",
        "mandi_csv_available": csv_path.exists(),
        "mandi_csv_name": csv_path.name if csv_path.exists() else None,
        "mandi_api_configured": mandi_api_is_configured(),
        "mandi_api_resource": "Current Daily Price of Various Commodities from Various Markets (Mandi)",
        "mandi_api_primary": True,
        "stt_model": GNANI_STT_MODEL,
        "auto_detect_enabled": GNANI_AUTO_DETECT_ENABLED,
        "translation_enabled": translation_is_configured(),
        "supported_speech_languages": [
            {"code": code, "name": name} for code, name in LANGUAGE_CODE_MAP.items()
        ],
        "full_assistant_languages": sorted(FULL_ASSISTANT_LANGUAGES),
        "mode": "LIVE VOICE" if get_gnani_api_key() else "TEXT DEMO — Gnani key not configured",
    }


@app.get("/api/profile")
def profile() -> dict[str, Any]:
    return get_farmer_profile()


@app.post("/api/profile")
def update_profile(payload: ProfileUpdate) -> dict[str, Any]:
    current = get_farmer_profile()
    updates = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
    current.update(updates)
    if current.get("land_acres") is not None and float(current["land_acres"]) < 0:
        raise HTTPException(400, "Land size cannot be negative.")
    consent = bool(current.get("gps_consent"))
    latitude, longitude = current.get("latitude"), current.get("longitude")
    if consent:
        if latitude is None or longitude is None:
            raise HTTPException(400, "Choose 'Use my location' to save GPS coordinates, or turn GPS consent off.")
        if not (-90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180):
            raise HTTPException(400, "The GPS coordinates are outside the valid range.")
    else:
        current["latitude"] = None
        current["longitude"] = None
    # Keep a complete geocoding string for weather while separately saving each
    # level for display and future local-service routing.
    location_parts = [
        current.get("village"), current.get("hobli"), current.get("taluk"),
        current.get("district"), current.get("state"), "India",
    ]
    hierarchy_location = ", ".join(dict.fromkeys(str(x).strip() for x in location_parts if str(x or "").strip()))
    if current.get("village") or current.get("taluk") or current.get("hobli") or current.get("district"):
        current["location"] = hierarchy_location
    elif updates.get("location"):
        current["location"] = updates["location"].strip()
    save_farmer_profile(current)
    return {"ok": True, "profile": current}


@app.post("/api/voice")
def voice_turn(
    file: UploadFile = File(...),
    language: str = Form("kn"),
    session_id: str = Form(...),
) -> JSONResponse:
    api_key = get_gnani_api_key()
    if not api_key:
        raise HTTPException(503, "Gnani API key is not configured. Typed testing is available; live speech is disabled.")
    if language == "auto" and not GNANI_AUTO_DETECT_ENABLED:
        raise HTTPException(400, "Automatic language detection needs GNANI_STT_MODEL=prisma-v3.0. With Prisma v2.5, please choose the language you are speaking.")
    if language != "auto" and language not in LANG_MAP:
        raise HTTPException(400, "Unsupported language selection.")
    _, cfg = _speech_language(language)
    audio_bytes = file.file.read(12 * 1024 * 1024 + 1)
    if not audio_bytes:
        raise HTTPException(400, "No audio was received.")
    if len(audio_bytes) > 12 * 1024 * 1024:
        raise HTTPException(413, "Recording is too large. Please record a shorter question.")
    try:
        stt_language = "indic-auto" if language == "auto" else cfg["stt"]
        stt_kwargs: dict[str, Any] = {"language_code": stt_language, "model": GNANI_STT_MODEL}
        if GNANI_STT_MODEL == "prisma-v3.0":
            stt_kwargs["output_format"] = "codemix"
        body = transcribe_audio(audio_bytes, "farmer-question.wav", api_key, **stt_kwargs)
    except (GnaniAPIError, ValueError) as exc:
        raise HTTPException(502, str(exc)) from exc
    transcript = str(body.get("transcript", "")).strip()
    detected = body.get("detected_language_code")
    if not detected and language == "auto":
        detected = detect_script_language(transcript)
    state = session_for(session_id)
    model_label = "Gnani Prisma v3.0" if GNANI_STT_MODEL == "prisma-v3.0" else "Gnani Prisma v2.5"
    payload = _build_response(transcript, language, state, model_label, detected_language=detected)
    payload["gnani_stt_http_status"] = body.get("_gnani_http_status")
    payload["gnani_stt_request_id"] = body.get("_gnani_request_id")
    payload["gnani_stt_model"] = body.get("_gnani_model") or model_label
    payload["gnani_stt_processing_time"] = body.get("_gnani_processing_time")
    payload["gnani_stt_end_to_end_latency"] = body.get("_gnani_end_to_end_latency")
    if body.get("detected_language_code"):
        payload["detected_language_source"] = "Prisma language detection"
    elif language == "auto" or payload.get("detected_language") != language:
        payload["detected_language_source"] = "transcript script estimate"
    else:
        payload["detected_language_source"] = "selected language"
    return JSONResponse(payload)


@app.post("/api/text")
def text_turn(payload: TextTurn) -> dict[str, Any]:
    if payload.language not in LANG_MAP and payload.language != "auto":
        raise HTTPException(400, "Unsupported language selection.")
    detected = detect_script_language(payload.text) if payload.language == "auto" else None
    effective = detected or ("en" if payload.language == "auto" else payload.language)
    state = session_for(payload.session_id)
    return _build_response(payload.text, effective, state, "Typed test — not speech recognition", detected_language=detected)


@app.post("/api/gnani/test-tts")
def test_gnani_tts(language: str = Form("kn")) -> JSONResponse:
    """Make one short, real Timbre request so a developer can verify API access."""
    api_key = get_gnani_api_key()
    if not api_key:
        raise HTTPException(503, "GNANI_API_KEY is not loaded by the FastAPI application.")
    if language not in LANGUAGES_BY_CODE:
        raise HTTPException(400, "Choose one supported language before testing Timbre.")
    cfg = LANGUAGES_BY_CODE[language]
    sample_text = {
        "kn": "ನಮಸ್ಕಾರ. ಇದು ನಮ್ಮವಾಣಿ ಧ್ವನಿ ಪರೀಕ್ಷೆ.",
        "te": "నమస్కారం. ఇది నమ్మవాణి వాయిస్ పరీక్ష.",
        "en": "Hello. This is a NammaVaani voice test.",
        "ta": "வணக்கம். இது நம்மவாணி குரல் சோதனை.",
        "hi": "नमस्ते। यह नम्मावाणी की आवाज़ की जाँच है।",
        "ml": "നമസ്കാരം. ഇത് നന്മവാണിയുടെ ശബ്ദ പരിശോധനയാണ്.",
        "mr": "नमस्कार. ही नम्मावाणी आवाज चाचणी आहे.",
        "bn": "নমস্কার। এটি নম্মাভানী কণ্ঠ পরীক্ষা।",
        "gu": "નમસ્તે. આ નમ્માવાણી અવાજ પરીક્ષણ છે.",
        "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ। ਇਹ ਨੰਮਾਵਾਣੀ ਦੀ ਆਵਾਜ਼ ਦੀ ਜਾਂਚ ਹੈ।",
    }[language]
    try:
        audio, meta = synthesize_speech_detailed(
            sample_text, api_key, cfg["tts"], cfg["voice"]
        )
    except GnaniAPIError as exc:
        raise HTTPException(502, f"Timbre API test failed: {exc}") from exc
    return JSONResponse({
        "ok": True,
        "gnani_tts": True,
        "model": meta["model"],
        "http_status": meta["http_status"],
        "audio_bytes": meta["audio_bytes"],
        "audio_mime": meta["content_type"] or "audio/wav",
        "audio_base64": base64.b64encode(audio).decode("ascii"),
        "language": language,
        "voice": meta["voice"],
        "message": "A real Timbre v2.5 request succeeded. This test may consume programme credits.",
    })


LANGUAGES_BY_CODE = {cfg["code"]: cfg for cfg in LANGUAGES.values()}


@app.get("/api/history")
def history(session_id: str) -> dict[str, Any]:
    state = session_for(session_id)
    return {"items": state.get("history", [])}


@app.post("/api/mandi-upload")
def upload_mandi(file: UploadFile = File(...)) -> dict[str, Any]:
    content = file.file.read(25 * 1024 * 1024 + 1)
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(413, "CSV file is larger than 25 MB.")
    try:
        path = save_mandi_csv(content)
    except MarketDataError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "file": path.name, "message": "Agmarknet CSV saved. Prices will be labelled with their actual observation dates."}


@app.get("/api/tickets")
def tickets() -> dict[str, Any]:
    return {"items": list_tickets()[:30]}


@app.post("/api/reset")
def reset_session(session_id: str = Form(...)) -> dict[str, Any]:
    SESSIONS[session_id] = {"flow": None, "history": []}
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=True)
