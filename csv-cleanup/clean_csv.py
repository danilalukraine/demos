#!/usr/bin/env python3
"""
clean_csv.py — practical CSV cleanup in one pass.

Fixes the usual spreadsheet mess:
  * trims whitespace, collapses double spaces
  * lowercases emails
  * normalizes phone numbers to (XXX) XXX-XXXX
  * normalizes dates to ISO (YYYY-MM-DD)
  * normalizes money values ($1,240.50 -> 1240.50)
  * fixes SHOUTING/lowercase names and cities to Title Case
  * drops fully empty rows
  * removes duplicates (exact or by key column, e.g. email)

Columns are auto-detected by header keywords (email / phone / date / name /
city / amount ...) — override nothing, it just works on sane headers.

Usage:
    python3 clean_csv.py input.csv -o output.csv
    python3 clean_csv.py input.csv -o output.csv --key email --dayfirst

Demo build by AmirWebWorks (Toronto). Python 3.8+, standard library only.
"""

import argparse
import csv
import re
import sys
from datetime import datetime

EMAIL_HINTS = ("email", "e-mail", "mail")
PHONE_HINTS = ("phone", "tel", "mobile", "cell")
DATE_HINTS = ("date", "signup", "created", "updated", "dob")
MONEY_HINTS = ("amount", "total", "price", "spent", "cost", "balance", "paid")
TITLE_HINTS = ("name", "city", "town", "province", "state", "vendor", "company")


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalize_email(value: str) -> str:
    return clean_text(value).lower()


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return clean_text(value)  # not a NA phone — leave as-is, just trimmed


def normalize_date(value: str, dayfirst: bool) -> str:
    text = clean_text(value).replace(",", "")
    if not text:
        return ""
    numeric_first = ["%d/%m/%Y", "%m/%d/%Y"] if dayfirst else ["%m/%d/%Y", "%d/%m/%Y"]
    formats = ["%Y-%m-%d", "%Y/%m/%d"] + numeric_first + [
        "%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return clean_text(value)  # unrecognized — never destroy data


def normalize_money(value: str) -> str:
    text = clean_text(value).replace("$", "").replace(",", "")
    if not text:
        return ""
    try:
        return f"{float(text):.2f}"
    except ValueError:
        return clean_text(value)


def normalize_case(value: str) -> str:
    text = clean_text(value)
    # Only fix clearly broken casing; leave "McDonald" and friends alone.
    if text.isupper() or text.islower():
        return text.title()
    return text


def column_kind(header: str) -> str:
    h = header.lower()
    if any(k in h for k in EMAIL_HINTS):
        return "email"
    if any(k in h for k in PHONE_HINTS):
        return "phone"
    if any(k in h for k in DATE_HINTS):
        return "date"
    if any(k in h for k in MONEY_HINTS):
        return "money"
    if any(k in h for k in TITLE_HINTS):
        return "title"
    return "text"


def main() -> int:
    ap = argparse.ArgumentParser(description="Clean up a messy CSV file.")
    ap.add_argument("input", help="path to the messy CSV")
    ap.add_argument("-o", "--output", required=True, help="path for the cleaned CSV")
    ap.add_argument("--key", help="comma-separated column(s) to dedupe on, e.g. 'email' "
                                  "(default: the whole normalized row)")
    ap.add_argument("--dayfirst", action="store_true",
                    help="treat 03/07/2026 as 3 July (default: March 7, North-American)")
    ap.add_argument("--report", default=None, help="also write a cleanup report to this file")
    args = ap.parse_args()

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        print("Input file is empty.", file=sys.stderr)
        return 1

    header = [clean_text(h) for h in rows[0]]
    kinds = [column_kind(h) for h in header]

    key_idx = None
    if args.key:
        wanted = [k.strip().lower() for k in args.key.split(",")]
        key_idx = [i for i, h in enumerate(header) if h.lower() in wanted]
        if not key_idx:
            print(f"Key column(s) {args.key!r} not found in header {header}.", file=sys.stderr)
            return 1

    cleaned, seen = [], set()
    stats = {"rows_in": len(rows) - 1, "empty_dropped": 0, "dupes_dropped": 0, "cells_fixed": 0}

    for raw in rows[1:]:
        raw += [""] * (len(header) - len(raw))          # pad short rows
        if all(not clean_text(c) for c in raw):
            stats["empty_dropped"] += 1
            continue

        row = []
        for i, cell in enumerate(raw[: len(header)]):
            kind = kinds[i]
            if kind == "email":
                fixed = normalize_email(cell)
            elif kind == "phone":
                fixed = normalize_phone(cell)
            elif kind == "date":
                fixed = normalize_date(cell, args.dayfirst)
            elif kind == "money":
                fixed = normalize_money(cell)
            elif kind == "title":
                fixed = normalize_case(cell)
            else:
                fixed = clean_text(cell)
            if fixed != cell:
                stats["cells_fixed"] += 1
            row.append(fixed)

        key = tuple(row[i].lower() for i in key_idx) if key_idx else tuple(c.lower() for c in row)
        if key_idx and all(not part for part in key):
            key = ("~blank~",) + tuple(c.lower() for c in row)  # blank key: fall back to full row
        if key in seen:
            stats["dupes_dropped"] += 1
            continue
        seen.add(key)
        cleaned.append(row)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleaned)

    report = (
        f"clean_csv.py report\n"
        f"  input:          {args.input}\n"
        f"  output:         {args.output}\n"
        f"  rows in:        {stats['rows_in']}\n"
        f"  rows out:       {len(cleaned)}\n"
        f"  empty dropped:  {stats['empty_dropped']}\n"
        f"  dupes dropped:  {stats['dupes_dropped']}"
        + (f" (key: {args.key})" if args.key else " (key: full row)")
        + f"\n  cells fixed:    {stats['cells_fixed']}\n"
    )
    print(report)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
