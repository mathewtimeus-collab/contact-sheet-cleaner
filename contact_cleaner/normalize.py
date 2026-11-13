"""Normalize names, emails, phone numbers, dates, cities, and state codes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

EMAIL_RE = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.IGNORECASE)
EXT_RE = re.compile(
    r"(?:\s*(?:ext\.?|extension|x)\s*[:#]?\s*(\d+))\s*$",
    re.IGNORECASE,
)
NON_DIGIT_RE = re.compile(r"\D+")
WHITESPACE_RE = re.compile(r"\s+")

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m-%d-%Y",
    "%m-%d-%y",
    "%m.%d.%Y",
    "%m.%d.%y",
    "%d.%m.%Y",
    "%d.%m.%y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%d %b %Y",
    "%d %b %y",
    "%d %B %Y",
    "%b %d %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%B %d, %Y",
    "%b. %d, %Y",
    "%Y.%m.%d",
)


@dataclass
class FieldResult:
    value: str
    changed: bool
    valid: bool = True
    issue: Optional[str] = None


def blank_to_empty(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    return str(value).strip()


def normalize_name(raw: Any) -> FieldResult:
    original = blank_to_empty(raw)
    if not original:
        return FieldResult(value="", changed=False, valid=True)
    # "PATEL, AISHA" -> "Aisha Patel"
    if "," in original and original.count(",") == 1:
        last, first = [part.strip() for part in original.split(",", 1)]
        if last and first and not any(ch.isdigit() for ch in original):
            original_swapped = f"{first} {last}"
            cleaned = WHITESPACE_RE.sub(" ", original_swapped).strip()
            cleaned = cleaned.title()
            # Keep common apostrophe names readable: O'Neil
            return FieldResult(value=_fix_name_caps(cleaned), changed=cleaned != raw if isinstance(raw, str) else True)
    cleaned = WHITESPACE_RE.sub(" ", original).strip().title()
    cleaned = _fix_name_caps(cleaned)
    return FieldResult(value=cleaned, changed=cleaned != original)


def _fix_name_caps(name: str) -> str:
    parts = []
    for token in name.split(" "):
        if "'" in token and len(token) > 2:
            head, tail = token.split("'", 1)
            token = f"{head.capitalize()}'{tail.capitalize()}"
        parts.append(token)
    return " ".join(parts)


def normalize_email(raw: Any) -> FieldResult:
    original = blank_to_empty(raw)
    if not original:
        return FieldResult(value="", changed=False, valid=True)
    cleaned = original.strip().lower()
    if EMAIL_RE.match(cleaned):
        return FieldResult(value=cleaned, changed=cleaned != original, valid=True)
    return FieldResult(
        value=cleaned,
        changed=cleaned != original,
        valid=False,
        issue="invalid email",
    )


def normalize_phone(raw: Any) -> FieldResult:
    original = blank_to_empty(raw)
    if not original:
        return FieldResult(value="", changed=False, valid=True)

    extension = ""
    working = original
    ext_match = EXT_RE.search(working)
    if ext_match:
        extension = ext_match.group(1)
        working = working[: ext_match.start()]

    digits = NON_DIGIT_RE.sub("", working)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) != 10:
        return FieldResult(
            value=original,
            changed=False,
            valid=False,
            issue="unrecognized phone",
        )

    formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if extension:
        formatted = f"{formatted} ext. {extension}"
    return FieldResult(value=formatted, changed=formatted != original, valid=True)


def normalize_date(raw: Any) -> FieldResult:
    if raw is None or raw == "":
        return FieldResult(value="", changed=False, valid=True)
    if isinstance(raw, datetime):
        iso = raw.date().isoformat()
        return FieldResult(value=iso, changed=True, valid=True)
    if isinstance(raw, date):
        return FieldResult(value=raw.isoformat(), changed=True, valid=True)

    original = blank_to_empty(raw)
    if not original:
        return FieldResult(value="", changed=False, valid=True)

    lowered = original.lower()
    if lowered in {"n/a", "na", "none", "unknown", "-", "tbd"}:
        return FieldResult(value="", changed=original != "", valid=True, issue="empty date placeholder")

    # 2024.5.9 style (unpadded month/day with dots)
    compact = original.replace(",", "")
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(compact, fmt)
            iso = parsed.date().isoformat()
            return FieldResult(value=iso, changed=iso != original, valid=True)
        except ValueError:
            continue

    # Unpadded dotted dates like 2024.5.9
    m = re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", compact)
    if m:
        try:
            parsed = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return FieldResult(value=parsed.isoformat(), changed=True, valid=True)
        except ValueError:
            pass

    return FieldResult(value=original, changed=False, valid=False, issue="unparsed date")


def normalize_city(raw: Any) -> FieldResult:
    original = blank_to_empty(raw)
    if not original:
        return FieldResult(value="", changed=False, valid=True)
    cleaned = WHITESPACE_RE.sub(" ", original).strip().title()
    return FieldResult(value=cleaned, changed=cleaned != original)


def normalize_state(raw: Any) -> FieldResult:
    original = blank_to_empty(raw)
    if not original:
        return FieldResult(value="", changed=False, valid=True)
    cleaned = original.upper()
    if len(cleaned) == 2 and cleaned.isalpha():
        return FieldResult(value=cleaned, changed=cleaned != original, valid=True)
    return FieldResult(
        value=original,
        changed=False,
        valid=False,
        issue="unrecognized state",
    )


def name_key(name: str) -> str:
    return WHITESPACE_RE.sub(" ", (name or "").strip()).lower()


def phone_key(phone: str) -> str:
    """10-digit US key, ignoring extensions."""
    if not phone:
        return ""
    working = EXT_RE.sub("", phone)
    digits = NON_DIGIT_RE.sub("", working)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""
