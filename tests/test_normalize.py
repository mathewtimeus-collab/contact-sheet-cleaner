from datetime import date

from contact_cleaner.normalize import (
    normalize_city,
    normalize_date,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_state,
    phone_key,
)


def test_normalize_name_collapses_space_and_title_cases():
    result = normalize_name("  jane   doe ")
    assert result.value == "Jane Doe"
    assert result.changed is True


def test_normalize_name_swaps_last_first():
    result = normalize_name("PATEL, AISHA")
    assert result.value == "Aisha Patel"


def test_normalize_name_preserves_apostrophe():
    assert normalize_name("Sarah O'Neil").value == "Sarah O'Neil"


def test_normalize_email_lowercases_and_validates():
    result = normalize_email("  Jane.Doe@ACME.com ")
    assert result.value == "jane.doe@acme.com"
    assert result.valid is True
    assert result.changed is True


def test_normalize_email_flags_invalid():
    result = normalize_email("maria@bad email")
    assert result.valid is False
    assert result.issue == "invalid email"


def test_normalize_phone_accepts_common_us_formats():
    expected = "(212) 555-0142"
    for raw in ("(212) 555-0142", "212-555-0142", "212.555.0142", "12125550142", "+1 212 555 0142"):
        result = normalize_phone(raw)
        assert result.value == expected, raw
        assert result.valid is True


def test_normalize_phone_keeps_extension():
    result = normalize_phone("917.555.0100 x12")
    assert result.value == "(917) 555-0100 ext. 12"
    assert result.valid is True


def test_normalize_phone_rejects_short_or_text():
    assert normalize_phone("555-0148").valid is False
    assert normalize_phone("not-a-phone").valid is False
    assert normalize_phone("").value == ""


def test_normalize_date_multiple_formats():
    cases = {
        "1/5/24": "2024-01-05",
        "2024-01-05": "2024-01-05",
        "Jan 12, 2024": "2024-01-12",
        "12-Jan-2024": "2024-01-12",
        "15 Oct 2025": "2025-10-15",
        "July 4, 2026": "2026-07-04",
        "2025/7/8": "2025-07-08",
        "2024.5.9": "2024-05-09",
        "13.09.2026": "2026-09-13",
        "01-05-2024": "2024-01-05",
    }
    for raw, expected in cases.items():
        result = normalize_date(raw)
        assert result.valid is True, raw
        assert result.value == expected, raw


def test_normalize_date_handles_datetime_and_placeholders():
    assert normalize_date(date(2024, 11, 1)).value == "2024-11-01"
    result = normalize_date("n/a")
    assert result.value == ""
    assert result.issue == "empty date placeholder"
    assert normalize_date("tomorrow").valid is False


def test_city_and_state():
    assert normalize_city("brooklyn").value == "Brooklyn"
    assert normalize_state("ny").value == "NY"
    assert normalize_state("New York").valid is False


def test_phone_key_strips_extension_and_country_code():
    assert phone_key("(917) 555-0100 ext. 12") == "9175550100"
    assert phone_key("+1 718 555 0194") == "7185550194"
