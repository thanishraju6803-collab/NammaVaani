from __future__ import annotations

import re
from typing import Any

from .conversation import (
    classify_intent, crop_advisory_text, crop_followup, detect_commodity,
    localized, market_question, weather_question,
)
from .farm_data import crop_basket
from .market_service import MarketDataError, load_mandi_prices
from .pipeline import extract_fields, ticket_summary
from .storage import create_ticket, get_farmer_profile, save_farmer_profile
from .weather_service import WeatherServiceError, get_weather_forecast


def _yes(text: str) -> bool:
    t = text.casefold().strip()
    return any(x in t for x in ["yes", "yeah", "correct", "ಹೌದು", "ಸರಿ", "ಆಯಿತು", "ಹೌದು ಸರಿ", "howdu", "haudu", "sari", "aytu", "ಆಯ್ತು", "అవును", "సరే", "ఔను", "avunu", "sare"])


def _no(text: str) -> bool:
    t = text.casefold().strip()
    return any(x in t for x in ["no", "wrong", "not correct", "ಬೇಡ", "ಇಲ್ಲ", "ತಪ್ಪು", "illa", "illa beda", "kaadu", "beda", "ledu", "kaadu", "కాదు", "వద్దు", "తప్పు"])


def _find_crop(text: str) -> str | None:
    # Reuse the farmer-facing commodity vocabulary before checking letter-specific aliases.
    common = detect_commodity(text)
    if common:
        return common.title()
    choices = {
        "Tomato": ["tomato", "ಟೊಮೇಟೊ", "ಟೊಮ್ಯಾಟೊ", "టమాటా", "టొమాటో"],
        "Ragi": ["ragi", "ರಾಗಿ", "రాగి"],
        "Maize": ["maize", "ಮೆಕ್ಕೆಜೋಳ", "మొక్కజొన్న"],
        "Groundnut": ["groundnut", "ಕಡಲೆಕಾಯಿ", "వేరుశెనగ"],
        "Beans": ["beans", "ಬೀನ್ಸ್", "చిక్కుడు", "బీన్స్"],
        "Onion": ["onion", "ಈರುಳ್ಳಿ", "ఉల్లిపాయ"],
        "Potato": ["potato", "ಆಲೂಗಡ್ಡೆ", "బంగాళాదుంప"],
        "Chilli": ["chilli", "ಮೆಣಸಿನಕಾಯಿ", "మిరప", "పచ్చిమిర్చి"],
    }
    low = text.casefold()
    for crop, variants in choices.items():
        if any(v.casefold() in low for v in variants):
            return crop
    return None


def _letter_intent(text: str) -> bool:
    t = text.casefold()
    return any(x in t for x in [
        "write letter", "write an application", "draft letter", "letter to mro", "mro sir",
        "tahsildar", "revenue officer", "ಅರ್ಜಿ", "ಪತ್ರ ಬರೆಯ", "ಪತ್ರ ಬರೆಯಿರಿ", "ಎಂಆರ್‌ಒ",
        "తహసీల్దార్", "ఎంఆర్ఓ", "లేఖ రాయ", "దరఖాస్తు", "letter", "application to officer",
    ])


def _pesticide_context(text: str) -> bool:
    t = text.casefold()
    return any(x in t for x in [
        "pesticide", "pest", "insecticide", "spray", "ಕೀಟನಾಶಕ", "ಕೀಟ", "ಔಷಧಿ", "ಸಿಂಪಡಣೆ",
        "పురుగుమందు", "పురుగు", "మందు", "స్ప్రే",
    ])


def _ask(language: str, slot: str, data: dict[str, Any]) -> str:
    questions = {
        "repair_equipment": (
            "ಯಾವ ಯಂತ್ರದಲ್ಲಿ ತೊಂದರೆ ಇದೆ? ಬೋರ್‌ವೆಲ್ ಮೋಟಾರಾ, ಟ್ರ್ಯಾಕ್ಟರಾ, ಸ್ಪ್ರೇಯರಾ ಅಥವಾ ಬೇರೆ ಯಂತ್ರವಾ?",
            "ఏ యంత్రంలో సమస్య ఉంది? బోర్‌వెల్ మోటారా, ట్రాక్టరా, స్ప్రేయరా లేదా మరేదైనా?",
            "Which machine has the problem: borewell motor, tractor, sprayer or something else?",
        ),
        "repair_problem": (
            "ಯಂತ್ರದಲ್ಲಿ ಏನು ತೊಂದರೆ ಆಗುತ್ತಿದೆ? ಸಾಮಾನ್ಯವಾಗಿ ಹೇಳಿ.",
            "యంత్రంలో ఏమి సమస్య వస్తోంది? మీ మాటల్లో చెప్పండి.",
            "What is going wrong with the machine? Please describe it in your own words.",
        ),
        "repair_village": (
            "ಯಂತ್ರ ಇರುವ ಊರಿನ ಹೆಸರನ್ನು ಹೇಳಿ.",
            "యంత్రం ఉన్న గ్రామం పేరు చెప్పండి.",
            "Which village is the machine located in?",
        ),
        "repair_confirm": (
            f"ನಿಮ್ಮ ದೂರು ಹೀಗಿದೆ: {data.get('equipment')}, {data.get('problem')}, ಸ್ಥಳ {data.get('village')}. ಈ ವಿವರಗಳು ಸರಿಯಾಗಿವೆಯೇ? ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ.",
            f"మీ ఫిర్యాదు: {data.get('equipment')}, {data.get('problem')}, గ్రామం {data.get('village')}. వివరాలు సరైనవేనా? అవును లేదా కాదు అని చెప్పండి.",
            f"Your request is for {data.get('equipment')}: {data.get('problem')}, in {data.get('village')}. Are these details correct? Please say yes or no.",
        ),
        "letter_crop": (
            "ಯಾವ ಬೆಳೆಗೆ ಸಂಬಂಧಿಸಿದ ಮಾಹಿತಿ ಬೇಕು? ಉದಾಹರಣೆಗೆ ಟೊಮೇಟೊ, ರಾಗಿ ಅಥವಾ ಮೆಕ್ಕೆಜೋಳ.",
            "ఏ పంటకు సంబంధించిన సమాచారం కావాలి? ఉదాహరణకు టమాటా, రాగి లేదా మొక్కజొన్న.",
            "Which crop is the letter about, for example tomato, ragi or maize?",
        ),
        "letter_issue": (
            "ಯಾವ ಮಾಹಿತಿ ಬೇಕು? ಬೆಳೆಯಲ್ಲಿ ಯಾವ ಕೀಟ ಅಥವಾ ತೊಂದರೆ ಕಾಣುತ್ತಿದೆ, ಅಥವಾ ಯಾವ ಬೆಳೆ ಸಂರಕ್ಷಣೆಯ ಬಗ್ಗೆ ತಿಳಿಯಬೇಕು? ಸರಳವಾಗಿ ಹೇಳಿ.",
            "ఏ సమాచారం కావాలి? పంటలో ఏ పురుగు లేదా సమస్య కనిపిస్తోంది, లేక పంట సంరక్షణ గురించి ఏమి తెలుసుకోవాలి? మీ మాటల్లో చెప్పండి.",
            "What information should the letter request? Tell me about the pest or crop-protection guidance you need.",
        ),
        "letter_village": (
            "ನಿಮ್ಮ ಊರಿನ ಹೆಸರನ್ನು ಹೇಳಿ.",
            "మీ గ్రామం పేరు చెప్పండి.",
            "Which village should I mention in the letter?",
        ),
        "letter_confirm": (
            "ನಿಮ್ಮ ವಿವರಗಳ ಆಧಾರದ ಮೇಲೆ ಅಧಿಕಾರಿಗೆ ಮನವಿ ಪತ್ರ ಸಿದ್ಧಪಡಿಸಿದ್ದೇನೆ. ಇದನ್ನು ನೋಡಬೇಕೇ?",
            "మీ వివరాల ఆధారంగా అధికారికి దరఖాస్తు సిద్ధం చేశాను. చూడాలా?",
            "I have prepared a draft letter based on your details. Would you like to review it?",
        ),
    }
    return localized(language, *questions[slot])


def _letter_text(data: dict[str, Any], language: str) -> str:
    crop = data.get("crop") or "ಬೆಳೆ"
    issue = data.get("issue") or "ಬೆಳೆಯಲ್ಲಿ ಕೀಟ / ತೊಂದರೆ ಕಾಣುತ್ತಿದೆ"
    village = data.get("village") or ""
    if language == "kn":
        return (
            "ಗೆ,\nಮಾನ್ಯ ಮಂಡಲ ಆದಾಯಾಧಿಕಾರಿಗಳು (MRO) / ಸಂಬಂಧಿತ ಕೃಷಿ ಅಧಿಕಾರಿ,\n"
            f"{village}\n\nವಿಷಯ: {crop} ಬೆಳೆಯಲ್ಲಿನ ಕೀಟ ಅಥವಾ ತೊಂದರೆಗೆ ಸೂಕ್ತ ಕೃಷಿ ಮಾರ್ಗದರ್ಶನ ಕೋರಿ ಮನವಿ.\n\n"
            "ಮಾನ್ಯರೇ,\n\n"
            f"ನಾನು {village} ಗ್ರಾಮದ ರೈತನು / ರೈತೆಯಾಗಿದ್ದೇನೆ. ನನ್ನ {crop} ಬೆಳೆಯಲ್ಲಿ ಈ ಕೆಳಗಿನ ತೊಂದರೆ ಗಮನಿಸಿದ್ದೇನೆ: {issue}.\n\n"
            "ದಯವಿಟ್ಟು ಕೃಷಿ ಇಲಾಖೆಯ ಅಧಿಕಾರಿ ಅಥವಾ ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರದ ತಜ್ಞರ ಮೂಲಕ ಬೆಳೆಯ ಸಮಸ್ಯೆಯನ್ನು ಪರಿಶೀಲಿಸಿ,"
            " ಸೂಕ್ತ ಮತ್ತು ಅಧಿಕೃತ ಬೆಳೆ ಸಂರಕ್ಷಣಾ ಕ್ರಮಗಳ ಬಗ್ಗೆ ಮಾರ್ಗದರ್ಶನ ನೀಡುವಂತೆ ವಿನಂತಿಸುತ್ತೇನೆ. ಅಗತ್ಯವಿದ್ದರೆ ಮಾತ್ರ"
            " ಅನುಮೋದಿತ ಔಷಧಿ, ಅದರ ಸರಿಯಾದ ಬಳಕೆ, ಸುರಕ್ಷತಾ ಕ್ರಮಗಳು ಮತ್ತು ಕಾಯುವ ಅವಧಿಯ ಬಗ್ಗೆ ಮಾಹಿತಿ ನೀಡಲು ವಿನಂತಿ.\n\n"
            "ಧನ್ಯವಾದಗಳೊಂದಿಗೆ,\nನಿಮ್ಮ ವಿಶ್ವಾಸಿ,\nರೈತರ ಹೆಸರು: __________________\nಗ್ರಾಮ: " + village + "\nದಿನಾಂಕ: ______________\nಸಂಪರ್ಕ: ______________"
        )
    if language == "te":
        return (
            "కు,\nగౌరవనీయులైన మండల రెవెన్యూ అధికారి (MRO) / సంబంధిత వ్యవసాయ అధికారి గారికి,\n"
            f"{village}\n\nవిషయం: {crop} పంటలో కనిపిస్తున్న సమస్యకు తగిన వ్యవసాయ మార్గదర్శకం కోరుతూ దరఖాస్తు.\n\n"
            "గౌరవనీయులైన సర్/మేడమ్,\n\n"
            f"నేను {village} గ్రామానికి చెందిన రైతును. నా {crop} పంటలో ఈ సమస్య కనిపిస్తోంది: {issue}.\n\n"
            "దయచేసి వ్యవసాయ శాఖ అధికారి లేదా కృషి విజ్ఞాన కేంద్రం నిపుణుల ద్వారా పంట సమస్యను పరిశీలించి,"
            " తగిన అధికారిక పంట సంరక్షణ సూచనలు అందించగలరు. అవసరమైతే మాత్రమే ఆమోదిత మందు, సరైన వాడకం,"
            " భద్రతా జాగ్రత్తలు మరియు కోతకు ముందు పాటించాల్సిన గడువు గురించి తెలియజేయండి.\n\n"
            "ధన్యవాదాలు,\nమీ విశ్వాసపాత్రుడు,\nరైతు పేరు: __________________\nగ్రామం: " + village + "\nతేదీ: ______________\nసంప్రదింపు: ______________"
        )
    return (
        "To,\nThe Mandal Revenue Officer (MRO) / Concerned Agriculture Officer,\n"
        f"{village}\n\nSubject: Request for official guidance on a pest or crop-health issue in {crop}.\n\n"
        "Respected Sir/Madam,\n\n"
        f"I am a farmer from {village}. I have noticed the following issue in my {crop} crop: {issue}.\n\n"
        "I request you to arrange guidance from the Agriculture Department or a Krishi Vigyan Kendra expert"
        " to identify the problem and advise appropriate, officially recommended crop-protection measures."
        " If a pesticide is necessary, please provide information on an approved product, correct use,"
        " safety precautions and the pre-harvest waiting period.\n\n"
        "Thank you.\nYours faithfully,\nFarmer name: __________________\nVillage: " + village + "\nDate: ______________\nContact: ______________"
    )


def _weather_answer(
    location: str,
    language: str,
    profile: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    profile = profile or {}
    coordinates = None
    if profile.get("gps_consent") and profile.get("latitude") is not None and profile.get("longitude") is not None:
        coordinates = (float(profile["latitude"]), float(profile["longitude"]))
    result = get_weather_forecast(location, coordinates=coordinates)
    current = result.get("current", {})
    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    rain = current.get("precipitation")
    wind = current.get("wind_speed_10m")
    values = {
        "temp": f"{temp}°C" if temp is not None else "—",
        "humidity": f"{humidity}%" if humidity is not None else "—",
        "rain": f"{rain} mm" if rain is not None else "—",
        "wind": f"{wind} km/h" if wind is not None else "—",
    }
    answer = localized(
        language,
        f"{result['location']['name']} ಹವಾಮಾನ: ತಾಪಮಾನ {values['temp']}, ತೇವಾಂಶ {values['humidity']}, ಈಗಿನ ಮಳೆ {values['rain']}, ಗಾಳಿಯ ವೇಗ {values['wind']}. ಮುಂದಿನ ದಿನಗಳ ಮುನ್ಸೂಚನೆ ಪರದೆಯಲ್ಲಿ ಇದೆ. ಇದು ಹವಾಮಾನ ಅಂದಾಜು; ನಿಮ್ಮ ಹೊಲದ ಸ್ಥಳೀಯ ಪರಿಸ್ಥಿತಿಯನ್ನೂ ಪರಿಶೀಲಿಸಿ.",
        f"{result['location']['name']} వాతావరణం: ఉష్ణోగ్రత {values['temp']}, తేమ {values['humidity']}, ప్రస్తుత వర్షపాతం {values['rain']}, గాలి వేగం {values['wind']}. రాబోయే రోజుల అంచనా తెరపై ఉంది. ఇది అంచనా మాత్రమే; పొలంలోని పరిస్థితిని కూడా పరిశీలించండి.",
        f"Weather near {result['location']['name']}: temperature {values['temp']}, humidity {values['humidity']}, current precipitation {values['rain']}, and wind {values['wind']}. The forecast is shown on screen. This is a forecast, so also check conditions at your field.",
    )
    return answer, result


def _start_repair(text: str, language: str, profile: dict[str, Any], state: dict[str, Any]) -> str:
    fields = extract_fields(text)
    data = {
        "equipment": fields.get("equipment") if fields.get("equipment") != "Other / not clear" else None,
        "problem": fields.get("problem") if fields.get("problem") != "Other / not clear" else None,
        "village": fields.get("village") or (profile.get("location") if profile.get("location") not in {"Bengaluru, Karnataka, India", "Bengaluru Urban"} else None),
        "duration": fields.get("duration"),
        "specification": fields.get("specification"),
        "operating_condition": fields.get("operating_condition"),
        "transcript": text,
    }
    state["flow"] = {"type": "repair", "data": data}
    for slot in ("repair_equipment", "repair_problem", "repair_village"):
        key = slot.replace("repair_", "")
        if not data.get(key):
            state["flow"]["slot"] = key
            return _ask(language, slot, data)
    state["flow"]["slot"] = "confirm"
    return _ask(language, "repair_confirm", data)


def _continue_repair(text: str, language: str, state: dict[str, Any]) -> dict[str, Any]:
    flow = state["flow"]
    data = flow["data"]
    slot = flow.get("slot")
    if slot == "equipment":
        fields = extract_fields(text)
        data["equipment"] = fields.get("equipment") if fields.get("equipment") != "Other / not clear" else text.strip()
    elif slot == "problem":
        fields = extract_fields(text)
        data["problem"] = fields.get("problem") if fields.get("problem") != "Other / not clear" else text.strip()
        data["operating_condition"] = fields.get("operating_condition") or data.get("operating_condition")
    elif slot == "village":
        data["village"] = text.strip()
    elif slot == "confirm":
        if _yes(text):
            ticket_id = create_ticket({
                "village": data["village"], "equipment": data["equipment"], "problem": data["problem"],
                "duration": data.get("duration"), "specification": data.get("specification"),
                "operating_condition": data.get("operating_condition"),
                "description": ticket_summary(data), "priority": "Normal", "language": language,
                "transcript": data.get("transcript", ""),
                "confirmation_text": "Farmer confirmed through voice conversation.",
                "source_mode": "gnani_voice",
            })
            state["flow"] = None
            msg = localized(language,
                f"ನಿಮ್ಮ ದೂರು ದಾಖಲಿಸಲಾಗಿದೆ. ಸಂಖ್ಯೆ {ticket_id}. ಸೇವಾ ಸಿಬ್ಬಂದಿ ಪರಿಶೀಲನೆಗಾಗಿ ಕಾಯಿರಿ.",
                f"మీ ఫిర్యాదు నమోదు అయింది. నంబర్ {ticket_id}. సేవా సిబ్బంది పరిశీలన కోసం వేచి ఉండండి.",
                f"Your request has been recorded. Ticket number {ticket_id}. It is awaiting service review.")
            return {"answer": msg, "intent": "repair", "ticket_id": ticket_id}
        if _no(text):
            state["flow"] = {"type": "repair", "data": data, "slot": "problem"}
            return {"answer": localized(language,
                "ಯಾವ ವಿವರ ತಪ್ಪಾಗಿದೆ? ಸಮಸ್ಯೆಯನ್ನು ಮತ್ತೊಮ್ಮೆ ಹೇಳಿ.",
                "ఏ వివరము తప్పుగా ఉంది? సమస్యను మళ్లీ చెప్పండి.",
                "Which detail is incorrect? Please describe the problem again."), "intent": "repair"}
        return {"answer": localized(language, "ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ.", "అవును లేదా కాదు అని చెప్పండి.", "Please say yes or no."), "intent": "repair"}

    # The next missing required slot is selected after each answer.
    for next_slot in ("equipment", "problem", "village"):
        if not data.get(next_slot):
            flow["slot"] = next_slot
            return {"answer": _ask(language, f"repair_{next_slot}", data), "intent": "repair"}
    flow["slot"] = "confirm"
    return {"answer": _ask(language, "repair_confirm", data), "intent": "repair"}


def _start_letter(text: str, language: str, profile: dict[str, Any], state: dict[str, Any]) -> str:
    data = {
        "crop": _find_crop(text),
        "issue": None,
        "village": profile.get("village") or (profile.get("location") if profile.get("location") not in {"Bengaluru, Karnataka, India", "Bengaluru Urban"} else None),
        "recipient": "MRO / concerned Agriculture Officer",
    }
    state["flow"] = {"type": "letter", "data": data}
    for slot in ("crop", "issue", "village"):
        if not data.get(slot):
            state["flow"]["slot"] = slot
            return _ask(language, f"letter_{slot}", data)
    state["flow"]["slot"] = "confirm"
    return _ask(language, "letter_confirm", data)


def _continue_letter(text: str, language: str, state: dict[str, Any]) -> dict[str, Any]:
    flow = state["flow"]
    data = flow["data"]
    slot = flow.get("slot")
    if slot == "crop":
        data["crop"] = _find_crop(text) or text.strip()
    elif slot == "issue":
        data["issue"] = text.strip()
    elif slot == "village":
        data["village"] = text.strip()
    elif slot == "confirm":
        if _yes(text):
            draft = _letter_text(data, language)
            state["flow"] = None
            return {
                "answer": localized(language, "ನಿಮ್ಮ ಮನವಿ ಪತ್ರದ ಕರಡು ಸಿದ್ಧವಾಗಿದೆ. ಅದನ್ನು ಪರಿಶೀಲಿಸಿ, ಅಗತ್ಯವಿದ್ದರೆ ಹೆಸರು ಮತ್ತು ದಿನಾಂಕ ಸೇರಿಸಿ.", "మీ దరఖాస్తు ముసాయిదా సిద్ధమైంది. పరిశీలించి పేరు, తేదీ జోడించండి.", "Your letter draft is ready. Review it and add your name and date before submitting."),
                "intent": "letter", "letter_text": draft, "download_name": "NammaVaani_MRO_Request.txt",
            }
        if _no(text):
            state["flow"] = {"type": "letter", "data": data, "slot": "issue"}
            return {"answer": localized(language, "ఏ వివరాన్ని మార్చాలి? ಸಮಸ್ಯೆಯನ್ನು మళ్లీ చెప్పండి.", "ఏ వివరాన్ని మార్చాలి? సమస్యను మళ్లీ చెప్పండి.", "Which detail should I change? Please describe the crop issue again."), "intent": "letter"}
        return {"answer": localized(language, "ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ.", "అవును లేదా కాదు అని చెప్పండి.", "Please say yes or no."), "intent": "letter"}
    for next_slot in ("crop", "issue", "village"):
        if not data.get(next_slot):
            flow["slot"] = next_slot
            return {"answer": _ask(language, f"letter_{next_slot}", data), "intent": "letter"}
    flow["slot"] = "confirm"
    return {"answer": _ask(language, "letter_confirm", data), "intent": "letter"}


def handle_turn(text: str, language: str, state: dict[str, Any]) -> dict[str, Any]:
    """Route a farmer's utterance to a verified service or voice conversation flow."""
    text = (text or "").strip()
    if not text:
        return {"answer": localized(language, "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಹೇಳಿ.", "దయచేసి మీ ప్రశ్న అడగండి.", "Please say your question."), "intent": "general"}

    profile = get_farmer_profile()
    flow = state.get("flow")
    if flow and flow.get("type") == "repair":
        return _continue_repair(text, language, state)
    if flow and flow.get("type") == "letter":
        return _continue_letter(text, language, state)
    if flow and flow.get("type") == "weather" and flow.get("slot") == "location":
        state["flow"] = None
        try:
            answer, payload = _weather_answer(text, language)
            return {"answer": answer, "intent": "weather", "weather": payload}
        except WeatherServiceError:
            return {"answer": localized(language, "ಈ ಊರಿನ ಹವಾಮಾನ ಸಿಗಲಿಲ್ಲ. ಹತ್ತಿರದ ಪಟ್ಟಣದ ಹೆಸರನ್ನು ಹೇಳಿ.", "ఈ ప్రాంతపు వాతావరణం అందలేదు. దగ్గర పట్టణం పేరు చెప్పండి.", "I couldn't find that place. Please say a nearby town name."), "intent": "weather"}
    if flow and flow.get("type") == "market" and flow.get("slot") == "commodity":
        commodity = detect_commodity(text)
        if not commodity:
            return {"answer": market_question(language), "intent": "market"}
        state["flow"] = None
        try:
            rows = load_mandi_prices(commodity, profile.get("district") or "Bengaluru Urban", state=profile.get("state") or "Karnataka")
            best = rows[0]
            modal = f"₹{best['modal_price']:,.0f}" if best.get("modal_price") is not None else "not reported"
            answer = localized(language,
                f"{best['market']} ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ {commodity} ಕೊನೆಯ ಲಭ್ಯ ಬೆಲೆ ದಿನಾಂಕ {best['arrival_date']}. ಮಧ್ಯಮ ಬೆಲೆ ಕ್ವಿಂಟಲ್‌ಗೆ {modal}. ಇದು ಮಾರುಕಟ್ಟೆ ವರದಿ ಮಾತ್ರ; ಖಚಿತ ಮಾರಾಟ ಬೆಲೆ ಅಲ್ಲ.",
                f"{best['market']} మార్కెట్‌లో {commodity} చివరి ధర తేదీ {best['arrival_date']}. మోడల్ ధర క్వింటాల్‌కు {modal}. ఇది మార్కెట్ సమాచారం మాత్రమే; ఖచ్చితమైన అమ్మకపు ధర కాదు.",
                f"The latest available {commodity} record for {best['market']} is dated {best['arrival_date']}. The modal price is {modal} per quintal. This is a wholesale market observation, not a guaranteed selling price.")
            return {"answer": answer, "intent": "market", "market_rows": rows[:8]}
        except MarketDataError:
            return {"answer": localized(language, "ಈ ಬೆಳೆಗೆ ಬೆಲೆ ದಾಖಲೆ ಸಿಗಲಿಲ್ಲ. ಹೊಸ Agmarknet CSV ಸೇರಿಸಿ.", "ఈ పంటకు ధర సమాచారం లేదు. తాజా Agmarknet CSV జోడించండి.", "No matching market record was found. Add a newer Agmarknet CSV."), "intent": "market"}
    if flow and flow.get("type") == "crop":
        slot = flow.get("slot")
        if slot == "soil_type":
            from .conversation import parse_soil
            profile["soil_type"] = parse_soil(text)
            save_farmer_profile(profile)
            flow["slot"] = "irrigation"
            return {"answer": _ask(language, "crop_irrigation", {}) if False else localized(language,
                "ನಿಮ್ಮ ಜಮೀನಿಗೆ ನೀರು ಹೇಗೆ ಸಿಗುತ್ತದೆ? ಬೋರ್‌ವೆಲ್, ಕೆರೆ/ಕಾಲುವೆ, ಹನಿ ನೀರಾವರಿ ಅಥವಾ ಮಳೆಯ ನೀರೇ?",
                "మీ పొలానికి నీరు ఎలా వస్తుంది? బోరు, చెరువు/కాలువ, డ్రిప్ లేదా వర్షాధారమా?",
                "How does your farm get water: borewell, canal/tank, drip irrigation or rainfall only?"), "intent": "crop"}
        if slot == "irrigation":
            from .conversation import parse_irrigation
            profile["irrigation"] = parse_irrigation(text)
            save_farmer_profile(profile)
            state["flow"] = None
            return {"answer": crop_advisory_text(profile, language), "intent": "crop", "crop_options": crop_basket(language)}

    if _letter_intent(text):
        return {"answer": _start_letter(text, language, profile, state), "intent": "letter"}

    intent = classify_intent(text)
    if intent == "repair":
        return {"answer": _start_repair(text, language, profile, state), "intent": "repair"}

    if intent == "weather":
        location = profile.get("location")
        has_saved_gps = bool(
            profile.get("gps_consent")
            and profile.get("latitude") is not None
            and profile.get("longitude") is not None
        )
        if (not location or location in {"Bengaluru, Karnataka, India", "Bengaluru Urban"}) and not has_saved_gps:
            explicit = re.search(r"(?:in|at|near|ಊರು|ಗ್ರಾಮ|లో|గ్రామం)\s+([A-Za-z][A-Za-z ]{1,35})", text, re.I)
            if explicit:
                location = explicit.group(1).strip()
            else:
                state["flow"] = {"type": "weather", "slot": "location"}
                return {"answer": weather_question(language), "intent": "weather", "needs_location": True}
        try:
            weather_label = profile.get("village") or profile.get("taluk") or profile.get("district") or ("My farm" if has_saved_gps else location)
            answer, payload = _weather_answer(weather_label, language, profile=profile)
            return {"answer": answer, "intent": "weather", "weather": payload}
        except WeatherServiceError:
            return {"answer": localized(language,
                "ಈ ಸ್ಥಳದ ಹವಾಮಾನ ಈಗ ಸಿಗಲಿಲ್ಲ. ಹಳ್ಳಿಯ ಹೆಸರನ್ನು ಪರಿಶೀಲಿಸಿ ಅಥವಾ ನಂತರ ಪ್ರಯತ್ನಿಸಿ.",
                "ఈ ప్రాంతపు వాతావరణం ఇప్పుడు అందుబాటులో లేదు. గ్రామం పేరును చూసి మళ్లీ ప్రయత్నించండి.",
                "Weather is unavailable for that location right now. Check the village name or try again later."), "intent": "weather"}

    if intent == "market":
        commodity = detect_commodity(text)
        if not commodity:
            state["flow"] = {"type": "market", "slot": "commodity"}
            return {"answer": market_question(language), "intent": "market"}
        try:
            rows = load_mandi_prices(commodity, profile.get("district") or "Bengaluru Urban", state=profile.get("state") or "Karnataka")
            best = rows[0]
            modal = f"₹{best['modal_price']:,.0f}" if best.get("modal_price") is not None else "not reported"
            answer = localized(language,
                f"{best['market']} ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ {commodity} ಕೊನೆಯ ಲಭ್ಯ ಬೆಲೆ ದಿನಾಂಕ {best['arrival_date']}. ಮಧ್ಯಮ ಬೆಲೆ ಕ್ವಿಂಟಲ್‌ಗೆ {modal}. ಇದು ಮಾರುಕಟ್ಟೆ ವರದಿ ಮಾತ್ರ; ಖಚಿತ ಮಾರಾಟ ಬೆಲೆ ಅಲ್ಲ.",
                f"{best['market']} మార్కెట్‌లో {commodity} చివరి ధర తేదీ {best['arrival_date']}. మోడల్ ధర క్వింటాల్‌కు {modal}. ఇది మార్కెట్ సమాచారం మాత్రమే; ఖచ్చితమైన అమ్మకపు ధర కాదు.",
                f"The latest available {commodity} record for {best['market']} is dated {best['arrival_date']}. The modal price is {modal} per quintal. This is a wholesale market observation, not a guaranteed selling price.")
            return {"answer": answer, "intent": "market", "market_rows": rows[:8]}
        except MarketDataError:
            return {"answer": localized(language,
                "ಈ ಬೆಳೆಗೆ ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ದಾಖಲೆ ಈಗ ಲಭ್ಯವಿಲ್ಲ. ಹೊಸ ಅಧಿಕೃತ Agmarknet CSV ಸೇರಿಸಿ ಅಥವಾ ಬೇರೆ ಬೆಳೆ ಕೇಳಿ.",
                "ఈ పంటకు మార్కెట్ ధర సమాచారం అందుబాటులో లేదు. తాజా అధికారిక Agmarknet CSV జోడించండి లేదా మరో పంట అడగండి.",
                "I couldn't find a matching market record from the government API or saved CSV. Check the district and commodity, or upload a newer official Agmarknet CSV."), "intent": "market"}

    if intent == "crop":
        slot, question = crop_followup(profile, language)
        if slot:
            state["flow"] = {"type": "crop", "slot": slot}
            return {"answer": question or "", "intent": "crop"}
        return {"answer": crop_advisory_text(profile, language), "intent": "crop", "crop_options": crop_basket(language)}

    if intent == "crop_health":
        return {"answer": localized(language,
            "ಬೆಳೆ ಹೆಸರು ಮತ್ತು ಲಕ್ಷಣಗಳನ್ನು ಹೇಳಿ. ಸಾಧ್ಯವಾದರೆ ಎಲೆಯ ಫೋಟೋವನ್ನು ಸೇರಿಸಿ. ಇದು ಪ್ರಾಥಮಿಕ ಮಾಹಿತಿ ಮಾತ್ರ; ಔಷಧಿ ಬಳಸುವ ಮೊದಲು KVK ಅಥವಾ ಕೃಷಿ ಅಧಿಕಾರಿಯ ಸಲಹೆ ಪಡೆಯಿರಿ.",
            "పంట పేరు, లక్షణాలు చెప్పండి. సాధ్యమైతే ఆకు ఫోటో జోడించండి. ఇది ప్రాథమిక సమాచారం మాత్రమే; మందు వాడే ముందు KVK లేదా వ్యవసాయ అధికారిని సంప్రదించండి.",
            "Tell me the crop and symptoms, and add a leaf photo if possible. This is preliminary guidance; consult a KVK or agriculture officer before applying chemicals."), "intent": "crop_health"}

    return {"answer": localized(language,
        "ನಿಮಗೆ ಯಾವ ಸಹಾಯ ಬೇಕು ಎಂದು ನನಗೆ ಸ್ಪಷ್ಟವಾಗಲಿಲ್ಲ. ಹವಾಮಾನ, ಬೆಳೆ, ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಅಥವಾ ಯಂತ್ರದ ತೊಂದರೆ — ಯಾವುದರ ಬಗ್ಗೆ ಕೇಳುತ್ತಿದ್ದೀರಿ?",
        "మీకు ఏ సహాయం కావాలో నాకు స్పష్టంగా అర్థం కాలేదు. వాతావరణం, పంట, మార్కెట్ ధర లేదా యంత్ర సమస్య — దేని గురించి అడుగుతున్నారు?",
        "I didn't quite understand. Do you need help with weather, crops, market prices or a machine problem? You can say it in your own words."), "intent": "general"}
