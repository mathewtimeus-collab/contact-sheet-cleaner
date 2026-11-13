import json
from pathlib import Path

from openpyxl import Workbook, load_workbook

from contact_cleaner.cli import main
from contact_cleaner.cleaner import load_table

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "messy-contacts.csv"


def test_cli_cleans_sample_csv(tmp_path):
    output = tmp_path / "cleaned.csv"
    report = tmp_path / "report.json"
    assert main([str(SAMPLE), "-o", str(output), "--report", str(report)]) == 0

    headers, rows = load_table(output)
    assert "name" in headers
    emails = [row["email"] for row in rows]
    assert emails.count("jane.doe@acme.com") == 1
    assert emails.count("john.smith@metro-hvac.com") == 1
    assert emails.count("aisha.patel@riverside.example") == 1

    jane = next(row for row in rows if row["email"] == "jane.doe@acme.com")
    assert jane["name"] == "Jane Doe"
    assert jane["phone"] == "(212) 555-0142"
    assert jane["last_service"] == "2024-01-05"

    robert = next(row for row in rows if "chen" in row["name"].lower())
    assert robert["phone"] == "(917) 555-0100 ext. 12"
    assert robert["email"] == "robert.chen@buildings.org"

    chris = next(row for row in rows if row["name"] == "Chris Bailey")
    assert chris["phone"] == "not-a-phone"
    assert chris["last_service"] == "2026-09-13"

    data = json.loads(report.read_text())
    assert data["rows_in"] == 20
    assert data["duplicates_removed"] == 4  # jane, john, aisha, mike rossi
    assert data["rows_out"] == 16
    assert data["emails_invalid"] >= 1
    assert data["phones_normalized"] >= 1
    assert data["dates_normalized"] >= 1


def test_cli_reads_and_writes_xlsx(tmp_path):
    source = tmp_path / "messy.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Full Name", "Email Address", "Phone Number", "Last Service"])
    sheet.append(["  jane doe ", "Jane.Doe@ACME.com", "(212) 555-0142", "1/5/24"])
    sheet.append(["Jane Doe", "jane.doe@acme.com", "212-555-0142", "2024-01-05"])
    workbook.save(source)

    output = tmp_path / "cleaned.xlsx"
    report = tmp_path / "report.json"
    assert main([str(source), "-o", str(output), "--report", str(report)]) == 0

    loaded = load_workbook(output)
    values = list(loaded.active.iter_rows(values_only=True))
    assert values[0] == ("name", "email", "phone", "last_service")
    assert len(values) == 2  # header + 1 deduped row
    assert values[1][1] == "jane.doe@acme.com"
    assert values[1][2] == "(212) 555-0142"
    assert values[1][3] == "2024-01-05"


def test_cli_missing_file_returns_error():
    # argparse errors call sys.exit(2) via parser.error — catch SystemExit
    try:
        main(["/tmp/does-not-exist-contact-sheet.csv"])
        assert False, "expected parser error"
    except SystemExit as exc:
        assert exc.code == 2
