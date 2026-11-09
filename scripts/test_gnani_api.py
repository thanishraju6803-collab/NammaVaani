from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from namma.config import LANGUAGES, LANGUAGE_CODE_MAP, get_gnani_api_key, get_gnani_key_source  # noqa: E402
from namma.gnani_client import GnaniAPIError, synthesize_speech_detailed, transcribe_audio  # noqa: E402

TEST_PHRASES = {
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
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify real Gnani Timbre and optionally Prisma API access. Never prints your API key."
    )
    parser.add_argument("--language", default="kn", choices=sorted(LANGUAGE_CODE_MAP))
    parser.add_argument("--audio", help="Optional local WAV/MP3/OGG/FLAC/M4A/AAC file for a real Prisma test")
    args = parser.parse_args()

    key = get_gnani_api_key()
    print(f"Project folder: {ROOT}")
    print(f".env exists: {(ROOT / '.env').is_file()}")
    print(f"API key loaded: {'YES' if key else 'NO'}")
    print(f"Key source: {get_gnani_key_source()}")
    if not key:
        print("FAIL: FastAPI/Python cannot read GNANI_API_KEY from this project's .env.")
        print("Put GNANI_API_KEY=your_key in the .env beside web_app.py. Do not share the key.")
        return 2

    cfg = next(v for v in LANGUAGES.values() if v["code"] == args.language)
    print("\n[1/2] Testing Gnani Timbre v2.5 (this is one real API request and may consume credits)...")
    try:
        audio, meta = synthesize_speech_detailed(
            TEST_PHRASES[args.language], key, cfg["tts"], cfg["voice"]
        )
        out = ROOT / f"gnani_timbre_test_{args.language}.wav"
        out.write_bytes(audio)
        print("TTS RESULT: SUCCESS")
        print(f"HTTP status: {meta['http_status']}")
        print(f"Model: {meta['model']}")
        print(f"Voice: {meta['voice']} ({meta['language']})")
        print(f"Audio bytes: {len(audio)}")
        print(f"Saved test audio: {out}")
    except GnaniAPIError as exc:
        print("TTS RESULT: FAILED")
        print(str(exc))
        print("If HTTP 401/403 appears, check the API key, organisation status and TTS scope.")
        print("If HTTP 402 appears, check available programme credits.")
        return 3

    if not args.audio:
        print("\nPrisma was not tested because --audio was not supplied.")
        print("To test both APIs, record a short WAV and run:")
        print(f'python scripts/test_gnani_api.py --language {args.language} --audio "C:\\path\\to\\sample.wav"')
        return 0

    audio_path = Path(args.audio).expanduser().resolve()
    if not audio_path.is_file():
        print(f"Audio file not found: {audio_path}")
        return 4

    print("\n[2/2] Testing Gnani Prisma v2.5 (this is one real API request and may consume credits)...")
    try:
        body = transcribe_audio(
            audio_path.read_bytes(), audio_path.name, key, cfg["stt"], model="prisma-v2.5"
        )
        print("STT RESULT: SUCCESS")
        print(f"HTTP status: {body.get('_gnani_http_status')}")
        print(f"Model: {body.get('_gnani_model')}")
        print(f"Request ID: {body.get('_gnani_request_id')}")
        print(f"Processing time: {body.get('_gnani_processing_time')}")
        print(f"Transcript: {body.get('transcript')}")
    except GnaniAPIError as exc:
        print("STT RESULT: FAILED")
        print(str(exc))
        print("Check language selection, API key STT scope, audio format and duration (max 30 seconds).")
        return 5

    print("\nBoth Gnani APIs returned successful responses.")
    print("If credits still do not appear, verify that this key belongs to the same app.gnani.ai account used for the competition credits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
