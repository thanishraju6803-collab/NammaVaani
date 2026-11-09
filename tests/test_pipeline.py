from namma.pipeline import extract_fields, clarification_questions


def test_kannada_english_borewell_example():
    text = (
        "Nanna borewell motor three days inda work agtilla. "
        "It is a 5 HP motor. Kattigenahalli alli ide."
    )
    fields = extract_fields(text)
    assert fields["equipment"] == "Borewell pump / motor"
    assert fields["problem"] == "Not starting / not working"
    assert fields["duration"] == "3 days"
    assert fields["specification"] == "5 HP"
    assert fields["village"] == "Kattigenahalli"
    assert "equipment" not in fields["missing_fields"]
    assert "problem" not in fields["missing_fields"]
    assert "village" not in fields["missing_fields"]


def test_missing_fields_prompt_clarification():
    fields = extract_fields("Motor is not working. Please send someone.")
    questions = clarification_questions(fields)
    assert any("village" in q.lower() for q in questions)


def test_ticket_storage_round_trip(tmp_path, monkeypatch):
    from namma import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    storage.init_db()
    ticket_id = storage.create_ticket({
        "language": "Kannada",
        "village": "Kattigenahalli",
        "equipment": "Borewell pump / motor",
        "problem": "Not starting / not working",
        "duration": "3 days",
        "transcript": "synthetic test transcript",
        "source_mode": "demo",
    })
    ticket = storage.get_ticket(ticket_id)
    assert ticket is not None
    assert ticket["village"] == "Kattigenahalli"
    storage.update_ticket(ticket_id, "Assigned", "Demo Technician")
    ticket = storage.get_ticket(ticket_id)
    assert ticket["status"] == "Assigned"
    assert ticket["technician"] == "Demo Technician"


def test_kannada_script_borewell_request():
    text = "ನಮ್ಮ ಬೋರ್‌ವೆಲ್ ಮೋಟಾರ್ ಮೂರು ದಿನಗಳಿಂದ ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ. ನಮ್ಮ ಊರು ಅತ್ತಿಬೆಲೆ."
    fields = extract_fields(text)
    assert fields["equipment"] == "Borewell pump / motor"
    assert fields["problem"] == "Not starting / not working"
    assert fields["duration"] == "3 days"
    assert fields["village"] == "ಅತ್ತಿಬೆಲೆ"
