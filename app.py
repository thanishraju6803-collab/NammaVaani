from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

import pandas as pd
import streamlit as st

from namma.config import (
    LANGUAGES, PRIORITIES, STATUSES, get_gnani_api_key,
)
from namma.gnani_client import GnaniAPIError, transcribe_audio, synthesize_speech
from namma.pipeline import extract_fields, ticket_summary
from namma.storage import (
    create_ticket, get_farmer_profile, get_ticket, init_db, list_tickets,
    save_farmer_profile, update_ticket,
)
from namma.farm_data import crop_basket, zone_context, UASB_ZONE_V_SOURCE, UASB_PRACTICES_SOURCE
from namma.weather_service import get_weather_forecast, WeatherServiceError, weather_code_label
from namma.market_service import (
    load_mandi_prices, save_mandi_csv, default_mandi_csv_path, MarketDataError,
)
from namma.conversation import (
    classify_intent, crop_followup, crop_advisory_text, detect_commodity,
    localized, market_question, parse_irrigation, parse_soil, weather_question,
)

st.set_page_config(
    page_title="NammaVaani Farm Companion",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()

UI = {
    "kn": {
        "home": "ಮುಖಪುಟ", "farm": "ನನ್ನ ಜಮೀನು", "crop": "ಬೆಳೆ ಯೋಜನೆ", "weather": "ಹವಾಮಾನ", "market": "ಮಾರುಕಟ್ಟೆ ಬೆಲೆ",
        "repair": "ಯಂತ್ರ ದುರಸ್ತಿ", "health": "ಬೆಳೆ ಆರೋಗ್ಯ", "planner": "ದಿನನಿತ್ಯದ ಕೆಲಸ", "operator": "ಸೇವಾ ಸಿಬ್ಬಂದಿ", "settings": "ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
        "hero": "ನಿಮ್ಮ ಕೃಷಿ ಸಹಾಯಕ", "subtitle": "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ ಮಾತನಾಡಿ ಕೇಳಿ.",
        "voice_title": "ನಮ್ಮವಾಣಿಯೊಂದಿಗೆ ಮಾತನಾಡಿ", "voice_hint": "ಒಂದು ಚಿಕ್ಕ ಪ್ರಶ್ನೆಯನ್ನು ಮಾತನಾಡಿ. ಒಂದು ಬಾರಿ 30 ಸೆಕೆಂಡುಗಳಿಗಿಂತ ಕಡಿಮೆ ಇರಲಿ.",
        "speech_language": "ನೀವು ಮಾತನಾಡುವ ಭಾಷೆ", "consent": "ನನ್ನ ಧ್ವನಿಯನ್ನು ಗುರುತಿಸಲು Gnani API ಗೆ ಕಳುಹಿಸಲು ಒಪ್ಪುತ್ತೇನೆ.",
        "send_voice": "🎤 ಮಾತನಾಡಿದ ಪ್ರಶ್ನೆಯನ್ನು ಕಳುಹಿಸಿ", "audio_missing": "ಮೊದಲು ಧ್ವನಿ ರೆಕಾರ್ಡ್ ಮಾಡಿ.",
        "typed_demo": "ಪರೀಕ್ಷೆಗೆ ಬರಹದ ಪ್ರಶ್ನೆ (ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆ ಅಲ್ಲ)", "typed_placeholder": "ಉದಾ: ಈ ಸೀಸನ್‌ನಲ್ಲಿ ಯಾವ ಬೆಳೆ ಸೂಕ್ತ?",
        "send_text": "ಪ್ರಶ್ನೆ ಪರೀಕ್ಷಿಸಿ", "demo_mode": "Gnani API ಕೀ ಇಲ್ಲ. ಬರಹದ ಪರೀಕ್ಷೆ ಮಾತ್ರ ಲಭ್ಯ; ನಿಜವಾದ ಧ್ವನಿ API ಕೆಲಸ ಮಾಡುವುದಿಲ್ಲ.",
        "quick": "ತ್ವರಿತ ಸೇವೆಗಳು", "myfarm": "ನನ್ನ ಜಮೀನಿನ ಮಾಹಿತಿ", "save": "ಮಾಹಿತಿ ಉಳಿಸಿ", "location": "ನಿಮ್ಮ ಊರು / ಹಳ್ಳಿ",
        "district": "ಜಿಲ್ಲೆ", "land": "ಜಮೀನು (ಎಕರೆ)", "soil": "ಮಣ್ಣಿನ ಪ್ರಕಾರ", "irrigation": "ನೀರಿನ ವ್ಯವಸ್ಥೆ", "current_crop": "ಈಗ ಬೆಳೆಯುತ್ತಿರುವ ಬೆಳೆ",
        "sowing_date": "ಬಿತ್ತನೆ ದಿನಾಂಕ (ಇದ್ದರೆ)", "language_saved": "ಮಾತನಾಡುವ ಭಾಷೆ", "unknown": "ಗೊತ್ತಿಲ್ಲ / ತಿಳಿದಿಲ್ಲ",
        "crop_title": "ನಿಮ್ಮ ಪ್ರದೇಶದ ಬೆಳೆ ಆಯ್ಕೆಗಳು", "crop_note": "ಇವು UAS Bengaluru Zone V ಯಲ್ಲಿ ಉಲ್ಲೇಖಿಸಿರುವ ಬೆಳೆ ಗುಂಪುಗಳು. ಇದು ನಿಮ್ಮ ಹೊಲಕ್ಕೆ ಅಂತಿಮ ಶಿಫಾರಸು ಅಥವಾ ಬೆಳೆಗಳ ಶ್ರೇಯಾಂಕವಲ್ಲ.",
        "weather_title": "ನಿಮ್ಮ ಊರಿನ ಹವಾಮಾನ", "refresh": "ಹವಾಮಾನ ನೋಡಿ", "market_title": "ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ದಾಖಲೆಗಳು", "commodity": "ಬೆಳೆ / ತರಕಾರಿ", "market_search": "ಬೆಲೆ ಹುಡುಕಿ",
        "no_api": "ಅಧಿಕೃತ CSV ಫೈಲ್ ಇನ್ನೂ ಸೇರಿಸಲಾಗಿಲ್ಲ.", "repair_title": "ಯಂತ್ರದ ತೊಂದರೆ ದಾಖಲಿಸಿ", "repair_desc": "ನಿಮ್ಮ ಮೋಟಾರ್ ಅಥವಾ ಕೃಷಿ ಯಂತ್ರದ ಸಮಸ್ಯೆಯನ್ನು ಹೇಳಿ. ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ ನಂತರ ದೂರು ದಾಖಲಿಸಿ.",
        "transcript": "ಗುರುತಿಸಿದ ಮಾತು (ಐಚ್ಛಿಕವಾಗಿ ನೋಡಿ)", "machine": "ಯಂತ್ರ", "problem": "ತೊಂದರೆ", "village": "ಊರು", "duration": "ಎಷ್ಟು ದಿನಗಳಿಂದ?", "capacity": "ಸಾಮರ್ಥ್ಯ (ಗೊತ್ತಿದ್ದರೆ)",
        "confirm": "ವಿವರಗಳು ಸರಿಯಾಗಿವೆ. ದೂರು ದಾಖಲಿಸಿ.", "create": "ದೂರು ದಾಖಲಿಸಿ", "saved": "ದೂರು ದಾಖಲಿಸಲಾಗಿದೆ", "operator_title": "ಸೇವಾ ಸಿಬ್ಬಂದಿ ಫಲಕ",
        "coming": "ಈ ವಿಭಾಗ ಮುಂದಿನ ಬಿಡುಗಡೆಯಲ್ಲಿ ಸೇರಿಸಲಾಗುತ್ತದೆ.", "source": "ಮೂಲ", "as_of": "ಮಾಹಿತಿ ಸಮಯ", "market_csv_help": "ಸರ್ಕಾರದ mandi API ಬಳಸಲು DATA_GOV_IN_API_KEY ಸೇರಿಸಿ. API ಸಿಗದಿದ್ದರೆ ಅಧಿಕೃತ Agmarknet CSV ಬ್ಯಾಕಪ್ ಬಳಸಿ.",
    },
    "en": {
        "home": "Home", "farm": "My Farm", "crop": "Crop Planner", "weather": "Weather", "market": "Mandi Prices",
        "repair": "Farm Repairs", "health": "Crop Health", "planner": "Daily Farm Plan", "operator": "Operator", "settings": "Settings",
        "hero": "Your farming companion", "subtitle": "Ask your farming question in your own language.",
        "voice_title": "Talk to NammaVaani", "voice_hint": "Speak one short question. Keep each recording under 30 seconds.",
        "speech_language": "Language you will speak", "consent": "I agree to send this audio to Gnani for speech recognition.",
        "send_voice": "🎤 Send spoken question", "audio_missing": "Record your voice first.",
        "typed_demo": "Typed test question (this is not speech recognition)", "typed_placeholder": "Example: Which crop is suitable this season?",
        "send_text": "Test question", "demo_mode": "No Gnani API key configured. Typed testing is available; live speech APIs are disabled.",
        "quick": "Quick services", "myfarm": "My farm information", "save": "Save information", "location": "Village / town",
        "district": "District", "land": "Land size (acres)", "soil": "Soil type", "irrigation": "Water source", "current_crop": "Current crop",
        "sowing_date": "Sowing date (if known)", "language_saved": "Preferred spoken language", "unknown": "Unknown / not sure",
        "crop_title": "Crop options for your region", "crop_note": "These are crops listed for UAS Bengaluru Zone V. This is not a final recommendation or ranking for your specific field.",
        "weather_title": "Weather near your farm", "refresh": "Check weather", "market_title": "Mandi price records", "commodity": "Commodity", "market_search": "Find prices",
        "no_api": "An official CSV file has not been added yet.", "repair_title": "Report a farm equipment problem", "repair_desc": "Describe the problem with your motor or farm equipment. Review the details before creating a request.",
        "transcript": "Recognised words (optional review)", "machine": "Machine", "problem": "Problem", "village": "Village", "duration": "How long?", "capacity": "Capacity (if known)",
        "confirm": "These details are correct. Create the request.", "create": "Create request", "saved": "Your request has been recorded", "operator_title": "Service operator dashboard",
        "coming": "This module is planned for a later release.", "source": "Source", "as_of": "Retrieved at", "market_csv_help": "Add DATA_GOV_IN_API_KEY for automatic government API lookup. The official Agmarknet CSV remains the fallback.",
    },
}


def _safe_index(items: list[str], value: str | None) -> int:
    try:
        return items.index(value)  # type: ignore[arg-type]
    except ValueError:
        return 0


def _lang_response(language: str, kn: str, te: str, en: str) -> str:
    return kn if language == "kn" else te if language == "te" else en


def _tts(text: str, speech_name: str, api_key: str | None) -> bytes | None:
    if not api_key:
        return None
    cfg = LANGUAGES[speech_name]
    return synthesize_speech(text, api_key, cfg["tts"], cfg["voice"])


def _set_pending(slot: str | None, intent: str | None = None) -> None:
    st.session_state["assistant_pending_slot"] = slot
    st.session_state["assistant_pending_intent"] = intent


def _service_error_message(exc: Exception, language: str) -> str:
    """Return a farmer-friendly error instead of exposing API jargon in speech."""
    if isinstance(exc, WeatherServiceError):
        return localized(
            language,
            "ಈ ಊರಿನ ಹವಾಮಾನ ಮಾಹಿತಿ ಈಗ ಸಿಗಲಿಲ್ಲ. ಊರಿನ ಹೆಸರನ್ನು ಪರಿಶೀಲಿಸಿ ಅಥವಾ ನಂತರ ಪ್ರಯತ್ನಿಸಿ.",
            "ఈ ప్రాంతపు వాతావరణ సమాచారం ఇప్పుడు అందుబాటులో లేదు. గ్రామం పేరును సరిచూసి మళ్లీ ప్రయత్నించండి.",
            "I couldn't retrieve weather for that place. Check the town name or try again later.",
        )
    if isinstance(exc, MarketDataError):
        return localized(
            language,
            "ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಮಾಹಿತಿ ಈಗ ಸಿಗಲಿಲ್ಲ. ಬೆಳೆ ಮತ್ತು ಮಾರುಕಟ್ಟೆ ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ ಅಥವಾ ನಂತರ ಪ್ರಯತ್ನಿಸಿ.",
            "మార్కెట్ ధర సమాచారం ఇప్పుడు అందుబాటులో లేదు. పంట, మార్కెట్ వివరాలు చూసి మళ్లీ ప్రయత్నించండి.",
            "Mandi prices are unavailable right now. Check the commodity and market details or try again later.",
        )
    return str(exc)


def _process_followup(text: str, language: str, profile: dict[str, Any]) -> tuple[str, str | None, str | None]:
    slot = st.session_state.get("assistant_pending_slot")
    intent = st.session_state.get("assistant_pending_intent")
    if not slot:
        return "", None, None

    if slot == "soil_type":
        profile["soil_type"] = parse_soil(text)
        save_farmer_profile(profile)
        _set_pending("irrigation", intent)
        question = localized(language,
            "ನಿಮ್ಮ ಜಮೀನಿಗೆ ನೀರು ಹೇಗೆ ಸಿಗುತ್ತದೆ? ಬೋರ್‌ವೆಲ್, ಕಾಲುವೆ/ಕೆರೆ, ಹನಿ ನೀರಾವರಿ ಅಥವಾ ಮಳೆಯ ನೀರೇ?",
            "మీ పొలానికి నీరు ఎలా వస్తుంది? బోరు, కాలువ/చెరువు, డ్రిప్ లేదా వర్షాధారమా?",
            "How does your farm get water: borewell, canal/tank, drip irrigation, or rainfall only?",
        )
        return question, "crop", None
    if slot == "irrigation":
        profile["irrigation"] = parse_irrigation(text)
        save_farmer_profile(profile)
        _set_pending(None, None)
        st.session_state["assistant_crop_candidates"] = crop_basket(language)
        return crop_advisory_text(profile, language), "crop", "crop"
    if slot == "location":
        profile["location"] = text.strip().strip(".,!? ")
        save_farmer_profile(profile)
        _set_pending(None, None)
        reply, result = _weather_reply(profile["location"], language)
        st.session_state["assistant_weather"] = result
        return reply, "weather", "weather"
    if slot == "commodity":
        commodity = detect_commodity(text)
        _set_pending(None, None)
        if not commodity:
            _set_pending("commodity", "market")
            return market_question(language), "market", None
        return _market_reply(commodity, profile, language), "market", "market"
    _set_pending(None, None)
    return localized(language, "ಮತ್ತೊಮ್ಮೆ ಸರಳವಾಗಿ ಹೇಳಿ.", "మళ్లీ సులభంగా చెప్పండి.", "Please say that another way."), "general", None


def _weather_reply(location: str, language: str) -> tuple[str, dict[str, Any]]:
    result = get_weather_forecast(location)
    current = result.get("current", {})
    daily = result.get("daily", [])
    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    rain = current.get("precipitation")
    wind = current.get("wind_speed_10m")
    temp_text = f"{temp}°C" if temp is not None else "—"
    humidity_text = f"{humidity}%" if humidity is not None else "—"
    rain_text = f"{rain} mm" if rain is not None else "—"
    wind_text = f"{wind} km/h" if wind is not None else "—"
    if language == "kn":
        reply = f"{result['location']['name']} ಹವಾಮಾನ. ಈಗ ತಾಪಮಾನ {temp_text}, ತೇವಾಂಶ {humidity_text}, ಮಳೆ {rain_text}, ಗಾಳಿಯ ವೇಗ {wind_text}. ಮುಂದಿನ ದಿನಗಳ ವಿವರಗಳನ್ನು ಪರದೆಯಲ್ಲಿ ನೋಡಿ. ಇದು ಹವಾಮಾನ ಪೂರ್ವಾನುಮಾನ; ಹೊಲದ ಸ್ಥಳೀಯ ಪರಿಸ್ಥಿತಿಯನ್ನೂ ಪರಿಶೀಲಿಸಿ."
    elif language == "te":
        reply = f"{result['location']['name']} వాతావరణం. ప్రస్తుతం ఉష్ణోగ్రత {temp_text}, తేమ {humidity_text}, వర్షపాతం {rain_text}, గాలి వేగం {wind_text}. రాబోయే రోజుల వివరాలు తెరపై చూడండి. ఇది వాతావరణ అంచనా మాత్రమే; పొలంలోని స్థానిక పరిస్థితులను కూడా పరిశీలించండి."
    else:
        reply = f"Weather near {result['location']['name']}: temperature {temp_text}, humidity {humidity_text}, precipitation {rain_text}, wind {wind_text}. See the forecast below. This is a forecast; also check conditions at your field."
    return reply, result


def _market_reply(commodity: str, profile: dict[str, Any], language: str) -> str:
    rows = load_mandi_prices(
        commodity, profile.get("district") or "Bengaluru Urban",
        state=profile.get("state") or "Karnataka",
    )
    st.session_state["assistant_market_rows"] = rows
    best = rows[0]
    market = best.get("market") or best.get("district") or "selected market"
    modal = best.get("modal_price")
    min_price = best.get("min_price")
    max_price = best.get("max_price")
    modal_text = f"₹{modal:,.0f}" if modal is not None else "not reported"
    if language == "kn":
        return f"{market} ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ {commodity} ಬೆಳೆಗಾಗಿ ಕೊನೆಯ ಲಭ್ಯ ದಾಖಲೆ {best['arrival_date']}. ಮಧ್ಯಮ ಬೆಲೆ ಕ್ವಿಂಟಲ್‌ಗೆ {modal_text}. ಕನಿಷ್ಠ ಮತ್ತು ಗರಿಷ್ಠ ಬೆಲೆಯನ್ನು ಪರದೆಯಲ್ಲಿ ನೋಡಿ. ಇದು ಮಾರುಕಟ್ಟೆ ವರದಿ; ನಿಮಗೆ ಸಿಗುವ ಖಚಿತ ಮಾರಾಟ ಬೆಲೆ ಅಲ್ಲ."
    if language == "te":
        return f"{market} మార్కెట్‌లో {commodity} కు చివరిగా అందుబాటులో ఉన్న ధర తేదీ {best['arrival_date']}. మోడల్ ధర క్వింటాల్‌కు {modal_text}. కనిష్ఠ, గరిష్ఠ ధరలను తెరపై చూడండి. ఇది మార్కెట్ నివేదిక మాత్రమే; మీకు లభించే ఖచ్చితమైన అమ్మకపు ధర కాదు."
    return f"The latest available {commodity} observation for {market} is dated {best['arrival_date']}. The modal price is {modal_text} per quintal. See minimum and maximum prices below. This is a reported mandi price, not a guaranteed farm-gate price."


def _handle_assistant_turn(text: str, language: str) -> tuple[str, str]:
    profile = get_farmer_profile()
    pending_slot = st.session_state.get("assistant_pending_slot")
    if pending_slot:
        try:
            reply, intent, _data_kind = _process_followup(text, language, profile)
            # Follow-up handlers perform their own retrieval once the missing
            # detail is supplied. Avoid making a duplicate weather API request.
            return reply, intent or "general"
        except (WeatherServiceError, MarketDataError) as exc:
            return _service_error_message(exc, language), "error"

    intent = classify_intent(text)
    if intent == "crop":
        slot, question = crop_followup(profile, language)
        if slot:
            _set_pending(slot, "crop")
            return question or "", intent
        st.session_state["assistant_crop_candidates"] = crop_basket(language)
        return crop_advisory_text(profile, language), intent
    if intent == "weather":
        if not profile.get("location"):
            _set_pending("location", "weather")
            return weather_question(language), intent
        try:
            reply, result = _weather_reply(profile["location"], language)
            st.session_state["assistant_weather"] = result
            return reply, intent
        except WeatherServiceError as exc:
            return _service_error_message(exc, language), "error"
    if intent == "market":
        commodity = detect_commodity(text)
        if not commodity:
            _set_pending("commodity", "market")
            return market_question(language), intent
        try:
            return _market_reply(commodity, profile, language), intent
        except MarketDataError as exc:
            return _service_error_message(exc, language), "error"
    if intent == "repair":
        return localized(language,
            "ಯಂತ್ರದ ದುರಸ್ತಿ ದಾಖಲಿಸಲು ‘ಯಂತ್ರ ದುರಸ್ತಿ’ ವಿಭಾಗ ತೆರೆಯಿರಿ. ನಿಮ್ಮ ಮಾತಿನ ಆಧಾರದ ಮೇಲೆ ದೂರು ದಾಖಲಿಸಬಹುದು.",
            "యంత్ర మరమ్మత్తు నమోదు చేయడానికి ‘Farm Repairs’ విభాగాన్ని తెరవండి.",
            "Open Farm Repairs to create a service request from your spoken description."), intent
    if intent == "crop_health":
        return localized(language,
            "ಬೆಳೆ ಎಲೆ ಅಥವಾ ಗಿಡದ ಫೋಟೋ ಪರಿಶೀಲನೆ ಮುಂದಿನ ಬಿಡುಗಡೆಯಲ್ಲಿ ಬರುತ್ತದೆ. ಈಗ ಬೆಳೆ ಹೆಸರು ಮತ್ತು ಲಕ್ಷಣಗಳನ್ನು ದಾಖಲಿಸಿ; ಔಷಧಿ ಬಳಸುವ ಮೊದಲು KVK ಸಲಹೆ ಪಡೆಯಿರಿ.",
            "పంట ఫోటో ఆధారిత నిర్ధారణ తదుపరి విడుదలలో ఉంటుంది. పంట పేరు, లక్షణాలు నమోదు చేయండి; మందు వాడే ముందు KVK సలహా తీసుకోండి.",
            "Photo-based crop-health support is planned for a later release. Record the crop and symptoms, and consult a KVK before applying chemicals."), intent
    return localized(language,
        "ಬೆಳೆ, ಹವಾಮಾನ, ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಅಥವಾ ಯಂತ್ರದ ತೊಂದರೆ ಬಗ್ಗೆ ಕೇಳಬಹುದು.",
        "పంట, వాతావరణం, మార్కెట్ ధర లేదా యంత్ర సమస్య గురించి అడగవచ్చు.",
        "You can ask about crops, weather, mandi prices or farm equipment problems."), intent


def _go_to_page(target: str) -> None:
    st.session_state["namma_page"] = target
    st.session_state["app_page_choice"] = target


def _render_home(ui_language: str, speech_language: str, api_key: str | None) -> None:
    t = UI[ui_language]
    st.subheader(t["voice_title"])
    st.write(t["voice_hint"])
    profile = get_farmer_profile()
    p1, p2, p3 = st.columns(3)
    p1.metric("📍 " + ("ಸ್ಥಳ" if ui_language == "kn" else "Farm area"), profile.get("location") or "Not set")
    p2.metric("🌱 " + ("ಮಣ್ಣು" if ui_language == "kn" else "Soil"), profile.get("soil_type") or t["unknown"])
    p3.metric("💧 " + ("ನೀರು" if ui_language == "kn" else "Water"), profile.get("irrigation") or t["unknown"])

    st.markdown("### 🎤 " + ("ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಕೇಳಿ" if ui_language == "kn" else "Ask your question"))
    language_display = st.selectbox(
        t["speech_language"],
        ["Kannada", "Telugu", "English (India)"],
        index=["Kannada", "Telugu", "English (India)"].index(speech_language),
        key="assistant_speech_language",
    )
    recorded = st.audio_input(
        "ಮಾತನಾಡಿ / Record your question" if ui_language == "kn" else "Record your question",
        key=f"assistant_audio_{st.session_state.get('assistant_audio_turn', 0)}",
    )
    audio_turn = st.session_state.get("assistant_audio_turn", 0)
    consent = st.checkbox(t["consent"], key=f"assistant_audio_consent_{audio_turn}")
    if st.button(t["send_voice"], type="primary", use_container_width=True, disabled=(recorded is None or not consent or not api_key)):
        cfg = LANGUAGES[language_display]
        try:
            with st.spinner("ನಿಮ್ಮ ಮಾತನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳುತ್ತಿದ್ದೇವೆ…" if ui_language == "kn" else "Understanding your question…"):
                result = transcribe_audio(recorded.getvalue(), "farmer-question.wav", api_key or "", cfg["stt"])
            utterance = str(result.get("transcript", "")).strip()
            if not utterance:
                st.warning("ಮಾತು ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ." if ui_language == "kn" else "No speech detected. Please try again.")
            else:
                reply, intent = _handle_assistant_turn(utterance, "kn" if language_display == "Kannada" else "te" if language_display == "Telugu" else "en")
                st.session_state.setdefault("assistant_history", []).append({"user": utterance, "assistant": reply, "intent": intent, "source": "Gnani Prisma v2.5"})
                st.session_state["assistant_last_transcript"] = utterance
                st.session_state["assistant_last_reply"] = reply
                st.session_state["assistant_audio_turn"] = st.session_state.get("assistant_audio_turn", 0) + 1
                try:
                    st.session_state["assistant_last_audio"] = _tts(reply, language_display, api_key)
                except GnaniAPIError as exc:
                    st.session_state["assistant_tts_error"] = str(exc)
                st.rerun()
        except GnaniAPIError as exc:
            st.error(str(exc))

    if not api_key:
        st.info(t["demo_mode"])
    with st.expander(t["typed_demo"], expanded=not bool(api_key)):
        typed = st.text_input(t["typed_demo"], placeholder=t["typed_placeholder"], key="assistant_typed_question")
        if st.button(t["send_text"], key="assistant_send_typed", use_container_width=True, disabled=not typed.strip()):
            reply, intent = _handle_assistant_turn(typed.strip(), "kn" if language_display == "Kannada" else "te" if language_display == "Telugu" else "en")
            st.session_state.setdefault("assistant_history", []).append({"user": typed.strip(), "assistant": reply, "intent": intent, "source": "Typed test – not Prisma"})
            st.session_state["assistant_last_reply"] = reply
            st.rerun()

    if st.session_state.get("assistant_history"):
        st.divider()
        st.subheader("💬 " + ("ನಮ್ಮ ಸಂಭಾಷಣೆ" if ui_language == "kn" else "Our conversation"))
        for item in st.session_state["assistant_history"][-8:]:
            with st.chat_message("user"):
                st.write(item["user"])
            with st.chat_message("assistant"):
                st.write(item["assistant"])
                st.caption(f"Intent: {item['intent']} · {item['source']}")
        if st.session_state.get("assistant_last_audio"):
            st.audio(st.session_state["assistant_last_audio"], format="audio/wav")
        if st.session_state.get("assistant_weather"):
            weather = st.session_state["assistant_weather"]
            st.markdown("#### 🌦️ Forecast details")
            weather_rows = [{
                "Date": d["date"], "Min °C": d["temperature_2m_min"], "Max °C": d["temperature_2m_max"],
                "Rain mm": d["precipitation_sum"], "Rain probability %": d["precipitation_probability_max"],
                "Conditions": weather_code_label(d["weather_code"]),
            } for d in weather.get("daily", [])]
            st.dataframe(pd.DataFrame(weather_rows), use_container_width=True, hide_index=True)
            st.caption(f"{weather.get('attribution')} · {weather.get('fetched_at')}")
        if st.session_state.get("assistant_market_rows"):
            st.markdown("#### 💰 Mandi price records")
            st.dataframe(pd.DataFrame(st.session_state["assistant_market_rows"]), use_container_width=True, hide_index=True)
        if st.session_state.get("assistant_crop_candidates"):
            st.markdown("#### 🌱 Local crop groups to investigate")
            st.dataframe(pd.DataFrame(st.session_state["assistant_crop_candidates"]), use_container_width=True, hide_index=True)
        if st.button("Clear conversation" if ui_language == "en" else "ಸಂಭಾಷಣೆ ತೆರವುಗೊಳಿಸಿ"):
            for key in ("assistant_history", "assistant_pending_slot", "assistant_pending_intent", "assistant_last_audio", "assistant_last_reply", "assistant_weather", "assistant_market_rows", "assistant_crop_candidates"):
                st.session_state.pop(key, None)
            st.rerun()

    st.divider()
    st.subheader(t["quick"])
    service_cards = [
        ("🌱", t["crop"], "Crop Planner"), ("🌦️", t["weather"], "Weather"),
        ("💰", t["market"], "Mandi Prices"), ("🐛", t["health"], "Crop Health"),
        ("🔧", t["repair"], "Farm Repairs"), ("📅", t["planner"], "Daily Farm Plan"),
    ]
    for row_start in range(0, len(service_cards), 2):
        cols = st.columns(2)
        for col, (icon, label, target) in zip(cols, service_cards[row_start:row_start + 2]):
            with col:
                st.button(f"{icon}  {label}", key=f"home_nav_{target}", use_container_width=True, on_click=_go_to_page, args=(target,))


def _render_my_farm(ui_language: str) -> None:
    t = UI[ui_language]
    st.subheader("🌱 " + t["myfarm"])
    st.write("ನಿಮ್ಮ ಜಮೀನಿನ ಮಾಹಿತಿ ಒಮ್ಮೆ ಉಳಿಸಿ. ಪ್ರತಿಸಾರಿ ಮತ್ತೆ ಹೇಳಬೇಕಾಗುವುದಿಲ್ಲ." if ui_language == "kn" else "Save your farm details once. NammaVaani can reuse them in later conversations.")
    profile = get_farmer_profile()
    with st.form("my_farm_profile"):
        location = st.text_input(t["location"], value=profile.get("location") or "Bengaluru Urban, Karnataka")
        district = st.selectbox(t["district"], ["Bengaluru Urban", "Bengaluru Rural", "Ramanagara", "Kolar", "Chikkaballapur"], index=_safe_index(["Bengaluru Urban", "Bengaluru Rural", "Ramanagara", "Kolar", "Chikkaballapur"], profile.get("district")))
        land = st.number_input(t["land"], min_value=0.0, max_value=10000.0, value=float(profile["land_acres"] or 0.0), step=0.25)
        soils = [t["unknown"], "Red soil / ಕೆಂಪು ಮಣ್ಣು", "Black soil / ಕಪ್ಪು ಮಣ್ಣು", "Sandy soil / ಮರಳು ಮಣ್ಣು", "Lateritic soil", "Alluvial soil"]
        irrigation_options = [t["unknown"], "Borewell / ಬೋರ್‌ವೆಲ್", "Canal or tank / ಕಾಲುವೆ ಅಥವಾ ಕೆರೆ", "Rainfed / ಮಳೆಯ ನೀರು", "Drip irrigation / ಹನಿ ನೀರಾವರಿ"]
        soil_label_map = {"Red soil": soils[1], "Black soil": soils[2], "Sandy soil": soils[3], "Lateritic soil": soils[4], "Alluvial soil": soils[5]}
        water_label_map = {"Borewell": irrigation_options[1], "Canal / tank": irrigation_options[2], "Rainfed": irrigation_options[3], "Drip irrigation": irrigation_options[4]}
        soil_sel = st.selectbox(t["soil"], soils, index=_safe_index(soils, soil_label_map.get(profile.get("soil_type"), soils[0])))
        irrigation_sel = st.selectbox(t["irrigation"], irrigation_options, index=_safe_index(irrigation_options, water_label_map.get(profile.get("irrigation"), irrigation_options[0])))
        current_crop = st.text_input(t["current_crop"], value=profile.get("current_crop") or "")
        sowing_enabled = st.checkbox("I know the sowing date / ಬಿತ್ತನೆ ದಿನ ಗೊತ್ತಿದೆ", value=bool(profile.get("sowing_date")))
        sowing_date = st.date_input(t["sowing_date"], value=date.fromisoformat(profile["sowing_date"]) if profile.get("sowing_date") else date.today()) if sowing_enabled else None
        preferred_language = st.selectbox(t["language_saved"], ["Kannada", "Telugu", "English (India)"], index=_safe_index(["Kannada", "Telugu", "English (India)"], profile.get("preferred_language", "Kannada")))
        saved = st.form_submit_button(t["save"], type="primary", use_container_width=True)
    if saved:
        soil_map = {
            "Red soil / ಕೆಂಪು ಮಣ್ಣು": "Red soil", "Black soil / ಕಪ್ಪು ಮಣ್ಣು": "Black soil",
            "Sandy soil / ಮರಳು ಮಣ್ಣು": "Sandy soil", "Lateritic soil": "Lateritic soil", "Alluvial soil": "Alluvial soil",
        }
        water_map = {
            "Borewell / ಬೋರ್‌ವೆಲ್": "Borewell", "Canal or tank / ಕಾಲುವೆ ಅಥವಾ ಕೆರೆ": "Canal / tank",
            "Rainfed / ಮಳೆಯ ನೀರು": "Rainfed", "Drip irrigation / ಹನಿ ನೀರಾವರಿ": "Drip irrigation",
        }
        profile.update({
            "location": location.strip(), "district": district, "state": "Karnataka",
            "land_acres": land if land > 0 else None,
            # Unknown is a valid farmer answer, not a blank that should be
            # asked repeatedly in the voice conversation.
            "soil_type": soil_map.get(soil_sel, "Unknown"),
            "irrigation": water_map.get(irrigation_sel, "Unknown"),
            "current_crop": current_crop.strip() or None,
            "sowing_date": sowing_date.isoformat() if sowing_date else None,
            "preferred_language": preferred_language,
        })
        save_farmer_profile(profile)
        st.success("ನಿಮ್ಮ ಜಮೀನಿನ ಮಾಹಿತಿ ಉಳಿಸಲಾಗಿದೆ." if ui_language == "kn" else "Your farm profile has been saved.")


def _render_crop_planner(ui_language: str) -> None:
    t = UI[ui_language]
    st.subheader("🌱 " + t["crop_title"])
    st.caption(t["crop_note"])
    context = zone_context()
    st.info(f"UAS Bengaluru · {context['zone']} · {context['climate']} · Typical zone soil: {context['dominant_soil']}")
    profile = get_farmer_profile()
    c1, c2, c3 = st.columns(3)
    c1.metric("Location", profile.get("location") or "Bengaluru Urban")
    c2.metric("Land (acres)", profile.get("land_acres") or t["unknown"])
    c3.metric("Water source", profile.get("irrigation") or t["unknown"])
    crops = crop_basket("kn" if ui_language == "kn" else "en")
    df = pd.DataFrame(crops)
    df = df.rename(columns={"name": "Crop", "english_name": "English name", "group": "Group", "note": "Why to consider"})
    if "english_name" in df.columns:
        st.dataframe(df[["Crop", "Group", "Why to consider"]], use_container_width=True, hide_index=True)
    st.warning("This is a locally grounded crop basket, not a personalised best-crop ranking. Confirm sowing time, variety, seed rate, input plan and crop protection from the current UAS Bengaluru Package of Practices or your nearest KVK before planting.")
    st.markdown(f"**Sources:** [UAS Bengaluru agro-climatic zones]({UASB_ZONE_V_SOURCE}) · [UAS e-books / Package of Practices]({UASB_PRACTICES_SOURCE})")
    with st.expander("Tell us more to improve your crop advice"):
        st.write(f"Soil: {profile.get('soil_type') or 'Not known'} · Irrigation: {profile.get('irrigation') or 'Not known'} · Land: {profile.get('land_acres') or 'Not known'} acres")
        st.caption("Fill or update these details in My Farm. Crop-specific recommendations will be added only when we map the relevant UAS practice tables and sowing windows.")


def _render_weather(ui_language: str) -> None:
    t = UI[ui_language]
    st.subheader("🌦️ " + t["weather_title"])
    profile = get_farmer_profile()
    default_location = profile.get("location") or "Bengaluru, Karnataka"
    location = st.text_input(t["location"], value=default_location, key="weather_location")
    if st.button(t["refresh"], type="primary", use_container_width=True):
        try:
            with st.spinner("ಹವಾಮಾನ ಮಾಹಿತಿ ಪಡೆಯಲಾಗುತ್ತಿದೆ…" if ui_language == "kn" else "Fetching forecast…"):
                result = get_weather_forecast(location)
            st.session_state["weather_result"] = result
        except WeatherServiceError as exc:
            st.error(str(exc))
    result = st.session_state.get("weather_result")
    if result:
        current = result["current"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Temperature", f"{current.get('temperature_2m', '—')} °C")
        m2.metric("Humidity", f"{current.get('relative_humidity_2m', '—')} %")
        m3.metric("Rain now", f"{current.get('precipitation', '—')} mm")
        m4.metric("Wind", f"{current.get('wind_speed_10m', '—')} km/h")
        rows = []
        for day in result["daily"]:
            rows.append({
                "Date": day["date"], "Min °C": day["temperature_2m_min"], "Max °C": day["temperature_2m_max"],
                "Rain mm": day["precipitation_sum"], "Rain probability %": day["precipitation_probability_max"],
                "Conditions": weather_code_label(day["weather_code"]),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(f"{result['attribution']} · Retrieved: {result['fetched_at']} · Location match: {result['location']['name']}, {result['location'].get('admin1','')}")
        st.warning("Forecasts are model guidance, not a guarantee. The selected town's weather may differ from conditions at an individual field. Check IMD district warnings and local conditions before taking weather-sensitive action.")
    else:
        st.info("Press Check weather to retrieve a current forecast for the selected village or town. Weather is fetched from Open-Meteo and credited on the results screen.")


def _render_market(ui_language: str) -> None:
    t = UI[ui_language]
    st.subheader("💰 " + t["market_title"])
    profile = get_farmer_profile()
    commodity = st.selectbox(t["commodity"], ["Tomato", "Onion", "Ragi", "Maize", "Groundnut", "Potato", "Green chilli", "Beans"])
    districts = ["Bengaluru Urban", "Bengaluru Rural", "Ramanagara", "Kolar", "Chikkaballapur"]
    district = st.selectbox(t["district"], districts, index=_safe_index(districts, profile.get("district")))

    if ui_language == "kn":
        st.write("DATA_GOV_IN_API_KEY ಇದ್ದರೆ ಸರ್ಕಾರದ mandi API ಮೊದಲು ಬಳಸುತ್ತೇವೆ; API ಸಿಗದಿದ್ದರೆ ಅಧಿಕೃತ Agmarknet CSV ಬಳಸುತ್ತೇವೆ.")
        upload_label = "Agmarknet CSV ಫೈಲ್ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ"
        save_label = "ಈ ಫೈಲ್ ಅನ್ನು ಮುಂದಿನ ಬಳಕೆಗೆ ಉಳಿಸಿ"
        source_label = "CSV ಫೈಲ್‌ನಲ್ಲಿರುವ ಬೆಲೆ ದಾಖಲೆಗಳು"
    elif ui_language == "te":
        st.write("DATA_GOV_IN_API_KEY ఉంటే ప్రభుత్వ mandi API ముందుగా ఉపయోగిస్తాం; API అందుబాటులో లేకపోతే అధికారిక Agmarknet CSV ఉపయోగిస్తాం.")
        upload_label = "Agmarknet CSV ఫైల్‌ను అప్‌లోడ్ చేయండి"
        save_label = "తర్వాత ఉపయోగించడానికి ఈ ఫైల్‌ను సేవ్ చేయండి"
        source_label = "CSV ఫైల్‌లోని ధర వివరాలు"
    else:
        st.write("NammaVaani tries the government mandi API first when configured. If it is unavailable, it uses the official Agmarknet CSV uploaded below.")
        upload_label = "Upload official Agmarknet CSV"
        save_label = "Save this CSV for future use"
        source_label = "Price observations from the CSV"

    st.markdown(
        "[Download the official Agmarknet daily-price CSV from data.gov.in]("
        "https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)"
    )
    uploaded = st.file_uploader(upload_label, type=["csv"], key="mandi_csv_upload")
    uploaded_bytes = uploaded.getvalue() if uploaded is not None else None
    local_csv = default_mandi_csv_path()

    if uploaded is not None:
        st.caption(f"Selected file: {uploaded.name} ({uploaded.size:,} bytes)")
        if st.button(save_label, use_container_width=True):
            try:
                saved_path = save_mandi_csv(uploaded_bytes)
                st.success(f"CSV saved for future use: {saved_path}")
            except MarketDataError as exc:
                st.error(str(exc))
    elif local_csv.exists():
        st.success(f"Saved mandi CSV found: {local_csv.name}")
    else:
        st.info(
            "No local CSV backup found yet. Automatic API lookup works when DATA_GOV_IN_API_KEY is set. "
            "You can also upload the official CSV below as a backup."
        )

    if st.button(t["market_search"], type="primary", use_container_width=True):
        try:
            with st.spinner("Loading market observations…"):
                rows = load_mandi_prices(
                    commodity,
                    district,
                    state=get_farmer_profile().get("state") or "Karnataka",
                    csv_path=(uploaded.name if uploaded is not None else None),
                    csv_bytes=uploaded_bytes,
                )
            st.session_state["market_rows"] = rows
            st.session_state["market_query"] = {"commodity": commodity, "district": district}
        except MarketDataError as exc:
            st.session_state.pop("market_rows", None)
            st.session_state.pop("market_query", None)
            st.error(str(exc))

    rows = st.session_state.get("market_rows")
    query = st.session_state.get("market_query", {})
    if rows and query.get("commodity") == commodity and query.get("district") == district:
        st.markdown(f"**{source_label}**")
        show_columns = [
            "market", "commodity", "variety", "arrival_date", "min_price",
            "max_price", "modal_price", "freshness",
        ]
        display = pd.DataFrame(rows)
        display = display[[column for column in show_columns if column in display.columns]].rename(columns={
            "market": "Market", "commodity": "Commodity", "variety": "Variety",
            "arrival_date": "Arrival date", "min_price": "Minimum (₹/quintal)",
            "max_price": "Maximum (₹/quintal)", "modal_price": "Modal (₹/quintal)",
            "freshness": "Data freshness",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)
        newest = rows[0]
        age = newest.get("days_old", 0)
        if age <= 1:
            st.success(f"Latest record date: {newest['arrival_date']} · {newest['freshness']}")
        elif age <= 3:
            st.warning(f"Latest record date: {newest['arrival_date']} · {newest['freshness']}")
        else:
            st.warning(f"Latest record date: {newest['arrival_date']} · {newest['freshness']}. Download a newer file if available.")
        st.caption(
            f"Source: {newest.get('source', 'Agmarknet')} · File: {newest.get('source_file', 'CSV')}. "
            "These are reported wholesale mandi observations, not guaranteed farm-gate prices."
        )
    else:
        st.caption("Source priority: data.gov.in Agmarknet API, then the saved or uploaded official CSV. The arrival date is the observation date, not a real-time quote.")


def _render_repairs(ui_language: str, speech_language: str, api_key: str | None) -> None:
    t = UI[ui_language]
    st.subheader("🔧 " + t["repair_title"])
    st.write(t["repair_desc"])
    profile = get_farmer_profile()
    speech_cfg = LANGUAGES[speech_language]
    audio = st.audio_input("ಮಾತನಾಡಿ / Record your repair request", key="repair_audio")
    consent = st.checkbox(t["consent"], key="repair_audio_consent")
    transcript = st.session_state.get("repair_transcript", "")
    if st.button("Understand repair request", type="primary", disabled=(audio is None or not consent or not api_key)):
        try:
            response = transcribe_audio(audio.getvalue(), "repair.wav", api_key or "", speech_cfg["stt"])
            transcript = str(response.get("transcript", "")).strip()
            st.session_state["repair_transcript"] = transcript
            st.session_state["repair_source"] = "gnani_api"
            st.session_state["repair_fields"] = extract_fields(transcript)
            st.rerun()
        except GnaniAPIError as exc:
            st.error(str(exc))
    if not api_key:
        st.info("Configure GNANI_API_KEY for real Prisma transcription. Use the typed field below to test the ticket workflow.")
    with st.expander("Typed demo / fallback", expanded=not bool(transcript)):
        typed = st.text_area("Describe the machine problem", placeholder="My borewell motor is running but water is not coming. Village: Anekal.")
        if st.button("Extract repair details from text", disabled=not typed.strip()):
            st.session_state["repair_transcript"] = typed.strip()
            st.session_state["repair_source"] = "typed_demo"
            st.session_state["repair_fields"] = extract_fields(typed.strip())
            st.rerun()
    fields = st.session_state.get("repair_fields")
    if not fields:
        return
    with st.expander(t["transcript"], expanded=False):
        edited = st.text_area("Transcript", value=st.session_state.get("repair_transcript", ""), key="repair_edit")
        if st.button("Re-extract after correction"):
            st.session_state["repair_transcript"] = edited
            st.session_state["repair_fields"] = extract_fields(edited)
            st.rerun()
    village = st.text_input(t["village"], value=fields.get("village") or profile.get("location", ""), key="repair_village")
    equipment = st.selectbox(t["machine"], ["Borewell pump / motor", "Water pump", "Tractor", "Drip irrigation", "Harvester", "Sprayer", "Other / not clear"], index=_safe_index(["Borewell pump / motor", "Water pump", "Tractor", "Drip irrigation", "Harvester", "Sprayer", "Other / not clear"], fields.get("equipment")))
    problem = st.selectbox(t["problem"], ["Not starting / not working", "Running but no water output", "Leakage / pipe damage", "Unusual noise / vibration", "Other / not clear"], index=_safe_index(["Not starting / not working", "Running but no water output", "Leakage / pipe damage", "Unusual noise / vibration", "Other / not clear"], fields.get("problem")))
    duration = st.text_input(t["duration"], value=fields.get("duration") or "")
    capacity = st.text_input(t["capacity"], value=fields.get("specification") or "")
    final = {"village": village.strip(), "equipment": equipment, "problem": problem, "duration": duration.strip(), "specification": capacity.strip(), "operating_condition": fields.get("operating_condition")}
    st.markdown("### Review / ಪರಿಶೀಲಿಸಿ")
    st.write(final)
    confirmed = st.checkbox(t["confirm"], key="repair_confirm")
    if st.button(t["create"], type="primary", disabled=(not village.strip() or equipment == "Other / not clear" or problem == "Other / not clear" or not confirmed)):
        ticket_data = {
            **final, "language": speech_language, "reporter_alias": "", "description": ticket_summary(final),
            "priority": "Normal", "transcript": st.session_state.get("repair_transcript", ""),
            "confirmation_text": "User reviewed and confirmed the service request.",
            "source_mode": st.session_state.get("repair_source", "typed_demo"),
        }
        ticket_id = create_ticket(ticket_data)
        st.success(f"{t['saved']}: {ticket_id}")
        for key in ("repair_fields", "repair_transcript", "repair_source", "repair_confirm", "repair_edit"):
            st.session_state.pop(key, None)


def _render_operator() -> None:
    st.subheader("🧰 " + UI["en"]["operator_title"])
    tickets = list_tickets()
    if not tickets:
        st.info("No repair requests yet.")
        return
    df = pd.DataFrame(tickets)
    show_cols = [c for c in ["ticket_id", "created_at", "village", "equipment", "problem", "priority", "status", "technician"] if c in df.columns]
    st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
    selected_id = st.selectbox("Select a ticket", [t["ticket_id"] for t in tickets])
    selected = get_ticket(selected_id)
    if selected:
        a, b = st.columns(2)
        with a:
            new_status = st.selectbox("Status", STATUSES, index=_safe_index(STATUSES, selected.get("status")))
            technician = st.text_input("Technician / service centre", value=selected.get("technician") or "")
        with b:
            st.write(f"**Village:** {selected.get('village')}")
            st.write(f"**Machine:** {selected.get('equipment')}")
            st.write(f"**Problem:** {selected.get('problem')}")
        if st.button("Save ticket update", type="primary"):
            update_ticket(selected_id, new_status, technician.strip() or None)
            st.success("Ticket updated.")
            st.rerun()
    st.download_button("Download tickets CSV", df[show_cols].to_csv(index=False).encode("utf-8"), "nammavaani_tickets.csv", "text/csv")


def _render_settings(api_key: str | None) -> None:
    st.subheader("⚙️ Settings and integrations")
    st.write("NammaVaani uses Gnani Prisma for speech recognition and Timbre for spoken replies. Crop information is sourced from UAS Bengaluru; weather from Open-Meteo; mandi prices are read from an official Agmarknet CSV file.")
    st.markdown("**Gnani speech services**")
    st.success("GNANI_API_KEY detected" if api_key else "GNANI_API_KEY not configured")
    st.code("GNANI_API_KEY=your_gnani_key\nNAMMAVAANI_MANDI_CSV=data/mandi_prices.csv", language="text")
    st.markdown("**Language limitation**")
    st.write("Prisma v2.5 REST requests use one selected language code per recording. For Kannada-English or Telugu-English speech, choose the main language of that turn. Automatic multi-language detection and broader code-mix handling are not claimed for this v2.5 integration.")
    st.markdown("**Data sources**")
    st.markdown("- [UAS Bengaluru agro-climatic zones](https://www.uasbangalore.edu.in/en/agroclimatic-zones-uas-bangalore/)\n- [UAS Bengaluru Package of Practices](https://www.uasbangalore.edu.in/ebooks/)\n- [Open-Meteo weather API](https://open-meteo.com/en/docs)\n- [Agmarknet daily-price CSV on data.gov.in](https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi) – download the CSV and upload it in Mandi Prices.")
    st.markdown("**Privacy**")
    st.write("Audio is sent to Gnani only after the farmer chooses to send it. The prototype stores farm profile fields and confirmed repair tickets in a local SQLite database. Audio recordings are not stored. This is a single-local-profile prototype, not a production multi-user system.")


# ---------------------------- App shell -------------------------------------
st.markdown("""
<style>
.block-container {max-width: 1120px; padding-top: 1.1rem; padding-bottom: 2.4rem;}
.hero {padding: 1.4rem 1.5rem; border-radius: 20px; background: linear-gradient(120deg,#123c2b,#26734c); color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin:0; font-size:2.25rem;}
.hero p {color:#e4f5e9; margin:.4rem 0 0 0; font-size:1.1rem;}
.stButton>button {min-height:3.1rem; border-radius:13px; font-weight:650;}
[data-testid="stAudioInput"] {background:white; border:2px dashed #93b59d; border-radius:16px; padding:.65rem;}
div[data-testid="stMetric"] {background:white; border:1px solid #e2e9e1; padding:10px; border-radius:12px;}
p, label, li {line-height:1.55;}
</style>
""", unsafe_allow_html=True)

api_key = get_gnani_api_key()
PAGE_LABEL_KEYS = {
    "Home": "home", "My Farm": "farm", "Crop Planner": "crop", "Weather": "weather",
    "Mandi Prices": "market", "Farm Repairs": "repair", "Crop Health": "health",
    "Daily Farm Plan": "planner", "Operator": "operator", "Settings": "settings",
}

with st.sidebar:
    st.markdown("## 🌾 NammaVaani")
    ui_choice = st.radio("Display language / ಪರದೆ ಭಾಷೆ", ["ಕನ್ನಡ", "English"], horizontal=True, key="ui_language_choice")
    ui_language = "kn" if ui_choice == "ಕನ್ನಡ" else "en"
    page_targets = list(PAGE_LABEL_KEYS)
    current_target = st.session_state.get("namma_page", "Home")
    page = st.radio(
        "Menu", page_targets, index=_safe_index(page_targets, current_target),
        format_func=lambda item: UI[ui_language][PAGE_LABEL_KEYS[item]], key="app_page_choice",
    )
    st.session_state["namma_page"] = page
    st.divider()
    if api_key:
        st.success("Gnani API ✓")
    else:
        st.caption("Gnani demo / typed test mode")
    st.caption("Pilot: Bengaluru district · Karnataka")

st.markdown(
    f"<div class='hero'><h1>🌾 NammaVaani</h1><p>{escape(UI[ui_language]['hero'])} · {escape(UI[ui_language]['subtitle'])}</p></div>",
    unsafe_allow_html=True,
)

saved_profile_language = get_farmer_profile().get("preferred_language", "Kannada")
# Older profile rows may store short locale codes (kn/te/en); the UI control
# uses the human-readable language names from LANGUAGES.
saved_profile_language = {"kn": "Kannada", "te": "Telugu", "en": "English (India)"}.get(
    saved_profile_language, saved_profile_language
)
if saved_profile_language not in LANGUAGES:
    saved_profile_language = "Kannada"
speech_language = st.session_state.get("assistant_speech_language", saved_profile_language)
if page == "Home":
    _render_home(ui_language, speech_language, api_key)
elif page == "My Farm":
    _render_my_farm(ui_language)
elif page == "Crop Planner":
    _render_crop_planner(ui_language)
elif page == "Weather":
    _render_weather(ui_language)
elif page == "Mandi Prices":
    _render_market(ui_language)
elif page == "Farm Repairs":
    _render_repairs(ui_language, speech_language, api_key)
elif page == "Crop Health":
    st.subheader("🐛 " + UI[ui_language]["health"])
    st.info(UI[ui_language]["coming"])
    st.write("Planned: crop symptom conversation, photo capture, possible-cause explanation, verified local advisory and KVK escalation. No automated pesticide prescription in this release.")
elif page == "Daily Farm Plan":
    st.subheader("📅 " + UI[ui_language]["planner"])
    st.info(UI[ui_language]["coming"])
    st.write("Planned: crop-stage calendar, weather-aware reminders, completed farm activities and voice-based progress updates.")
elif page == "Operator":
    _render_operator()
else:
    _render_settings(api_key)

st.divider()
st.caption("Prototype for the Great Indian AI Internship Challenge · Verify all crop decisions with UAS/KVK guidance · Market prices are reported mandi observations, not guaranteed farm-gate prices.")
