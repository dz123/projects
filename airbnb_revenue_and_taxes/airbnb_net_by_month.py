#!/usr/bin/env python3
"""
Read an Airbnb transaction CSV, filter to Reservation rows, and compute
    calculated = Amount * 0.97 - Cleaning fee
grouped by (year-month of Start date, property).

Prints: year-month | property | calculated | sum(nights)

Usage:
    python airbnb_net_by_month.py [path/to/airbnb.csv]
"""

import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DOWNLOADS   = Path.home() / "Downloads"
_candidates = sorted(DOWNLOADS.glob("airbnb_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
DEFAULT_CSV = _candidates[0] if _candidates else None
OUTPUT_CSV  = Path(__file__).parent / "airbnb_net_by_month.csv"
START_YEAR  = 2023

LISTING_MAP = {
    "1blk to waikiki beach! newly renovated king condo":    "PM 1105",
    "25thfl ocean view 1blk to waikiki beach king condo":   "PM 2505",
    "partial ocean view king condo at maui vista kihei":    "MV 1321",
}


def map_listing(s: str):
    return LISTING_MAP.get(s.strip().lower())


def _float(s):
    try:
        return float((s or "").strip().replace(",", ""))
    except ValueError:
        return 0.0


def _int(s):
    try:
        return int(float((s or "").strip()))
    except ValueError:
        return 0


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path:
        sys.exit("No airbnb_*.csv found in Downloads. Pass the CSV path as an argument.")
    if not csv_path.exists():
        sys.exit(f"File not found: {csv_path}")

    # keyed by (year_month, property) → {"calc": float, "nights": int}
    totals = defaultdict(lambda: {"calc": 0.0, "nights": 0})

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["Type"].strip() != "Reservation":
                continue

            start_str = r.get("Start date", "").strip()
            if not start_str:
                continue
            try:
                start = datetime.strptime(start_str, "%m/%d/%Y").date()
            except ValueError:
                continue
            if start.year < START_YEAR:
                continue

            prop = map_listing(r.get("Listing", ""))
            if not prop:
                continue

            amount   = _float(r.get("Amount", ""))
            cleaning = _float(r.get("Cleaning fee", ""))
            nights   = _int(r.get("Nights", ""))

            calc = amount * 0.97 - cleaning

            key = (f"{start.year}-{start.month:02d}", prop)
            totals[key]["calc"]   += calc
            totals[key]["nights"] += nights

    # Write sorted by month, then property
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["year_month", "property", "calculated", "nights", "avg_per_night"])
        for (ym, prop) in sorted(totals.keys()):
            row = totals[(ym, prop)]
            avg = row["calc"] / row["nights"] if row["nights"] else 0.0
            writer.writerow([ym, prop, f"{row['calc']:.2f}", row["nights"], f"{avg:.2f}"])

    print(f"Saved {len(totals)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
