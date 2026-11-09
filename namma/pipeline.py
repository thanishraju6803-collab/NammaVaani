from __future__ import annotations

import re
import uuid
from typing import Any


EQUIPMENT_TERMS = {
    "Borewell pump / motor": ["borewell", "bore well", "bore motor", "bore-motor", "borewell motor", "borewell motoru", "boru motor", "బోరు మోటార్", "ಬೋರ್ವೆಲ್", "ಬೋರ್ ವೆಲ್", "ಬೋರ್‌ವೆಲ್", "ಬೋರ್ವೆಲ್ ಮೋಟಾರ್", "ಬೋರ್‌ವೆಲ್ ಮೋಟಾರ್", "బోరు మోటార్", "బోర్‌వెల్ మోటార్", "బోర్వెల్"],
    "Water pump": ["water pump", "pump", "ನೀರಿನ ಪಂಪ್", "ಪಂಪ್"],
    "Tractor": ["tractor", "ಟ್ರಾಕ್ಟರ್", "tractor-u"],
    "Drip irrigation": ["drip", "drip pipe", "ಡ್ರಿಪ್", "ಹನಿ ನೀರಾವರಿ"],
    "Harvester": ["harvester", "harvesting machine", "ಹಾರ್ವೆಸ್ಟರ್"],
    "Sprayer": ["sprayer", "spray machine", "ಸ್ಪ್ರೇಯರ್"],
    "Other / not clear": [],
}

PROBLEM_TERMS = {
    "Not starting / not working": [
        "not working", "not start", "won't start", "stopped working", "start agtilla",
        "start agalla", "start avvatledu", "start avvatle", "work agtilla", "work agalla", "kelasa agtilla", "kelasa agalla", "kelasa madtilla", "pani cheyyatledu", "panicheyatledu", "pani avvatledu",
        "ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ", "ಕೆಲಸ ಮಾಡ್ತಿಲ್ಲ", "ಕೆಲಸ ಆಗುತ್ತಿಲ್ಲ", "ಕೆಲಸ ಆಗ್ತಿಲ್ಲ",
        "ಸ್ಟಾರ್ಟ್ ಆಗುತ್ತಿಲ್ಲ", "ಸ್ಟಾರ್ಟ್ ಆಗ್ತಿಲ್ಲ", "ಆನ್ ಆಗುತ್ತಿಲ್ಲ", "ಆಗುತ್ತಿಲ್ಲ",
        "పని చేయడం లేదు", "పని చేయట్లేదు", "ఆన్ అవ్వడం లేదు", "స్టార్ట్ కావడం లేదు",
    ],
    "Running but no water output": [
        "water not coming", "no water", "neeru illa", "neeru baralla", "neellu levu", "water barthilla", "neeru barthilla", "neeru baralla", "neeru bartilla", "neeru baralla", "neellu ravatledu", "neellu raavatledu", "neellu ravatle", "water ravatledu",
        "ನೀರು ಬರುತ್ತಿಲ್ಲ", "ನೀರು ಬರ್ತಿಲ್ಲ", "ನೀರು ಬರಲ್ಲ", "నీళ్లు రావడం లేదు", "నీరు రావడం లేదు",
    ],
    "Leakage / pipe damage": [
        "leak", "leakage", "pipe broken", "pipe damage", "ಸೋರಿಕೆ", "ಪೈಪ್ ಒಡೆದಿದೆ",
    ],
    "Unusual noise / vibration": ["noise", "vibration", "sound", "ಶಬ್ದ", "ಕಂಪನ"],
    "Other / not clear": [],
}


def extract_fields(transcript: str) -> dict[str, Any]:
    """Transparent rule-assisted extraction for a small repair-domain MVP.

    This is intentionally not presented as an LLM. Users must review and confirm
    every suggested field before a service ticket can be created.
    """
    text = transcript.strip()
    normal = text.casefold()

    equipment = _first_match(normal, EQUIPMENT_TERMS)
    problem = _first_match(normal, PROBLEM_TERMS)
    duration = _extract_duration(normal)
    hp = _extract_hp(normal)
    village = _extract_village(text)

    required = {
        "equipment": equipment,
        "problem": problem,
        "village": village,
    }
    missing = [field for field, value in required.items() if not value or value.startswith("Other")]

    return {
        "equipment": equipment,
        "problem": problem,
        "village": village,
        "duration": duration,
        "specification": hp,
        "operating_condition": _operating_condition(normal),
        "missing_fields": missing,
        "extraction_note": "Rule-assisted suggestions. Review and confirm every field before saving.",
    }


def clarification_questions(fields: dict[str, Any]) -> list[str]:
    questions: list[str] = []
    if not fields.get("equipment") or fields.get("equipment") == "Other / not clear":
        questions.append("Which machine or equipment needs repair?")
    if not fields.get("problem") or fields.get("problem") == "Other / not clear":
        questions.append("What exactly is happening: not starting, running without water, leakage, or something else?")
    if not fields.get("village"):
        questions.append("Which village or area is the equipment located in?")
    if not fields.get("operating_condition") and fields.get("equipment") in {"Borewell pump / motor", "Water pump"}:
        questions.append("Is the motor completely stopped, or is it running without pumping water?")
    if not fields.get("duration"):
        questions.append("For how long has this problem been happening? (Optional)")
    return questions


def ticket_summary(fields: dict[str, Any]) -> str:
    parts = [
        f"{fields.get('equipment') or 'Equipment not specified'}: {fields.get('problem') or 'problem not specified'}",
    ]
    if fields.get("specification"):
        parts.append(str(fields["specification"]))
    if fields.get("duration"):
        parts.append(f"Duration: {fields['duration']}")
    if fields.get("village"):
        parts.append(f"Location: {fields['village']}")
    if fields.get("operating_condition"):
        parts.append(str(fields["operating_condition"]))
    return " | ".join(parts)


def confirmation_text(fields: dict[str, Any], language: str = "Kannada") -> str:
    equipment = fields.get("equipment") or "ಯಂತ್ರದ ವಿವರ ಇಲ್ಲ"
    problem = fields.get("problem") or "ಸಮಸ್ಯೆಯ ವಿವರ ಇಲ್ಲ"
    village = fields.get("village") or "ಸ್ಥಳದ ವಿವರ ಇಲ್ಲ"
    duration = fields.get("duration")

    if language == "Kannada":
        duration_part = f" ಸಮಸ್ಯೆ {duration} ಆಗಿದೆ." if duration else ""
        return (
            f"ನಿಮ್ಮ ದೂರು ಪರಿಶೀಲಿಸಿ. ಯಂತ್ರ: {equipment}. ಸಮಸ್ಯೆ: {problem}. "
            f"ಸ್ಥಳ: {village}.{duration_part} ಈ ವಿವರಗಳು ಸರಿಯಾಗಿವೆಯೇ?"
        )
    return (
        f"Please confirm: {equipment} has the issue '{problem}' at {village}. "
        f"Duration: {duration or 'not provided'}. Are these details correct?"
    )


def new_ticket_id() -> str:
    return "NV-" + uuid.uuid4().hex[:6].upper()


def _first_match(text: str, terms: dict[str, list[str]]) -> str:
    for label, variants in terms.items():
        if any(term.casefold() in text for term in variants):
            return label
    return "Other / not clear"


def _extract_duration(text: str) -> str | None:
    number_words = {
        "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
        "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
        "ಒಂದು": "1", "ಎರಡು": "2", "ಮೂರು": "3", "ನಾಲ್ಕು": "4", "ಐದು": "5",
    }
    numeric = re.search(r"\b(\d{1,3})\s*(?:days?|dina|dinagalu|dinaginda)\b", text, flags=re.IGNORECASE)
    if numeric:
        return f"{numeric.group(1)} days"

    words = "|".join(re.escape(word) for word in number_words)
    word_match = re.search(rf"\b({words})\s*(?:days?|dina|dinagalu|dinaginda)\b", text, flags=re.IGNORECASE)
    if word_match:
        return f"{number_words[word_match.group(1).casefold()]} days"

    kannada = re.search(r"(\d{1,3})\s*ದಿನ(?:ಗಳಿಂದ|ಗಳ|ದಿಂದ)?", text)
    if kannada:
        return f"{kannada.group(1)} days"
    kannada_number_words = {"ಒಂದು": "1", "ಎರಡು": "2", "ಮೂರು": "3", "ನಾಲ್ಕು": "4", "ಐದು": "5", "ಆರು": "6", "ಏಳು": "7", "ಎಂಟು": "8", "ಒಂಬತ್ತು": "9", "ಹತ್ತು": "10"}
    kannada_words_pattern = "|".join(re.escape(word) for word in kannada_number_words)
    kannada_word_match = re.search(rf"({kannada_words_pattern})\s*ದಿನ(?:ಗಳಿಂದ|ಗಳ|ದಿಂದ)?", text)
    if kannada_word_match:
        return f"{kannada_number_words[kannada_word_match.group(1)]} days"
    if "yesterday" in text or "ninne inda" in text or "ninneindha" in text or "ನೆನ್ನೆಯಿಂದ" in text:
        return "Since yesterday"
    return None


def _extract_hp(text: str) -> str | None:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:hp|horse\s*power)\b", text, flags=re.IGNORECASE)
    return f"{match.group(1)} HP" if match else None


def _extract_village(text: str) -> str | None:
    # Capture whole whitespace-delimited tokens. Python \w excludes some
    # combining marks used by Kannada, so [^\s,.;]+ is safer here.
    kannada_label = re.search(
        r"(?:ನಮ್ಮ\s*)?(?:ಗ್ರಾಮ|ಊರು|ಹಳ್ಳಿ)(?:\s*[:\-]\s*|\s+)([^\s,.;]+)",
        text,
        flags=re.IGNORECASE,
    )
    if kannada_label:
        value = kannada_label.group(1).strip()
        if value and value not in {"ಇದೆ", "ಇಲ್ಲಿ", "ಯಲ್ಲಿ", "ಗ್ರಾಮದಲ್ಲಿ"}:
            return value

    explicit = re.search(
        r"(?:village|grama)\s*[:\-]?\s*([^\s,.;]+(?:\s+[^\s,.;]+){0,2})(?=[,.;\n]|$)",
        text,
        flags=re.IGNORECASE,
    )
    if explicit:
        value = explicit.group(1).strip()
        if value:
            return value.title() if value.isascii() else value

    # Kannada construction: “ಅತ್ತಿಬೆಲೆ ಗ್ರಾಮದಲ್ಲಿ ಇದೆ”.
    kannada_suffix = re.search(r"([^\s,.;]+)\s+ಗ್ರಾಮ(?:ದಲ್ಲಿ|ಕ್ಕೆ|ದ)?", text)
    if kannada_suffix:
        return kannada_suffix.group(1).strip()

    # Romanised Kannada/Telugu labels: “ooru Attibele”, “maa village Anekal”.
    roman_label = re.search(
        r"(?:namma\s+ooru|nanna\s+ooru|nam\s+ooru|maa\s+ooru|ooru|gramam|maa\s+village|village)\s*[:=\-]?\s*([A-Za-z][A-Za-z'-]{1,30})",
        text, flags=re.IGNORECASE,
    )
    if roman_label:
        return roman_label.group(1).strip().title()

    # Romanised Kannada construction: “Kattigenahalli alli ide”.
    local = re.search(r"\b([A-Za-z][A-Za-z'-]{1,30})\s+alli\b", text, flags=re.IGNORECASE)
    if local:
        value = local.group(1).strip()
        if value.casefold() not in {"village", "motor", "pump", "borewell"}:
            return value.title()
    return None


def _operating_condition(text: str) -> str | None:
    if any(term in text for term in ["running", "run agtide", "running ide", "on agutte", "on agide", "run agutte", "run agtide", "chalu ide", "చాలుతోంది", "ఆన్ అవుతుంది", "ಚಾಲನೆಯಲ್ಲಿದೆ", "ಮೋಟಾರ್ ಓಡುತ್ತಿದೆ", "ಪಂಪ್ ಓಡುತ್ತಿದೆ"]):
        return "Motor is running"
    if any(term in text for term in ["completely stopped", "motor stopped", "start agtilla", "ಸ್ಟಾರ್ಟ್ ಆಗುತ್ತಿಲ್ಲ", "ಸ್ಟಾರ್ಟ್ ಆಗ್ತಿಲ್ಲ", "ಮೋಟಾರ್ ನಿಂತಿದೆ"]):
        return "Motor is stopped"
    return None
