# Contact Sheet Cleaner

A small Python CLI that cleans messy contact lists in CSV or Excel files. It normalizes names, emails, US phone numbers, and dates, deduplicates rows, and writes a JSON report of every fix.

This is a sample project for my freelance profile. The contacts in `samples/` are fictional demo data, not a client list.

Built with AI-assisted development; reviewed and tested by me.

## What it does

- **Names:** trims extra spaces, title-cases, and turns `PATEL, AISHA` into `Aisha Patel`
- **Emails:** trims, lowercases, and flags values that are not valid addresses
- **Phones:** accepts common US formats (`212-555-0142`, `(212) 555-0142`, `+1 212 555 0142`, extensions like `x12`) and writes `(212) 555-0142`
- **Dates:** parses mixed formats (`1/5/24`, `Jan 12, 2024`, `2025/7/8`) into ISO `YYYY-MM-DD`, and treats `n/a` as empty
- **City / state:** title-cases cities and uppercases 2-letter state codes
- **Deduping:** merges rows that share a normalized email, or the same name + phone when email is missing. Blank fields are filled in from the duplicate.

Column names are flexible. `Full Name`, `Email Address`, `Phone Number`, and `Last Service` all map to the expected fields. Other columns are passed through.

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m contact_cleaner samples/messy-contacts.csv \
  -o samples/cleaned-contacts.csv \
  --report samples/cleanup-report.json
```

Excel works the same way. Use `--sheet` if the data is not on the first sheet:

```bash
python -m contact_cleaner samples/messy-contacts.xlsx -o samples/cleaned-contacts.xlsx
```

The command prints a short JSON summary and writes the cleaned file plus a report of individual changes.

## Sample output

From the bundled messy sheet (20 data rows, including blank and duplicate records):

```json
{
  "rows_in": 20,
  "rows_out": 16,
  "duplicates_removed": 4,
  "phones_normalized": 13,
  "emails_normalized": 6,
  "emails_invalid": 1,
  "dates_normalized": 14,
  "dates_unparsed": 0
}
```

`samples/messy-contacts.csv` (and `samples/messy-contacts.xlsx`) is the input. After you run the command above, `samples/cleaned-contacts.csv` and `samples/cleanup-report.json` will match the checked-in copies. A rendered sample of that run is in `docs/thumbnail.png`.

## Tests

```bash
pip install pytest
pytest -q
```

## License

MIT
