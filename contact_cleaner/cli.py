"""Command-line interface for contact_cleaner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from contact_cleaner.cleaner import clean_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contact-sheet-cleaner",
        description=(
            "Clean a messy contact CSV or Excel sheet: normalize names, emails, "
            "US phone numbers, and dates, then deduplicate and write a report."
        ),
    )
    parser.add_argument("input", type=Path, help="Path to a .csv or .xlsx contact sheet")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path (.csv or .xlsx). Default: <input>-cleaned.csv",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="JSON report path. Default: <input>-report.json",
    )
    parser.add_argument("--sheet", help="Excel sheet name (defaults to the first sheet)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    input_path = args.input
    if not input_path.exists():
        parser.error(f"input file not found: {input_path}")

    stem = input_path.with_suffix("")
    output_path = args.output or Path(f"{stem}-cleaned.csv")
    report_path = args.report or Path(f"{stem}-report.json")

    try:
        report = clean_file(input_path, output_path, report_path=report_path, sheet=args.sheet)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    summary = {
        "rows_in": report["rows_in"],
        "rows_out": report["rows_out"],
        "duplicates_removed": report["duplicates_removed"],
        "phones_normalized": report["phones_normalized"],
        "emails_normalized": report["emails_normalized"],
        "emails_invalid": report["emails_invalid"],
        "dates_normalized": report["dates_normalized"],
        "dates_unparsed": report["dates_unparsed"],
        "output": report["output"],
        "report": report.get("report"),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
