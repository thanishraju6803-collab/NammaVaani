from __future__ import annotations

from namma import voice_assistant as va


def test_letter_flow_builds_safe_mro_request(monkeypatch):
    monkeypatch.setattr(va, "get_farmer_profile", lambda: {
        "location": "Bengaluru, Karnataka, India", "district": "Bengaluru Urban",
        "soil_type": "Unknown", "irrigation": "Unknown",
    })
    saved = {}
    monkeypatch.setattr(va, "create_ticket", lambda data: "NV-TEST01")
    state = {"flow": None}
    first = va.handle_turn("Write a letter to MRO asking pesticide guidance for my tomato crop", "en", state)
    assert first["intent"] == "letter"
    assert "pest or crop-protection" in first["answer"].lower()
    second = va.handle_turn("Leaves are turning yellow and small insects are visible", "en", state)
    assert "village" in second["answer"].lower()
    third = va.handle_turn("Anekal", "en", state)
    assert "draft letter" in third["answer"].lower()
    final = va.handle_turn("yes", "en", state)
    assert "letter_text" in final
    assert "Mandal Revenue Officer" in final["letter_text"]
    assert "tomato" in final["letter_text"].lower()
    assert "approved product" in final["letter_text"].lower()


def test_repair_flow_confirms_before_ticket(monkeypatch):
    monkeypatch.setattr(va, "get_farmer_profile", lambda: {
        "location": "Bengaluru, Karnataka, India", "district": "Bengaluru Urban",
    })
    created = []
    monkeypatch.setattr(va, "create_ticket", lambda data: created.append(data) or "NV-ABC123")
    state = {"flow": None}
    first = va.handle_turn("My borewell motor is not working", "en", state)
    assert "village" in first["answer"].lower()
    second = va.handle_turn("Anekal", "en", state)
    assert "correct" in second["answer"].lower()
    assert not created
    final = va.handle_turn("yes", "en", state)
    assert final["ticket_id"] == "NV-ABC123"
    assert len(created) == 1


def test_market_query_asks_commodity_when_missing(monkeypatch):
    monkeypatch.setattr(va, "get_farmer_profile", lambda: {"district": "Bengaluru Urban"})
    state = {"flow": None}
    result = va.handle_turn("What is today's mandi price?", "en", state)
    assert result["intent"] == "market"
    assert state["flow"] == {"type": "market", "slot": "commodity"}
    assert "which commodity" in result["answer"].lower()


def test_unknown_request_explains_supported_actions(monkeypatch):
    monkeypatch.setattr(va, "get_farmer_profile", lambda: {})
    state = {"flow": None}
    result = va.handle_turn("Hello", "kn", state)
    assert result["intent"] == "general"
    assert "ಹವಾಮಾನ" in result["answer"]


def test_saved_consent_gps_avoids_asking_for_village(monkeypatch):
    monkeypatch.setattr(va, "get_farmer_profile", lambda: {
        "location": "Bengaluru, Karnataka, India", "district": "Bengaluru Urban",
        "village": "", "taluk": "", "gps_consent": True,
        "latitude": 12.75, "longitude": 77.70,
    })
    captured = {}
    def fake_weather(location, language, profile=None):
        captured["location"] = location
        captured["coordinates"] = (profile["latitude"], profile["longitude"])
        return "Forecast ready", {"source": "Open-Meteo"}
    monkeypatch.setattr(va, "_weather_answer", fake_weather)
    state = {"flow": None}
    result = va.handle_turn("What is the weather today?", "en", state)
    assert result["intent"] == "weather"
    assert captured["location"] == "Bengaluru Urban"
    assert captured["coordinates"] == (12.75, 77.70)
