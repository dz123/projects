#!/usr/bin/env python3
"""
Download Hawaii Monthly Visitor Statistics Excel files.

Downloads "Monthly Visitor Statistics" (Visitor Highlights) from:
  https://dbedt.hawaii.gov/economic/tourism/monthly-statistics/

Files are saved to the same directory as this script.
Starts from START_YEAR_MONTH and downloads through the current month,
skipping files that already exist.

Usage:
    python download_visitor_stats.py
"""

import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

BASE_URL    = "https://files.hawaii.gov/dbedt/economic/tourism/monthly-highlights"
START_YEAR  = 2025
START_MONTH = 1
OUTPUT_DIR  = Path(__file__).parent


def month_url(year: int, month: int) -> str:
    label = date(year, month, 1).strftime("%b %Y")   # e.g. "Jan 2025"
    encoded = label.replace(" ", "%20")
    return f"{BASE_URL}/{encoded}.xlsx"


def download_month(year: int, month: int) -> bool:
    label    = date(year, month, 1).strftime("%b %Y")
    filename = f"visitor_stats_{year}_{month:02d}.xlsx"
    dest     = OUTPUT_DIR / filename

    url = month_url(year, month)

    if dest.exists():
        print(f"  Already exists: {filename}  ({url})")
        return True

    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  Downloaded:     {filename}  ({url})")
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  Not available:  {label} (404)")
        else:
            print(f"  Error {e.code}:      {label}")
        return False


def main():
    today  = date.today()
    errors = []

    year  = START_YEAR
    month = START_MONTH

    while (year, month) <= (today.year, today.month):
        ok = download_month(year, month)
        if not ok:
            errors.append(f"{year}-{month:02d}")

        if month == 12:
            year  += 1
            month  = 1
        else:
            month += 1

    if errors:
        print(f"\nSkipped (not yet published or unavailable): {', '.join(errors)}")
    else:
        print("\nAll files downloaded.")


if __name__ == "__main__":
    main()
