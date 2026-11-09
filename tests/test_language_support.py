from __future__ import annotations

from namma.config import LANGUAGES, LANGUAGE_CODE_MAP, FULL_ASSISTANT_LANGUAGES
from namma.language_utils import detect_script_language, normalize_language_code
from namma.gnani_client import transcribe_audio
import pytest


def test_all_ten_gnani_stt_languages_are_configured():
    expected = {"bn", "en", "gu", "hi", "kn", "ml", "mr", "pa", "ta", "te"}
    assert set(LANGUAGE_CODE_MAP) == expected
    assert len(LANGUAGES) == 10
    for language in LANGUAGES.values():
        assert language["stt"].endswith("-IN")
        assert language["tts"].endswith("-IN")
        assert language["voice"]


def test_full_assistant_language_scope_is_explicit():
    assert FULL_ASSISTANT_LANGUAGES == {"kn", "te", "en"}


def test_script_fallback_detects_major_indic_scripts():
    assert detect_script_language("ನಾಳೆ ಮಳೆ ಬರುತ್ತದೆಯೇ?") == "kn"
    assert detect_script_language("రేపు వర్షం పడుతుందా?") == "te"
    assert detect_script_language("आज बारिश होगी क्या?") == "hi"
    assert detect_script_language("Will it rain tomorrow?") == "en"


def test_language_code_normalisation():
    assert normalize_language_code("kn-IN") == "kn"
    assert normalize_language_code("te_in") == "te"
    assert normalize_language_code("indic-auto") is None
    assert normalize_language_code("xx-IN") is None


def test_prisma_v3_request_includes_auto_codemix_fields(monkeypatch):
    calls = {}

    class FakeResponse:
        ok = True
        status_code = 200
        content = b"{}"
        text = ""

        @staticmethod
        def json():
            return {"success": True, "transcript": "ಇವತ್ತು rain ಬರುತ್ತಾ?", "detected_language_code": "kn-IN"}

    def fake_post(url, **kwargs):
        calls["url"] = url
        calls.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("namma.gnani_client.requests.post", fake_post)
    result = transcribe_audio(
        b"fake-audio", "sample.wav", "test-key",
        language_code="indic-auto", model="prisma-v3.0", output_format="codemix",
    )
    assert result["detected_language_code"] == "kn-IN"
    assert calls["data"]["language_code"] == "indic-auto"
    assert calls["data"]["model"] == "prisma-v3.0"
    assert calls["data"]["format"] == "codemix"
    assert calls["headers"]["X-API-Key-ID"] == "test-key"


def test_prisma_v25_does_not_send_v3_model_field(monkeypatch):
    calls = {}

    class FakeResponse:
        ok = True
        status_code = 200
        content = b"{}"
        text = ""

        @staticmethod
        def json():
            return {"success": True, "transcript": "ನಮಸ್ಕಾರ"}

    def fake_post(url, **kwargs):
        calls.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("namma.gnani_client.requests.post", fake_post)
    transcribe_audio(b"fake-audio", "sample.wav", "test-key", "kn-IN", model="prisma-v2.5")
    assert "model" not in calls["data"]
    assert calls["data"]["language_code"] == "kn-IN"


def test_wrong_selected_language_can_be_recovered_from_transcript_script(monkeypatch):
    from web_app import _build_response

    monkeypatch.setattr("web_app.get_gnani_api_key", lambda: None)
    monkeypatch.setattr("web_app.handle_turn", lambda text, language, state: {
        "answer": "రేపు వర్షం పడే అవకాశం ఉంది.", "intent": "weather"
    })
    result = _build_response("రేపు వర్షం పడుతుందా?", "en", {"history": []}, "Gnani Prisma v2.5")
    assert result["detected_language"] == "te"
    assert result["reply_language"] == "te"
    assert result["language_support"] == "full"


def test_beta_language_notice_uses_matching_language_voice(monkeypatch):
    from web_app import _build_response

    monkeypatch.setattr("web_app.get_gnani_api_key", lambda: None)
    result = _build_response("தமிழில் வானிலை எப்படி?", "ta", {"history": []}, "Typed test")
    assert result["language_support"] == "speech-beta"
    assert result["reply_language"] == "ta"
    assert "கன்னடம்" in result["answer"]


def test_translation_bridge_calls_existing_english_service_then_translates_back(monkeypatch):
    from web_app import _build_response
    calls = []

    def fake_translate(text, source, target):
        calls.append((text, source, target))
        if target == "English":
            return "What is today's tomato price?"
        return "தமிழில் மொழிபெயர்க்கப்பட்ட பதில்."

    monkeypatch.setattr("web_app.translation_is_configured", lambda: True)
    monkeypatch.setattr("web_app.translate_text", fake_translate)
    monkeypatch.setattr("web_app.get_gnani_api_key", lambda: None)
    monkeypatch.setattr("web_app.handle_turn", lambda text, language, state: {
        "answer": "The latest tomato price is ₹2,400 per quintal.", "intent": "market",
        "market_rows": [],
    })
    result = _build_response("இன்றைய தக்காளி விலை என்ன?", "ta", {"history": []}, "Gnani Prisma v2.5")
    assert result["language_support"] == "translated"
    assert result["reply_language"] == "ta"
    assert result["answer"] == "தமிழில் மொழிபெயர்க்கப்பட்ட பதில்."
    assert calls[0][1:] == ("Tamil", "English")
    assert calls[1][1:] == ("English", "Tamil")


def test_translation_service_preserves_numbers(monkeypatch):
    from namma.translation_service import translate_text, TranslationServiceError
    monkeypatch.setenv("NAMMAVAANI_TRANSLATION_API_URL", "http://localhost:8001/v1")
    monkeypatch.setenv("NAMMAVAANI_TRANSLATION_MODEL", "test-multilingual-model")
    monkeypatch.delenv("NAMMAVAANI_TRANSLATION_API_KEY", raising=False)

    class FakeResponse:
        ok = True
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "Tomato 1200 rupees"}}]}

    monkeypatch.setattr("namma.translation_service.requests.post", lambda *args, **kwargs: FakeResponse())
    assert translate_text("ಟೊಮೇಟೊ 1200 ರೂಪಾಯಿ", "Kannada", "English") == "Tomato 1200 rupees"

    class BadNumberResponse(FakeResponse):
        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "Tomato 1000 rupees"}}]}

    monkeypatch.setattr("namma.translation_service.requests.post", lambda *args, **kwargs: BadNumberResponse())
    with pytest.raises(TranslationServiceError):
        translate_text("ಟೊಮೇಟೊ 1200 ರೂಪಾಯಿ", "Kannada", "English")


def test_prisma_returns_provider_request_telemetry(monkeypatch):
    calls = {}

    class FakeResponse:
        ok = True
        status_code = 200
        content = b"{}"
        text = ""

        @staticmethod
        def json():
            return {
                "success": True,
                "transcript": "ನಮಸ್ಕಾರ",
                "model": "prisma-v2.5",
                "request_id": "req-test-123",
                "processing_time": 0.2,
            }

    def fake_post(url, **kwargs):
        calls["url"] = url
        calls.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("namma.gnani_client.requests.post", fake_post)
    result = transcribe_audio(b"fake-audio", "sample.wav", "test-key", "kn-IN")
    assert calls["url"] == "https://api.vachana.ai/stt/v3"
    assert calls["headers"]["X-API-Key-ID"] == "test-key"
    assert calls["headers"].get("X-API-Request-ID")
    assert result["_gnani_http_status"] == 200
    assert result["_gnani_request_id"] == "req-test-123"
    assert result["_gnani_model"] == "prisma-v2.5"


def test_timbre_v25_request_matches_official_rest_shape(monkeypatch):
    from namma.gnani_client import synthesize_speech_detailed

    calls = {}

    class FakeResponse:
        ok = True
        status_code = 200
        content = b"RIFF-test-wav"
        headers = {"Content-Type": "audio/wav"}
        text = ""

    def fake_post(url, **kwargs):
        calls["url"] = url
        calls.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("namma.gnani_client.requests.post", fake_post)
    audio, metadata = synthesize_speech_detailed(
        "ನಮಸ್ಕಾರ", "test-key", "kn-IN", "Kavin"
    )
    assert calls["url"] == "https://api.vachana.ai/api/v1/tts/inference"
    assert calls["headers"]["X-API-Key-ID"] == "test-key"
    assert calls["json"]["model"] == "timbre-v2.5"
    assert calls["json"]["language"] == "kn-IN"
    assert calls["json"]["voice"] == "Kavin"
    assert calls["json"]["audio_config"]["sample_rate"] == 48000
    assert audio == b"RIFF-test-wav"
    assert metadata["http_status"] == 200
    assert metadata["audio_bytes"] == len(audio)


def test_timbre_test_endpoint_returns_explicit_live_success(monkeypatch):
    from fastapi.testclient import TestClient
    import web_app

    monkeypatch.setattr("web_app.get_gnani_api_key", lambda: "secret-test-key")
    monkeypatch.setattr(
        "web_app.synthesize_speech_detailed",
        lambda text, key, language, voice: (
            b"RIFF-test",
            {"http_status": 200, "content_type": "audio/wav", "audio_bytes": 9,
             "model": "timbre-v2.5", "language": language, "voice": voice},
        ),
    )
    with TestClient(web_app.app) as client:
        response = client.post("/api/gnani/test-tts", data={"language": "kn"})
    assert response.status_code == 200
    body = response.json()
    assert body["gnani_tts"] is True
    assert body["model"] == "timbre-v2.5"
    assert body["audio_bytes"] == 9
    assert body["voice"] == "Kavin"
