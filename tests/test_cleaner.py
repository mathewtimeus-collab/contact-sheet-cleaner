from contact_cleaner.cleaner import clean_records


HEADERS = ["name", "email", "phone", "company", "city", "state", "last_service"]


def _row(**kwargs):
    base = {key: "" for key in HEADERS}
    base.update(kwargs)
    return base


def test_dedupes_by_email_and_merges_blank_fields():
    records = [
        _row(name="Jane Doe", email="Jane.Doe@ACME.com", phone="(212) 555-0142", city="New York"),
        _row(name="Jane Doe", email="jane.doe@acme.com", phone="212-555-0142", company="Acme Facilities"),
    ]
    cleaned, report = clean_records(HEADERS, records)
    assert report["duplicates_removed"] == 1
    assert report["rows_out"] == 1
    assert cleaned[0]["email"] == "jane.doe@acme.com"
    assert cleaned[0]["company"] == "Acme Facilities"
    assert cleaned[0]["city"] == "New York"


def test_dedupes_by_name_and_phone_when_email_missing():
    records = [
        _row(name="Mike Rossi", phone="(973) 555-0155", company="Rossi Doors", last_service="2/2/26"),
        _row(name="mike rossi", phone="973-555-0155", company="Rossi Doors", last_service="2026-02-02"),
    ]
    cleaned, report = clean_records(HEADERS, records)
    assert report["duplicates_removed"] == 1
    assert cleaned[0]["name"] == "Mike Rossi"
    assert cleaned[0]["phone"] == "(973) 555-0155"
    assert cleaned[0]["last_service"] == "2026-02-02"


def test_does_not_merge_different_people_with_same_phone():
    records = [
        _row(name="Jane Doe", email="jane.doe@acme.com", phone="2125550142"),
        _row(name="Elena Vasquez", email="elena.vasquez@acme.com", phone="2125550142"),
    ]
    cleaned, report = clean_records(HEADERS, records)
    assert report["duplicates_removed"] == 0
    assert len(cleaned) == 2


def test_skips_completely_empty_rows_before_clean(tmp_path):
    from contact_cleaner.cleaner import load_table, write_csv

    path = tmp_path / "in.csv"
    write_csv(
        path,
        HEADERS,
        [
            _row(name="A", email="a@example.com", phone="2125550142"),
            _row(),
        ],
    )
    # write_csv will still write the empty row; load_table should skip it
    text = path.read_text() + "\n,,,,,,\n"
    path.write_text(text)
    headers, records = load_table(path)
    assert headers == HEADERS
    assert len(records) == 1
