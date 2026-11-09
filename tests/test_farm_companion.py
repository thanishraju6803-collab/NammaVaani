from namma.farm_data import crop_basket, zone_context
from namma.conversation import (
    classify_intent, detect_commodity, parse_soil, parse_irrigation,
    crop_followup, crop_advisory_text,
)
from namma.weather_service import weather_code_label
from namma.market_service import load_mandi_prices, save_mandi_csv, MarketDataError


def test_zone_v_crop_basket_is_grounded_and_not_empty():
    crops = crop_basket("kn")
    assert any(c["english_name"] == "Ragi (Finger millet)" for c in crops)
    assert zone_context()["zone"] == "Zone V"
    assert all(c["note"] for c in crops)


def test_multilingual_intent_and_commodity_detection():
    assert classify_intent("ನನ್ನ ಜಮೀನಿಗೆ ಯಾವ ಬೆಳೆ ಸೂಕ್ತ?") == "crop"
    assert classify_intent("Tomorrow rain ideya?") == "weather"
    assert classify_intent("ఇవాళ tomato ధర ఎంత?") == "market"
    assert detect_commodity("ಇವತ್ತು tomato price ಎಷ್ಟು") == "Tomato"
    assert detect_commodity("టమాటా మార్కెట్ ధర") == "Tomato"


def test_soil_and_irrigation_parser():
    assert parse_soil("ನಮ್ಮದು ಕೆಂಪು ಮಣ್ಣು") == "Red soil"
    assert parse_soil("ఎర్ర నేల") == "Red soil"
    assert parse_irrigation("ನಮ್ಮಲ್ಲಿ borewell ಇದೆ") == "Borewell"
    assert parse_irrigation("వర్షాధారం") == "Rainfed"


def test_crop_followup_asks_one_missing_question_at_a_time():
    slot, question = crop_followup({}, "kn")
    assert slot == "soil_type"
    assert "ಮಣ್ಣು" in question
    slot, question = crop_followup({"soil_type": "Unknown"}, "te")
    assert slot == "irrigation"
    assert "నీరు" in question
    slot, question = crop_followup({"soil_type": "Red soil", "irrigation": "Borewell"}, "en")
    assert slot is None and question is None


def test_crop_advisory_does_not_claim_best_crop():
    reply = crop_advisory_text({"location": "Anekal", "soil_type": "Red soil", "irrigation": "Borewell"}, "en")
    assert "not a ranking" in reply
    assert "UAS Bengaluru" in reply


def test_weather_code_labels():
    assert weather_code_label(0) == "Clear sky"
    assert weather_code_label(95) == "Thunderstorm"
    assert weather_code_label(None) == "Conditions unavailable"


def test_mandi_csv_missing_file_is_a_clear_error(tmp_path):
    try:
        load_mandi_prices("Tomato", csv_path=tmp_path / "not-here.csv")
    except MarketDataError as exc:
        assert "No mandi CSV" in str(exc)
    else:
        raise AssertionError("Missing CSV should not return price data")


def test_farmer_profile_storage_round_trip(tmp_path, monkeypatch):
    from namma import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "farm-profile.db")
    storage.init_db()
    profile = storage.get_farmer_profile()
    profile.update({
        "location": "Anekal, Bengaluru Urban, Karnataka",
        "land_acres": 2.0,
        "soil_type": "Red soil",
        "irrigation": "Borewell",
        "preferred_language": "kn",
    })
    storage.save_farmer_profile(profile)
    saved = storage.get_farmer_profile()
    assert saved["location"].startswith("Anekal")
    assert saved["land_acres"] == 2.0
    assert saved["soil_type"] == "Red soil"
    assert saved["irrigation"] == "Borewell"


def test_weather_service_uses_geocoding_and_returns_attributed_forecast(monkeypatch):
    from namma import weather_service

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    responses = [
        FakeResponse({"results": [{
            "name": "Anekal", "admin1": "Karnataka", "country": "India",
            "country_code": "IN", "latitude": 12.71, "longitude": 77.69,
        }]}),
        FakeResponse({
            "timezone": "Asia/Kolkata",
            "current": {"temperature_2m": 26.0, "relative_humidity_2m": 60},
            "daily": {
                "time": ["2026-11-08"],
                "temperature_2m_max": [29.0],
                "temperature_2m_min": [19.0],
                "precipitation_sum": [1.2],
                "precipitation_probability_max": [40],
                "weather_code": [61],
            },
        }),
    ]
    calls = []
    def fake_get(url, **kwargs):
        calls.append(url)
        return responses.pop(0)
    monkeypatch.setattr(weather_service.requests, "get", fake_get)

    result = weather_service.get_weather_forecast("Anekal")
    assert result["location"]["name"] == "Anekal"
    assert result["daily"][0]["precipitation_probability_max"] == 40
    assert "Open-Meteo" in result["attribution"]
    assert len(calls) == 2


def test_mandi_csv_parses_official_columns_and_filters_district():
    from namma import market_service

    csv_text = (
        "State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min Price,Max Price,Modal Price\n"
        "Karnataka,Bangalore Urban,Yeshwanthapura,Tomato,Local,FAQ,08/11/2026,1800,3000,2400\n"
        "Karnataka,Kolar,Kolar,Tomato,Local,FAQ,08/11/2026,1700,2800,2200\n"
    )
    rows = market_service.load_mandi_prices(
        "Tomato", "Bengaluru Urban", csv_bytes=csv_text.encode("utf-8")
    )
    assert len(rows) == 1
    assert rows[0]["market"] == "Yeshwanthapura"
    assert rows[0]["modal_price"] == 2400.0
    assert rows[0]["unit"] == "₹ / quintal"
    assert rows[0]["record_date"] == "2026-11-08"
    assert rows[0]["source"] == "Agmarknet / data.gov.in CSV"


def test_mandi_csv_accepts_export_header_variations_and_sorts_newest_first():
    csv_text = (
        "State Name,District Name,Market Name,Commodity Name,Variety,Grade,Date,"
        "Min Price (Rs/Quintal),Max Price (Rs/Quintal),Modal Price (Rs/Quintal)\n"
        "Karnataka,Bengaluru Urban,Bangalore APMC,Tomato,Local,FAQ,07-11-2026,1000,2000,1500\n"
        "Karnataka,Bengaluru Urban,Bangalore APMC,Tomato,Local,FAQ,08-11-2026,1200,2200,1700\n"
    )
    rows = load_mandi_prices("Tomato", csv_bytes=csv_text.encode("utf-8"))
    assert len(rows) == 2
    assert rows[0]["record_date"] == "2026-11-08"
    assert rows[0]["modal_price"] == 1700.0


def test_save_mandi_csv_validates_and_persists(tmp_path):
    csv_text = (
        "State,District,Market,Commodity,Arrival_Date,Min Price,Max Price,Modal Price\n"
        "Karnataka,Bengaluru Urban,Anekal,Tomato,08/11/2026,1000,2000,1500\n"
    )
    destination = tmp_path / "mandi_prices.csv"
    saved = save_mandi_csv(csv_text.encode("utf-8"), destination)
    assert saved == destination
    rows = load_mandi_prices("Tomato", csv_path=destination)
    assert rows[0]["market"] == "Anekal"
    assert rows[0]["modal_price"] == 1500.0


def test_save_mandi_csv_rejects_non_agmarknet_file(tmp_path):
    bad_csv = b"name,amount\nTomato,20\n"
    try:
        save_mandi_csv(bad_csv, tmp_path / "bad.csv")
    except MarketDataError as exc:
        assert "does not look like the Agmarknet" in str(exc)
    else:
        raise AssertionError("Invalid CSV should be rejected")



def test_crop_health_intent_wins_over_broad_crop_keyword():
    assert classify_intent("ಬೆಳೆ ಎಲೆಗಳು ಹಳದಿಯಾಗುತ್ತಿವೆ") == "crop_health"
    assert classify_intent("పంట ఆకులు పసుపు రంగులో ఉన్నాయి") == "crop_health"


def test_unknown_soil_and_irrigation_are_accepted_values():
    slot, _ = crop_followup({"soil_type": "Unknown", "irrigation": "Unknown"}, "kn")
    assert slot is None


def test_local_romanised_kannada_and_telugu_phrases():
    from namma.pipeline import extract_fields
    assert classify_intent("Nam borewell motor on agutte, aadre neeru baralla") == "repair"
    fields = extract_fields("Nam borewell motor on agutte, aadre neeru baralla, namma ooru Attibele")
    assert fields["equipment"] == "Borewell pump / motor"
    assert fields["problem"] == "Running but no water output"
    assert fields["village"] == "Attibele"
    assert classify_intent("ivattu male barutta?") == "weather"
    assert classify_intent("tamota rate eshtu?") == "market"
    assert detect_commodity("namma tamota ge rate eshtu") == "Tomato"
    assert parse_soil("namma holadalli kempu mannu ide") == "Red soil"
    assert parse_irrigation("namma boru ide") == "Borewell"


def test_mandi_api_returns_cleaned_official_records(monkeypatch):
    from datetime import date, timedelta
    from namma import market_service

    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {"records": [{
                "state": "Karnataka", "district": "Bengaluru Urban", "market": "Anekal",
                "commodity": "Tomato", "variety": "Local", "grade": "FAQ",
                "arrival_date": (date.today() - timedelta(days=1)).strftime("%d/%m/%Y"),
                "min_price": "1800", "max_price": "2400", "modal_price": "2100",
            }]}

    class FakeSession:
        def __init__(self):
            self.calls = []
        def get(self, url, params, timeout):
            self.calls.append((url, params, timeout))
            return FakeResponse()

    fake = FakeSession()
    rows = market_service.fetch_mandi_api_prices(
        "Tomato", "Bengaluru Urban", api_key="test-key", session=fake
    )
    assert rows[0]["market"] == "Anekal"
    assert rows[0]["modal_price"] == 2100
    assert rows[0]["source"] == "Agmarknet / data.gov.in API"
    assert fake.calls[0][1]["api-key"] == "test-key"
    assert fake.calls[0][1]["filters[commodity]"] == "Tomato"


def test_mandi_api_failure_uses_csv_backup(monkeypatch):
    from namma import market_service
    csv_data = (
        "State,District,Market,Commodity,Arrival_Date,Min Price,Max Price,Modal Price\n"
        "Karnataka,Bengaluru Urban,Anekal,Tomato,08/11/2026,1800,2400,2100\n"
    ).encode()
    monkeypatch.setattr(market_service, "DATA_GOV_IN_API_KEY", "example-key")
    monkeypatch.setattr(
        market_service, "fetch_mandi_api_prices",
        lambda **kwargs: (_ for _ in ()).throw(MarketDataError("API unavailable")),
    )
    rows = market_service.load_mandi_prices(
        "Tomato", "Bengaluru Urban", csv_bytes=csv_data
    )
    assert rows[0]["source"] == "Agmarknet / data.gov.in CSV"
    assert "API unavailable" in rows[0]["fallback_note"]


def test_farmer_profile_keeps_location_hierarchy_and_gps_consent(tmp_path, monkeypatch):
    from namma import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "hierarchy.db")
    storage.init_db()
    profile = storage.get_farmer_profile()
    profile.update({
        "state": "Karnataka", "district": "Bengaluru Urban", "taluk": "Anekal",
        "hobli": "Attibele", "village": "Bidaraguppe", "gps_consent": True,
        "latitude": 12.75, "longitude": 77.70,
    })
    storage.save_farmer_profile(profile)
    saved = storage.get_farmer_profile()
    assert saved["state"] == "Karnataka"
    assert saved["district"] == "Bengaluru Urban"
    assert saved["taluk"] == "Anekal"
    assert saved["hobli"] == "Attibele"
    assert saved["village"] == "Bidaraguppe"
    assert saved["gps_consent"] is True
    assert saved["latitude"] == 12.75


def test_weather_uses_gps_only_when_coordinates_are_provided(monkeypatch):
    from namma import weather_service
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {
                "timezone": "Asia/Kolkata",
                "current": {"temperature_2m": 25},
                "daily": {"time": [], "temperature_2m_max": [], "temperature_2m_min": [],
                          "precipitation_sum": [], "precipitation_probability_max": [], "weather_code": []},
            }

    def fake_get(url, params, timeout):
        captured.update(params)
        return FakeResponse()

    monkeypatch.setattr(weather_service.requests, "get", fake_get)
    result = weather_service.get_weather_forecast("Bidaraguppe", coordinates=(12.75, 77.70))
    assert captured["latitude"] == 12.75
    assert captured["longitude"] == 77.70
    assert result["location"]["match_method"] == "consented farm GPS"


def test_profile_endpoint_saves_hierarchy_and_clears_gps_without_consent(monkeypatch):
    import web_app
    saved = {}
    monkeypatch.setattr(web_app, "get_farmer_profile", lambda: {
        "state": "Karnataka", "district": "Bengaluru Urban", "location": "Bengaluru, Karnataka, India",
        "gps_consent": True, "latitude": 12.0, "longitude": 77.0,
    })
    monkeypatch.setattr(web_app, "save_farmer_profile", lambda profile: saved.update(profile))
    payload = web_app.ProfileUpdate(
        state="Karnataka", district="Bengaluru Urban", taluk="Anekal",
        hobli="Attibele", village="Bidaraguppe", gps_consent=False,
        latitude=12.75, longitude=77.70,
    )
    result = web_app.update_profile(payload)
    assert result["profile"]["location"] == "Bidaraguppe, Attibele, Anekal, Bengaluru Urban, Karnataka, India"
    assert saved["latitude"] is None and saved["longitude"] is None
    assert saved["gps_consent"] is False


def test_profile_endpoint_requires_valid_gps_when_consent_is_on(monkeypatch):
    from fastapi import HTTPException
    import web_app
    monkeypatch.setattr(web_app, "get_farmer_profile", lambda: {"state": "Karnataka", "district": "Anekal"})
    monkeypatch.setattr(web_app, "save_farmer_profile", lambda profile: None)
    payload = web_app.ProfileUpdate(gps_consent=True, latitude=12.5)
    try:
        web_app.update_profile(payload)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "coordinates" in str(exc.detail)
    else:
        raise AssertionError("GPS consent without both coordinates should be rejected")


def test_kannada_spoken_repair_phrase_extracts_village_and_problem():
    from namma.pipeline import extract_fields
    fields = extract_fields("ನಮ್ಮ ಬೋರ್‌ವೆಲ್ ಮೋಟಾರ್ ಓಡುತ್ತಿದೆ, ಆದರೆ ನೀರು ಬರ್ತಿಲ್ಲ. ನಮ್ಮ ಊರು ಅತ್ತಿಬೆಲೆ.")
    assert fields["equipment"] == "Borewell pump / motor"
    assert fields["problem"] == "Running but no water output"
    assert fields["village"] == "ಅತ್ತಿಬೆಲೆ"
    assert fields["operating_condition"] == "Motor is running"
