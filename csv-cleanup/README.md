# CSV Cleanup — demo build by AmirWebWorks (Toronto)

One script, one pass — a messy customer/vendor spreadsheet becomes clean,
deduplicated, analysis-ready data. This folder is a self-contained demo:
`before.csv` is the kind of file we receive, `after.csv` is what we hand back.

> **Demo build.** The data in `before.csv` is fictional, generated to
> showcase the cleanup. No real customer data is used.

## What it fixes

| Problem in `before.csv` | Result in `after.csv` |
|---|---|
| `  John Smith ` / `john smith` / `JOHN SMITH` | `John Smith` |
| `John.SMITH@Gmail.com` | `john.smith@gmail.com` |
| `4165550182`, `416.555.0182`, `+1 416 555 0182` | `(416) 555-0182` |
| `07/03/2026`, `July 3 2026`, `2026/07/03` | `2026-07-03` (ISO) |
| `$1,240.50`, `1240.5` | `1240.50` |
| Same customer entered 2–3 times | one row (dedupe by email) |
| Fully empty rows | removed |

Columns are auto-detected from the header (`email`, `phone`, `date`, `name`,
`city`, `total`/`amount` …) — no config file needed.

## Run it

```bash
python3 clean_csv.py before.csv -o after.csv --key email --report cleanup_report.txt
```

Output on this demo data:

```
rows in:        25
rows out:       17
empty dropped:  2
dupes dropped:  6 (key: email)
cells fixed:    82
```

## Options

| Flag | Meaning |
|---|---|
| `-o FILE` | where to write the cleaned CSV (required) |
| `--key COLS` | dedupe on these column(s), e.g. `--key email` or `--key name,phone`. Default: whole row |
| `--dayfirst` | read `03/07/2026` as 3 July (default: March 7, North-American) |
| `--report F` | also save the summary report to a file |

## Notes

- Python 3.8+, **standard library only** — nothing to install, runs anywhere.
- Non-destructive by design: anything the script can not confidently parse
  (odd date, foreign phone) is trimmed but left as-is, never guessed.
- Originals are never touched; output always goes to a new file.

---
*Want this adapted to your export (QuickBooks, Shopify, Excel, CRM dumps) —
including merge of several files? AmirWebWorks does it same-day. This demo
script is free to run on your own data.*
