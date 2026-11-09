from __future__ import annotations

import os
import re
from typing import Any

import requests


class TranslationServiceError(RuntimeError):
    """Raised when the optional multilingual translation service fails."""


def _settings() -> tuple[str, str, str]:
    base_url = os.getenv("NAMMAVAANI_TRANSLATION_API_URL", "").strip()
    api_key = os.getenv("NAMMAVAANI_TRANSLATION_API_KEY", "").strip()
    model = os.getenv("NAMMAVAANI_TRANSLATION_MODEL", "").strip()
    return base_url, api_key, model


def translation_is_configured() -> bool:
    base_url, _, model = _settings()
    return bool(base_url and model)


def _chat_completions_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    return base_url + "/chat/completions"


def _digit_tokens(text: str) -> list[str]:
    # Preserve numeric facts such as prices, dates, land sizes, HP, and quantities.
    return re.findall(r"(?<![\w])\d[\d,]*(?:\.\d+)?", text or "")


def translate_text(text: str, source_language: str, target_language: str) -> str:
    """Translate one short conversational turn via an OpenAI-compatible model.

    Configure an OpenAI-compatible chat-completions endpoint. This may be a
    self-hosted Evon v3.3 deployment or another multilingual model. The model
    is used for language bridging only; factual crop/weather/price content is
    still retrieved and validated by NammaVaani's services.
    """
    if not text or not text.strip():
        return text
    base_url, api_key, model = _settings()
    if not base_url or not model:
        raise TranslationServiceError("Multilingual translation is not configured.")

    system_prompt = (
        "You are a faithful translation layer for a farmer-support application. "
        "Translate the user's text from the source language into the target language. "
        "Use simple, natural language a rural farmer can understand. Preserve crop names, "
        "village names, people names, measurements, dates, prices, quantities, units, "
        "and all digits exactly. Do not answer the question, add advice, infer missing "
        "facts, or change the meaning. Return only the translated text."
    )
    user_prompt = (
        f"Source language: {source_language}\n"
        f"Target language: {target_language}\n"
        "Text to translate:\n"
        f"{text.strip()}"
    )
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload: dict[str, Any] = {
        "model": model,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        response = requests.post(
            _chat_completions_url(base_url),
            headers=headers,
            json=payload,
            timeout=(10, 45),
        )
    except requests.RequestException as exc:
        raise TranslationServiceError(f"Could not reach the translation model: {exc}") from exc

    if not response.ok:
        raise TranslationServiceError(
            f"Translation model returned HTTP {response.status_code}: {response.text[:240]}"
        )
    try:
        body = response.json()
        translated = str(body["choices"][0]["message"]["content"]).strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise TranslationServiceError("Translation model returned an unexpected response.") from exc

    if not translated:
        raise TranslationServiceError("Translation model returned an empty translation.")
    if _digit_tokens(text) != _digit_tokens(translated):
        raise TranslationServiceError("Translation changed one or more numbers. The answer was not used for safety.")
    return translated
