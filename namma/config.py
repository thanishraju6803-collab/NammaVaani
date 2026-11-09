from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False, encoding="utf-8-sig")

DB_PATH = Path(os.getenv("NAMMAVAANI_DB_PATH", str(PROJECT_ROOT / "data" / "namma_vani.db")))
STT_URL = os.getenv("GNANI_STT_URL", "https://api.vachana.ai/stt/v3")
TTS_URL = os.getenv("GNANI_TTS_URL", "https://api.vachana.ai/api/v1/tts/inference")

# Keep Prisma v2.5 as the competition-safe default. Prisma v3.0 is optional
# and enables automatic Indic language detection and the codemix format.
GNANI_STT_MODEL = os.getenv("GNANI_STT_MODEL", "prisma-v2.5").strip().lower()
if GNANI_STT_MODEL not in {"prisma-v2.5", "prisma-v3.0"}:
    GNANI_STT_MODEL = "prisma-v2.5"
GNANI_AUTO_DETECT_ENABLED = GNANI_STT_MODEL == "prisma-v3.0"

# Timbre v2.5 voice catalogue: one preferred voice per supported language.
# These are configurable so a project can change voices after previewing them.
LANGUAGES = {
    "Bengali": {"code": "bn", "stt": "bn-IN", "tts": "bn-IN", "voice": os.getenv("GNANI_TTS_VOICE_BN", "Kirra")},
    "English (India)": {"code": "en", "stt": "en-IN", "tts": "en-IN", "voice": os.getenv("GNANI_TTS_VOICE_EN", "Kaveri")},
    "Gujarati": {"code": "gu", "stt": "gu-IN", "tts": "gu-IN", "voice": os.getenv("GNANI_TTS_VOICE_GU", "Falak")},
    "Hindi": {"code": "hi", "stt": "hi-IN", "tts": "hi-IN", "voice": os.getenv("GNANI_TTS_VOICE_HI", "Nalini")},
    "Kannada": {"code": "kn", "stt": "kn-IN", "tts": "kn-IN", "voice": os.getenv("GNANI_TTS_VOICE_KN", "Kavin")},
    "Malayalam": {"code": "ml", "stt": "ml-IN", "tts": "ml-IN", "voice": os.getenv("GNANI_TTS_VOICE_ML", "Reshma")},
    "Marathi": {"code": "mr", "stt": "mr-IN", "tts": "mr-IN", "voice": os.getenv("GNANI_TTS_VOICE_MR", "Zahira")},
    "Punjabi": {"code": "pa", "stt": "pa-IN", "tts": "pa-IN", "voice": os.getenv("GNANI_TTS_VOICE_PA", "Mehuli")},
    "Tamil": {"code": "ta", "stt": "ta-IN", "tts": "ta-IN", "voice": os.getenv("GNANI_TTS_VOICE_TA", "Asmita")},
    "Telugu": {"code": "te", "stt": "te-IN", "tts": "te-IN", "voice": os.getenv("GNANI_TTS_VOICE_TE", "Suhana")},
}

LANGUAGE_CODE_MAP = {cfg["code"]: name for name, cfg in LANGUAGES.items()}
LANGUAGE_NAMES = {cfg["code"]: name for name, cfg in LANGUAGES.items()}

# Rich NammaVaani answers are fully localised today for these three languages.
# Speech recognition and Timbre voices exist for all ten; the other seven are
# explicitly labelled beta until their complete response translations are tested.
FULL_ASSISTANT_LANGUAGES = {"kn", "te", "en"}

STATUSES = ["New", "Assigned", "In progress", "Resolved"]
PRIORITIES = ["Normal", "High", "Urgent"]

_mandi_csv_setting = Path(os.getenv("NAMMAVAANI_MANDI_CSV", "data/mandi_prices.csv"))
MANDI_CSV_PATH = (
    _mandi_csv_setting if _mandi_csv_setting.is_absolute()
    else PROJECT_ROOT / _mandi_csv_setting
)

# data.gov.in Agmarknet API. Keep this key server-side in .env; never send it
# to the browser. The resource is the official daily mandi price dataset.
DATA_GOV_IN_API_KEY = os.getenv("DATA_GOV_IN_API_KEY", "").strip()
DATA_GOV_IN_MANDI_RESOURCE_ID = os.getenv(
    "DATA_GOV_IN_MANDI_RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070"
).strip()


def get_gnani_api_key() -> str | None:
    """Read key from environment or Streamlit secrets without exposing it."""
    value = os.getenv("GNANI_API_KEY", "").strip()
    if value:
        return value
    try:
        import streamlit as st
        secret_value = st.secrets.get("GNANI_API_KEY", "")
        return str(secret_value).strip() or None
    except Exception:
        return None


def get_gnani_key_source() -> str:
    """Return where a key was found, never the key value itself."""
    if os.getenv("GNANI_API_KEY", "").strip():
        return "environment/.env"
    try:
        import streamlit as st
        if str(st.secrets.get("GNANI_API_KEY", "")).strip():
            return "Streamlit secrets"
    except Exception:
        pass
    return "not configured"
