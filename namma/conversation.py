from __future__ import annotations

from typing import Any


COMMODITIES = {
    "tomato": ["tomato", "ಟೊಮೇಟೊ", "ಟೊಮ್ಯಾಟೊ", "టమాటా", "టొమాటో", "tamota", "tamatar"],
    "onion": ["onion", "ಈರುಳ್ಳಿ", "ಉಳ್ಳಿ", "ఉల్లిపాయ", "ullipaya", "ulli"],
    "ragi": ["ragi", "ರಾಗಿ", "రాగి", "raggi"],
    "maize": ["maize", "ಮೆಕ್ಕೆಜೋಳ", "ಮೆಕ್ಕೆ ಜೋಳ", "మొక్కజొన్న", "mokkajonna"],
    "groundnut": ["groundnut", "ಕಡಲೆಕಾಯಿ", "ಕಡಲೆಕಾಯಿ", "వేరుశెనగ", "verusenaga", "kadlekai"],
    "potato": ["potato", "ಆಲೂಗಡ್ಡೆ", "బంగాళాదుంప", "bangaladumpa"],
    "green chilli": ["green chilli", "ಹಸಿಮೆಣಸು", "ಹಸಿ ಮೆಣಸು", "పచ్చిమిర్చి", "pachimirchi"],
    "beans": ["beans", "ಬೀನ್ಸ್", "ಬೀನ್ಸ್", "చిక్కుడు", "chikkudu"],
}


def detect_intent(text: str) -> str:
    t = " ".join((text or "").casefold().replace("’", "'").split())
    # Crop-health phrases must be checked before the broad crop intent.
    if any(x in t for x in ["ಎಲೆ", "ಕಲೆ", "ರೋಗ", "ಹಳದಿ", "yellow", "disease", "leaf", "ఆకు", "పసుపు", "తెగులు"]):
        return "crop_health"
    if any(x in t for x in [
        "ಮೋಟಾರ್", "ಪಂಪ್", "ಟ್ರ್ಯಾಕ್ಟರ್", "ಬೋರ್‌ವೆಲ್", "ಬೋರ್ವೆಲ್", "ಬೋರ್ ವೆಲ್", "ಯಂತ್ರ", "ದೂರು", "ಮೋಟಾರ್ ಕೆಲಸ ಮಾಡ್ತಿಲ್ಲ", "ನೀರು ಬರ್ತಿಲ್ಲ",
        "motor", "motoru", "pump", "pumpu", "tractor", "borewell", "bore well", "boru", "machine", "repair", "complaint", "not working", "kelasa agtilla", "kelasa agalla", "neeru barthilla", "neeru baralla", "neeru bartilla", "neellu ravatledu", "pani cheyyatledu", "panicheyatledu",
        "పంపు", "బోరు", "బోర్‌వెల్", "మోటార్", "ట్రాక్టర్", "యంత్రం", "ఫిర్యాదు", "పని చేయడం లేదు",
    ]):
        return "repair"
    if any(x in t for x in ["ಬೆಲೆ", "ದರ", "price", "market rate", "mandi", "ರೇಟ್", "ಧಾರಣೆ", "ధర", "మార్కెట్ రేట్", "మండి", "price eshtu", "rate eshtu", "bele eshtu", "tomato bele", "tamota rate", "tamatar bhav"]):
        return "market"
    if any(x in t for x in ["ಮಳೆ", "ಹವಾಮಾನ", "weather", "rain", "forecast", "temperature", "వర్షం", "వాతావరణం", "మంచు", "male barutta", "male ideya", "rain ideya", "varsham padutunda"]):
        return "weather"
    if any(x in t for x in ["ಬೆಳೆ", "ಯಾವ ಬೆಳೆ", "crop", "grow", "ಬಿತ್ತನೆ", "ಸೀಸನ್", "season", "పంట", "ఏ పంట", "విత్తనం", "yava bele", "beLe yenu", "pantalu"]):
        return "crop"
    return "general"


def detect_commodity(text: str) -> str | None:
    t = text.casefold()
    for commodity, variants in COMMODITIES.items():
        if any(v.casefold() in t for v in variants):
            return commodity.title()
    return None


def parse_soil(text: str) -> str:
    t = text.casefold()
    if any(x in t for x in ["ಕೆಂಪು", "kempu mannu", "kempu mann", "red soil", "red मिट्टी", "ఎర్ర నేల", "erra nela"]):
        return "Red soil"
    if any(x in t for x in ["ಕಪ್ಪು", "kappu mannu", "black soil", "నల్ల నేల", "nalla nela"]):
        return "Black soil"
    if any(x in t for x in ["ಮರಳು", "maralu mannu", "sandy", "ఇసుక నేల", "isuka nela"]):
        return "Sandy soil"
    if any(x in t for x in ["ಗೊತ್ತಿಲ್ಲ", "ತಿಳಿದಿಲ್ಲ", "gottila", "tilidilla", "don't know", "not sure", "తెలియదు", "teliyadu"]):
        return "Unknown"
    return "Unknown"


def parse_irrigation(text: str) -> str:
    t = text.casefold()
    if any(x in t for x in ["ಬೋರ್", "borewell", "bore well", "boru", "బోరు", "బోర్‌వెల్"]):
        return "Borewell"
    if any(x in t for x in ["ಕೆರೆ", "kere", "ಕಾಲುವೆ", "canal", "tank", "ಕಾಲುವೆ ನೀರು", "కాలువ", "చెరువు", "cheruvu"]):
        return "Canal / tank"
    if any(x in t for x in ["ಮಳೆ", "rainfed", "ಮಳೆಯನ್ನೇ", "వర్షాధారం", "వానపైనే"]):
        return "Rainfed"
    if any(x in t for x in ["drip", "ಹನಿ ನೀರಾವರಿ", "ಹನಿ ನೀರು", "డ్రిప్"]):
        return "Drip irrigation"
    if any(x in t for x in ["ಗೊತ್ತಿಲ್ಲ", "ತಿಳಿದಿಲ್ಲ", "gottila", "tilidilla", "don't know", "not sure", "తెలియదు", "teliyadu"]):
        return "Unknown"
    return "Unknown"


def localized(language: str, kn: str, te: str, en: str) -> str:
    return kn if language == "kn" else te if language == "te" else en


def crop_followup(profile: dict[str, Any], language: str) -> tuple[str | None, str | None]:
    if not profile.get("soil_type"):
        return "soil_type", localized(
            language,
            "ನಿಮ್ಮ ಜಮೀನಿನ ಮಣ್ಣು ಯಾವುದು? ಕೆಂಪು ಮಣ್ಣಾ, ಕಪ್ಪು ಮಣ್ಣಾ, ಮರಳು ಮಣ್ಣಾ? ಗೊತ್ತಿಲ್ಲ ಅಂದರೂ ಹೇಳಬಹುದು.",
            "మీ పొలంలో నేల ఎలా ఉంటుంది? ఎర్ర నేలా, నల్ల నేలా, ఇసుక నేలా? తెలియకపోయినా చెప్పండి.",
            "What kind of soil is in your field: red, black or sandy? It is okay to say you do not know.",
        )
    if not profile.get("irrigation"):
        return "irrigation", localized(
            language,
            "ನಿಮ್ಮ ಜಮೀನಿಗೆ ನೀರು ಹೇಗೆ ಸಿಗುತ್ತದೆ? ಬೋರ್‌ವೆಲ್, ಕೆರೆ/ಕಾಲುವೆ, ಹನಿ ನೀರಾವರಿ ಅಥವಾ ಮಳೆಯ ನೀರೇ?",
            "మీ పొలానికి నీరు ఎలా వస్తుంది? బోరు, చెరువు/కాలువ, డ్రిప్ లేదా వర్షాధారమా?",
            "How does your farm get water: borewell, canal or tank, drip irrigation, or rainfall only?",
        )
    return None, None


def crop_advisory_text(profile: dict[str, Any], language: str) -> str:
    location = profile.get("location") or "Bengaluru Urban"
    soil = profile.get("soil_type") or "Unknown"
    irrigation = profile.get("irrigation") or "Unknown"
    if language == "kn":
        return (
            f"ನಿಮ್ಮ ಸ್ಥಳ {location}, ಮಣ್ಣು {soil}, ನೀರಿನ ವ್ಯವಸ್ಥೆ {irrigation}. UAS ಬೆಂಗಳೂರು ವಲಯ V ಯಲ್ಲಿ ರಾಗಿ, ಮೆಕ್ಕೆಜೋಳ, ಬೇಳೆಕಾಳುಗಳು, ಕಡಲೆಕಾಯಿ, ಹಿಪ್ಪುನೇರಳೆ, ಹಣ್ಣು, ತರಕಾರಿ ಮತ್ತು ಹೂ ಬೆಳೆಗಳನ್ನು ಉಲ್ಲೇಖಿಸಿದೆ. "
            "ಇವು ಸ್ಥಳೀಯವಾಗಿ ಪರಿಶೀಲಿಸಬಹುದಾದ ಬೆಳೆ ಆಯ್ಕೆಗಳು ಮಾತ್ರ; ನಿಮ್ಮ ಹೊಲಕ್ಕೆ ಯಾವುದು ಉತ್ತಮ ಎಂದು ಈ ಮಾಹಿತಿ ಮಾತ್ರದಿಂದ ಖಚಿತಪಡಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ಬಿತ್ತನೆ ತಿಂಗಳು, ಮಣ್ಣಿನ ಪರೀಕ್ಷೆ, ನೀರು, ವೆಚ್ಚ ಮತ್ತು ಮಾರುಕಟ್ಟೆ ಪರಿಶೀಲಿಸಿ UAS/KVK ಸಲಹೆ ಪಡೆಯಿರಿ."
        )
    if language == "te":
        return (
            f"మీ ప్రాంతం {location}, నేల {soil}, నీటి వనరు {irrigation}. UAS బెంగళూరు Zone V లో రాగి, మొక్కజొన్న, పప్పుధాన్యాలు, వేరుశెనగ, మల్బరీ, పండ్లు, కూరగాయలు, పూల పంటలను పేర్కొంది. "
            "ఇవి స్థానికంగా పరిశీలించాల్సిన పంట ఎంపికలు మాత్రమే; ఈ వివరాలతో మీ పొలానికి ఉత్తమ పంటను ఖచ్చితంగా నిర్ణయించలేం. విత్తే నెల, మట్టి పరీక్ష, నీరు, ఖర్చు, మార్కెట్‌ను పరిశీలించి UAS/KVK సలహా తీసుకోండి."
        )
    return (
        f"Your farm profile says location: {location}, soil: {soil}, water: {irrigation}. UAS Bengaluru lists ragi, maize, pulses, groundnut, mulberry, fruits, vegetables and flowers among crops for Zone V. "
        "These are local crop options to investigate, not a ranking or a guaranteed recommendation for your plot. Check the sowing month, soil test, water, costs and market access with UAS/KVK guidance before choosing."
    )


def weather_question(language: str) -> str:
    return localized(language,
        "ನಿಮ್ಮ ಊರು ಅಥವಾ ಹಳ್ಳಿಯ ಹೆಸರನ್ನು ಹೇಳಿ. ಆ ಸ್ಥಳದ ಹವಾಮಾನ ನೋಡುತ್ತೇನೆ.",
        "మీ గ్రామం లేదా పట్టణం పేరు చెప్పండి. ఆ ప్రాంతపు వాతావరణం చూస్తాను.",
        "Which village or town should I check the weather for?",
    )


def market_question(language: str) -> str:
    return localized(language,
        "ಯಾವ ಬೆಳೆ ಅಥವಾ ತರಕಾರಿಯ ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಬೇಕು? ಉದಾ: ಟೊಮೇಟೊ, ಈರುಳ್ಳಿ, ರಾಗಿ.",
        "ఏ పంట లేదా కూరగాయ మార్కెట్ ధర కావాలి? ఉదా: టమాటా, ఉల్లిపాయ, రాగి.",
        "Which commodity price do you want: for example tomato, onion or ragi?",
    )

# Public name used by the app's router.
classify_intent = detect_intent
