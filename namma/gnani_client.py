from __future__ import annotations

import requests
import uuid
from typing import Any

from .config import STT_URL, TTS_URL


class GnaniAPIError(RuntimeError):
    """Raised when a Gnani API request fails."""


def transcribe_audio(
    audio_bytes: bytes,
    filename: str,
    api_key: str,
    language_code: str = "kn-IN",
    *,
    model: str = "prisma-v2.5",
    output_format: str | None = None,
    keywords: list[str] | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    """Transcribe a short recording with Prisma v2.5 or optional v3.0.

    Prisma v2.5 remains the default and is selected by omitting ``model``.
    Prisma v3.0 accepts ``indic-auto`` for language detection and additional
    context fields such as ``format=codemix``, ``keywords`` and ``topic``.
    """
    if not audio_bytes:
        raise ValueError("The audio file is empty.")

    request_id = str(uuid.uuid4())
    headers = {
        "X-API-Key-ID": api_key,
        "X-API-Request-ID": request_id,
    }
    files = {"audio_file": (filename, audio_bytes, _content_type(filename))}
    data: dict[str, Any] = {"language_code": language_code}
    if model == "prisma-v3.0":
        data["model"] = model
        data["format"] = output_format or "codemix"
        if keywords:
            data["keywords"] = ",".join(keywords[:200])
        if topic:
            data["topic"] = topic[:1600]
    else:
        # Preserve Prisma v2.5's documented request shape.
        data["format"] = output_format or "transcribe"

    try:
        response = requests.post(
            STT_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=(10, 90),
        )
    except requests.RequestException as exc:
        raise GnaniAPIError(f"Could not reach Gnani Prisma: {exc}") from exc

    if not response.ok:
        raise GnaniAPIError(_read_api_error(response))

    try:
        body = response.json()
    except ValueError as exc:
        raise GnaniAPIError("Gnani Prisma returned a response that was not valid JSON.") from exc

    if not body.get("success"):
        error = body.get("error") or {}
        message = error.get("message") or body.get("message") or "Prisma transcription failed."
        raise GnaniAPIError(f"{message} (request id: {body.get('request_id') or request_id})")

    transcript = str(body.get("transcript", "")).strip()
    if not transcript:
        raise GnaniAPIError(
            f"Prisma did not detect speech. Try a clearer or longer recording. "
            f"(request id: {body.get('request_id') or request_id})"
        )
    # Keep non-secret telemetry so the UI can prove that a provider response
    # was received. Never include the API key in this metadata.
    body["_gnani_http_status"] = response.status_code
    body["_gnani_request_id"] = body.get("request_id") or request_id
    body["_gnani_model"] = body.get("model") or model
    body["_gnani_processing_time"] = body.get("processing_time")
    body["_gnani_end_to_end_latency"] = body.get("end_to_end_latency")
    return body


def synthesize_speech_detailed(
    text: str,
    api_key: str,
    language: str = "kn-IN",
    voice: str = "Kavin",
) -> bytes:
    """Create a WAV response with Timbre v2.5 and return safe request metadata."""
    if not text.strip():
        raise ValueError("Text for speech generation cannot be empty.")

    payload = {
        "text": text,
        "voice": voice,
        "model": "timbre-v2.5",
        "language": language,
        "speed": 0.95,
        "audio_config": {
            "sample_rate": 48000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }
    try:
        response = requests.post(
            TTS_URL,
            headers={"X-API-Key-ID": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=(10, 90),
        )
    except requests.RequestException as exc:
        raise GnaniAPIError(f"Could not reach Gnani Timbre: {exc}") from exc

    if not response.ok:
        raise GnaniAPIError(_read_api_error(response))
    if not response.content:
        raise GnaniAPIError("Timbre returned an empty audio response.")
    metadata = {
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type", "application/octet-stream"),
        "audio_bytes": len(response.content),
        "model": "timbre-v2.5",
        "language": language,
        "voice": voice,
    }
    return response.content, metadata


def synthesize_speech(
    text: str,
    api_key: str,
    language: str = "kn-IN",
    voice: str = "Kavin",
) -> bytes:
    """Backward-compatible helper returning only generated audio bytes."""
    audio, _metadata = synthesize_speech_detailed(text, api_key, language, voice)
    return audio


def _content_type(filename: str) -> str:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else "wav"
    return {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
    }.get(suffix, "application/octet-stream")


def _read_api_error(response: requests.Response) -> str:
    try:
        body = response.json()
        detail = body.get("detail") or {}
        error = body.get("error") or {}
        message = (
            detail.get("message")
            or error.get("message")
            or body.get("message")
            or body.get("detail")
        )
        if message:
            return f"Gnani API returned HTTP {response.status_code}: {message}"
    except ValueError:
        pass
    return f"Gnani API returned HTTP {response.status_code}: {response.text[:300]}"
