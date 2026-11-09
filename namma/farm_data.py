from __future__ import annotations

from typing import Any

# This is a regional crop basket, not a crop ranking or a planting prescription.
# It is based on UAS Bengaluru's Agro-climatic Zones page, which lists the
# Bengaluru Urban districts in Zone V and lists these crop groups for that zone.
# Crop-specific sowing dates, seed rates, varieties and protection practices
# must be fetched from the current UASB Package of Practices / KVK guidance.
UASB_ZONE_V_CROPS: list[dict[str, Any]] = [
    {
        "name": "Ragi (Finger millet)",
        "kn": "ರಾಗಿ",
        "te": "రాగి",
        "group": "Millets",
        "note_en": "Listed among Zone V crops. Check the locally recommended sowing window and variety before planting.",
        "note_kn": "ವಲಯ V ಯಲ್ಲಿ ಉಲ್ಲೇಖಿಸಿರುವ ಬೆಳೆ. ಬಿತ್ತನೆ ಸಮಯ ಮತ್ತು ತಳಿಗೆ ಸ್ಥಳೀಯ ಕೃಷಿ ಸಲಹೆ ಪರಿಶೀಲಿಸಿ.",
        "note_te": "జోన్ V పంటలలో రాగి ఉంది. విత్తే సమయం, రకాన్ని స్థానిక వ్యవసాయ సలహాతో నిర్ధారించండి.",
    },
    {
        "name": "Maize",
        "kn": "ಮೆಕ್ಕೆಜೋಳ",
        "te": "మొక్కజొన్న",
        "group": "Cereals",
        "note_en": "Listed among Zone V crops. Suitability depends on sowing window, soil and water availability.",
        "note_kn": "ವಲಯ V ಯಲ್ಲಿ ಉಲ್ಲೇಖಿಸಿರುವ ಬೆಳೆ. ಬಿತ್ತನೆ ಕಾಲ, ಮಣ್ಣು ಮತ್ತು ನೀರಿನ ಲಭ್ಯತೆ ಪರಿಶೀಲಿಸಿ.",
        "note_te": "జోన్ V పంటలలో మొక్కజొన్న ఉంది. విత్తే కాలం, నేల, నీటి లభ్యతను పరిశీలించండి.",
    },
    {
        "name": "Pulses",
        "kn": "ಬೇಳೆಕಾಳುಗಳು",
        "te": "పప్పుధాన్యాలు",
        "group": "Pulses",
        "note_en": "The zone profile lists pulses as a crop group. Select the pulse and variety using current local guidance.",
        "note_kn": "ಈ ವಲಯದ ಬೆಳೆಗಳಲ್ಲಿ ಬೇಳೆಕಾಳುಗಳಿವೆ. ಯಾವ ಬೇಳೆ ಮತ್ತು ತಳಿಯನ್ನು ಬೆಳೆಸಬೇಕು ಎಂಬುದನ್ನು ಸ್ಥಳೀಯ ಸಲಹೆಯೊಂದಿಗೆ ಆರಿಸಿ.",
        "note_te": "ఈ ప్రాంతంలో పప్పుధాన్యాలు ఉన్నాయి. ఏ పంట, రకం ఎంచుకోవాలో స్థానిక సలహా తీసుకోండి.",
    },
    {
        "name": "Groundnut",
        "kn": "ಕಡಲೆಕಾಯಿ",
        "te": "వేరుశెనగ",
        "group": "Oilseeds",
        "note_en": "Listed among Zone V crops. Check field drainage, soil and the recommended sowing window.",
        "note_kn": "ವಲಯ V ಯಲ್ಲಿ ಉಲ್ಲೇಖಿಸಿರುವ ಬೆಳೆ. ಹೊಲದ ನೀರು ಹರಿವು, ಮಣ್ಣು ಮತ್ತು ಬಿತ್ತನೆ ಸಮಯ ಪರಿಶೀಲಿಸಿ.",
        "note_te": "జోన్ V పంటలలో వేరుశెనగ ఉంది. నేల, నీటి పారుదల, విత్తే సమయాన్ని పరిశీలించండి.",
    },
    {
        "name": "Mulberry",
        "kn": "ಹಿಪ್ಪುನೇರಳೆ",
        "te": "మల్బరీ",
        "group": "Sericulture",
        "note_en": "Listed for the zone. Consider it only where the farmer has access to sericulture support and a suitable market.",
        "note_kn": "ಈ ವಲಯದಲ್ಲಿ ಉಲ್ಲೇಖಿಸಲಾಗಿದೆ. ರೇಷ್ಮೆ ಸಾಕಾಣಿಕೆ ಬೆಂಬಲ ಮತ್ತು ಮಾರುಕಟ್ಟೆ ವ್ಯವಸ್ಥೆ ಇದ್ದರೆ ಮಾತ್ರ ಪರಿಗಣಿಸಿ.",
        "note_te": "ఈ ప్రాంతానికి సూచించిన పంట. పట్టు పరిశ్రమకు అవసరమైన మద్దతు, మార్కెట్ ఉంటేనే పరిశీలించండి.",
    },
    {
        "name": "Vegetables",
        "kn": "ತರಕಾರಿಗಳು",
        "te": "కూరగాయలు",
        "group": "Horticulture",
        "note_en": "The zone profile includes vegetables. Choose a specific vegetable only after checking season, water, input cost and market access.",
        "note_kn": "ಈ ವಲಯದಲ್ಲಿ ತರಕಾರಿಗಳಿವೆ. ನಿರ್ದಿಷ್ಟ ತರಕಾರಿ ಆಯ್ಕೆ ಮಾಡುವ ಮೊದಲು ಋತು, ನೀರು, ವೆಚ್ಚ ಮತ್ತು ಮಾರುಕಟ್ಟೆ ಪರಿಶೀಲಿಸಿ.",
        "note_te": "ఈ ప్రాంతంలో కూరగాయలు ఉన్నాయి. నిర్దిష్ట పంటకు ముందు సీజన్, నీరు, ఖర్చు, మార్కెట్‌ను పరిశీలించండి.",
    },
    {
        "name": "Fruits",
        "kn": "ಹಣ್ಣು ಬೆಳೆಗಳು",
        "te": "పండ్ల పంటలు",
        "group": "Horticulture",
        "note_en": "The zone profile includes fruits. Perennial crops need longer-term water, soil and market planning.",
        "note_kn": "ಈ ವಲಯದಲ್ಲಿ ಹಣ್ಣು ಬೆಳೆಗಳಿವೆ. ದೀರ್ಘಕಾಲದ ನೀರು, ಮಣ್ಣು ಮತ್ತು ಮಾರುಕಟ್ಟೆ ಯೋಜನೆ ಅಗತ್ಯ.",
        "note_te": "ఈ ప్రాంతంలో పండ్ల పంటలు ఉన్నాయి. దీర్ఘకాలిక నీరు, నేల, మార్కెట్ ప్రణాళిక అవసరం.",
    },
    {
        "name": "Flowers",
        "kn": "ಹೂ ಬೆಳೆಗಳು",
        "te": "పూల పంటలు",
        "group": "Horticulture",
        "note_en": "The zone profile includes flowers. Check local buyer access, harvest frequency and price volatility before choosing.",
        "note_kn": "ಈ ವಲಯದಲ್ಲಿ ಹೂ ಬೆಳೆಗಳಿವೆ. ಖರೀದಿದಾರರು, ಕೊಯ್ಲಿನ ಅವಧಿ ಮತ್ತು ಬೆಲೆ ಬದಲಾವಣೆ ಪರಿಶೀಲಿಸಿ.",
        "note_te": "ఈ ప్రాంతంలో పూల పంటలు ఉన్నాయి. కొనుగోలుదారులు, కోత తరచుదనం, ధర మార్పులను పరిశీలించండి.",
    },
]

UASB_ZONE_V_SOURCE = "https://www.uasbangalore.edu.in/en/agroclimatic-zones-uas-bangalore/"
UASB_PRACTICES_SOURCE = "https://www.uasbangalore.edu.in/ebooks/"


def crop_basket(language: str = "en") -> list[dict[str, Any]]:
    key = language if language in {"kn", "te"} else "en"
    result = []
    for crop in UASB_ZONE_V_CROPS:
        result.append({
            "name": crop["kn"] if key == "kn" else crop["te"] if key == "te" else crop["name"],
            "english_name": crop["name"],
            "group": crop["group"],
            "note": crop[f"note_{key}"],
        })
    return result


def zone_context() -> dict[str, Any]:
    return {
        "zone": "Zone V",
        "climate": "Hot, moist semi-arid",
        "annual_rainfall_mm": "680–890",
        "dominant_soil": "Red soils; lateritic and alluvial soils also occur",
        "districts": ["Bengaluru Urban", "Bengaluru Rural", "Ramanagara", "Kolar", "Chikkaballapur"],
        "source": UASB_ZONE_V_SOURCE,
    }
