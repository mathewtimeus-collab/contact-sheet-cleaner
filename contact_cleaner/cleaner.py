"""Load, clean, deduplicate, and write contact sheets."""

from __future__ import annotations

import csv
import json
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook, load_workbook

from contact_cleaner.normalize import (
    FieldResult,
    name_key,
    normalize_city,
    normalize_date,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_state,
    phone_key,
)

COLUMN_ALIASES = {
    "name": "name",
    "full_name": "name",
    "full name": "name",
    "contact": "name",
    "contact name": "name",
    "email": "email",
    "e-mail": "email",
    "email_address": "email",
    "email address": "email",
    "phone": "phone",
    "phone_number": "phone",
    "phone number": "phone",
    "mobile": "phone",
    "tel": "phone",
    "telephone": "phone",
    "company": "company",
    "organization": "company",
    "org": "company",
    "city": "city",
    "state": "state",
    "last service": "last_service",
    "last_service": "last_service",
    "service date": "last_service",
    "service_date": "last_service",
    "date": "last_service",
}

NORMALIZERS = {
    "name": normalize_name,
    "email": normalize_email,
    "phone": normalize_phone,
    "city": normalize_city,
    "state": normalize_state,
    "last_service": normalize_date,
}


def canonical_headers(headers: Iterable[str]) -> list[str]:
    mapped = []
    used = set()
    for header in headers:
        raw = (header or "").strip()
        key = COLUMN_ALIASES.get(raw.lower(), raw.strip().lower().replace(" ", "_"))
        if not key:
            key = "column"
        candidate = key
        n = 2
        while candidate in used:
            candidate = f"{key}_{n}"
            n += 1
        used.add(candidate)
        mapped.append(candidate)
    return mapped


def _row_from_values(headers: list[str], values: Iterable[Any]) -> dict[str, Any]:
    row = OrderedDict()
    for header, value in zip(headers, values):
        row[header] = value
    return row


def load_table(path: Path, sheet: str | None = None) -> tuple[list[str], list[dict[str, Any]]]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        workbook = load_workbook(path, data_only=True)
        worksheet = workbook[sheet] if sheet else workbook[workbook.sheetnames[0]]
        rows_iter = worksheet.iter_rows(values_only=True)
        try:
            raw_headers = next(rows_iter)
        except StopIteration:
            return [], []
        headers = canonical_headers(["" if h is None else str(h) for h in raw_headers])
        records = []
        for values in rows_iter:
            if values is None or all(v is None or str(v).strip() == "" for v in values):
                continue
            records.append(_row_from_values(headers, values))
        return headers, records

    if suffix == ".xls":
        raise ValueError("Legacy .xls files are not supported. Save the sheet as .xlsx or .csv.")

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            raw_headers = next(reader)
        except StopIteration:
            return [], []
        headers = canonical_headers(raw_headers)
        records = []
        for values in reader:
            if not values or all(str(v).strip() == "" for v in values):
                continue
            records.append(_row_from_values(headers, values))
        return headers, records


def _filled_count(row: dict[str, Any]) -> int:
    return sum(1 for value in row.values() if str(value or "").strip())


def _dedupe_key(row: dict[str, Any]) -> tuple[str, str] | None:
    email = (row.get("email") or "").strip().lower()
    if email and "@" in email and " " not in email:
        return ("email", email)
    name = name_key(row.get("name") or "")
    phone = phone_key(row.get("phone") or "")
    if name and phone:
        return ("name_phone", f"{name}|{phone}")
    return None


def _merge_rows(primary: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    # Prefer the row with more filled fields as the base, then fill blanks.
    base, other = (primary, incoming)
    if _filled_count(incoming) > _filled_count(primary):
        base, other = incoming, primary
    merged = deepcopy(base)
    for key, value in other.items():
        if not str(merged.get(key) or "").strip() and str(value or "").strip():
            merged[key] = value
    return merged


def clean_records(headers: list[str], records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    report = {
        "rows_in": len(records),
        "rows_out": 0,
        "duplicates_removed": 0,
        "phones_normalized": 0,
        "emails_normalized": 0,
        "emails_invalid": 0,
        "dates_normalized": 0,
        "dates_unparsed": 0,
        "names_normalized": 0,
        "cities_normalized": 0,
        "states_normalized": 0,
        "changes": [],
    }

    cleaned: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=2):  # header is row 1
        row = OrderedDict((key, record.get(key, "")) for key in headers)
        for field, normalizer in NORMALIZERS.items():
            if field not in row:
                continue
            result: FieldResult = normalizer(row[field])
            if result.changed:
                report["changes"].append(
                    {
                        "row": index,
                        "field": field,
                        "from": "" if record.get(field) is None else str(record.get(field)),
                        "to": result.value,
                        "issue": result.issue,
                    }
                )
                if field == "phone" and result.valid:
                    report["phones_normalized"] += 1
                elif field == "email":
                    report["emails_normalized"] += 1
                elif field == "last_service" and result.valid:
                    report["dates_normalized"] += 1
                elif field == "name":
                    report["names_normalized"] += 1
                elif field == "city":
                    report["cities_normalized"] += 1
                elif field == "state":
                    report["states_normalized"] += 1
            if field == "email" and not result.valid:
                report["emails_invalid"] += 1
                report["changes"].append(
                    {
                        "row": index,
                        "field": field,
                        "from": "" if record.get(field) is None else str(record.get(field)),
                        "to": result.value,
                        "issue": result.issue,
                    }
                ) if not result.changed else None
            if field == "last_service" and not result.valid:
                report["dates_unparsed"] += 1
            if field == "phone" and not result.valid and str(row[field] or "").strip():
                report["changes"].append(
                    {
                        "row": index,
                        "field": field,
                        "from": str(row[field]),
                        "to": result.value,
                        "issue": result.issue,
                    }
                ) if not result.changed else None
            row[field] = result.value
        for key, value in list(row.items()):
            if key in NORMALIZERS:
                continue
            if value is None:
                row[key] = ""
            elif isinstance(value, str):
                row[key] = value.strip()
        cleaned.append(row)

    # Deduplicate while preserving first-seen order, merging blank fields.
    deduped: list[dict[str, Any]] = []
    index_by_key: dict[tuple[str, str], int] = {}
    for row in cleaned:
        key = _dedupe_key(row)
        if key and key in index_by_key:
            existing_index = index_by_key[key]
            deduped[existing_index] = _merge_rows(deduped[existing_index], row)
            report["duplicates_removed"] += 1
            report["changes"].append(
                {
                    "row": None,
                    "field": "record",
                    "from": f"duplicate by {key[0]}",
                    "to": "merged into earlier row",
                    "issue": "duplicate",
                }
            )
            continue
        if key:
            index_by_key[key] = len(deduped)
        deduped.append(row)

    report["rows_out"] = len(deduped)
    return deduped, report


def write_csv(path: Path, headers: list[str], records: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow({key: record.get(key, "") for key in headers})


def write_xlsx(path: Path, headers: list[str], records: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Cleaned"
    sheet.append(headers)
    for record in records:
        sheet.append([record.get(key, "") for key in headers])
    workbook.save(path)


def write_report(path: Path, report: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = deepcopy(report)
    path.write_text(json.dumps(serializable, indent=2) + "\n", encoding="utf-8")


def clean_file(
    input_path: Path,
    output_path: Path,
    report_path: Path | None = None,
    sheet: str | None = None,
) -> dict[str, Any]:
    headers, records = load_table(input_path, sheet=sheet)
    if not headers:
        raise ValueError(f"No header row found in {input_path}")
    cleaned, report = clean_records(headers, records)
    output_path = Path(output_path)
    if output_path.suffix.lower() in {".xlsx", ".xlsm"}:
        write_xlsx(output_path, headers, cleaned)
    else:
        write_csv(output_path, headers, cleaned)
    if report_path:
        write_report(report_path, report)
    report["output"] = str(output_path)
    if report_path:
        report["report"] = str(report_path)
    return report
