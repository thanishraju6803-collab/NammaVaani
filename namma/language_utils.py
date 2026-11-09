from __future__ import annotations

from collections import Counter

# Unicode ranges used only as a fallback for identifying the script of a
# completed transcript. This is not an acoustic language detector.
_SCRIPT_RANGES = {
    "bn": (0x0980, 0x09FF),
    "gu": (0x0A80, 0x0AFF),
    "pa": (0x0A00, 0x0A7F),
    "hi": (0x0900, 0x097F),
    "ta": (0x0B80, 0x0BFF),
    "te": (0x0C00, 0x0C7F),
    "kn": (0x0C80, 0x0CFF),
    "ml": (0x0D00, 0x0D7F),
}


def detect_script_language(text: str) -> str | None:
    """Guess the dominant writing system in text; never treat this as ASR detection."""
    counts: Counter[str] = Counter()
    for char in text or "":
        code = ord(char)
        for language, (start, end) in _SCRIPT_RANGES.items():
            if start <= code <= end:
                counts[language] += 1
                break
        else:
            if char.isalpha() and code < 0x0250:
                counts["en"] += 1
    if not counts:
        return None
    language, count = counts.most_common(1)[0]
    total = sum(counts.values())
    if count < 2 or count / total < 0.35:
        return None
    return language


def normalize_language_code(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower().replace("_", "-")
    if value in {"indic-auto", "auto"}:
        return None
    base = value.split("-", 1)[0]
    return base if base in {"bn", "en", "gu", "hi", "kn", "ml", "mr", "pa", "ta", "te"} else None
