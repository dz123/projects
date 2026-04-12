# hawaii_analysis — Project Notes

## Goal
Download and parse Hawaii monthly visitor statistics from the DBEDT website, extract island-level metrics, and visualize them in a browser dashboard.

## Data Source
- **URL**: https://dbedt.hawaii.gov/economic/tourism/monthly-statistics/
- **Files**: Monthly Visitor Statistics Excel files (Visitor Highlights)
- **Pattern**: `https://files.hawaii.gov/dbedt/economic/tourism/monthly-highlights/[Mon YYYY].xlsx`
- **Coverage**: January 2025 onward

## Scripts

### download_visitor_stats.py
Downloads Excel files from DBEDT, saving them as `visitor_stats_YYYY_MM.xlsx`.
- Starts from `START_YEAR=2025`, `START_MONTH=1`
- Skips files already downloaded
- Prints the full URL for each file

### parse_visitor_stats.py
Parses the "Island" sheet from each Excel file and extracts 7 metrics × 6 islands.

**Metrics extracted:**
- TOTAL EXPENDITURES ($ MILLION)
- TOTAL VISITOR DAYS
- VISITOR ARRIVALS
- AVERAGE DAILY CENSUS
- AVERAGE LENGTH OF STAY
- PER PERSON PER DAY SPENDING ($)
- PER PERSON PER TRIP SPENDING ($)

**Islands:** oahu, maui, molokai, lanai, kauai, hawaii island

**Year logic:**
- 2025 files: extract both `2025P` and `2024P` columns (prior year comparison)
- 2026+ files: extract only the current year column
- Handles column variants: `2024P`, `2024RP` (Revised Preliminary), `2024` (no suffix)

**Output:** `hawaii_visitor_stats.csv` — columns: `year_month, category, island, value`

### index.html
Single-file browser dashboard (no build step). Serve with:
```bash
python -m http.server 8000 --bind 127.0.0.1
```
Then open http://127.0.0.1:8000/

**Features:**
- Metric dropdown (all 7 metrics)
- Line / Bar chart toggle
- Value / YoY % view toggle
- Island chips (click to show/hide islands; Moloka'i and Lāna'i off by default)
- Summary cards with YoY % change per island
- Uses Chart.js via CDN

## Notes
- Island names in Excel contain Unicode apostrophes (ʻ, ', ') and diacritics (ā, ī) — normalized via `unicodedata` before matching
- Some months have N/A for Moloka'i and Lāna'i (limited data) — these produce fewer than 42 records per file, which is expected
