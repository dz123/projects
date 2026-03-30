# airbnb_pricing — Project Notes

## Goal
Scrape Airbnb listing pages for two Maui condo complexes to collect:
- **Occupancy**: which nights are booked over the next 3 months
- **Pricing**: total cost for available 2-night stays
- **Reviews**: number of reviews and average score

Output is three CSVs per run, written line-by-line (flushed after each listing) so partial progress is never lost.

---

## Properties
- **Kamaole Sands** — 17 listings
- **Maui Vista** — 14 listings
- All URLs are in `main.py` under `KAMAOLE_SANDS` and `MAUI_VISTA` lists

---

## Architecture
- `main.py` — entry point; opens one browser, one page, scrapes listings sequentially
- `scraper.py` — core logic: calendar scraping, pricing, reviews, unit extraction
- `inspect_calendar.py` — diagnostic script for inspecting Airbnb DOM (not part of main run)
- `output/` — created at runtime; CSVs saved here with timestamp in filename

---

## How the Scraper Works

### Browser
- Playwright, headless=False (visible window), slow_mo=600ms
- Single browser + single page reused across all listings (no re-login risk)
- Fresh context each run — no stored cookies, no Airbnb account involved

### Per Listing Flow
1. Load listing page (`domcontentloaded` + 6s wait)
2. Extract title → parse unit number via regex
3. Scrape reviews from body text
4. Scroll to `[data-section-id="AVAILABILITY_CALENDAR_INLINE"]`
5. Read calendar day divs for 3 months, navigating forward each month
6. For available 2-night windows: load URL with `?check_in=&check_out=` to get total price
7. Write rows to all 3 CSVs immediately and flush

---

## Airbnb Calendar DOM (discovered via inspect_calendar.py)

### Calendar day elements
```
<div data-testid="calendar-day-MM/DD/YYYY" class="CLASS notranslate">DAY_NUMBER</div>
```
- Date is encoded in the `data-testid` attribute (format: `MM/DD/YYYY`)
- Inner HTML is just the day number — **no price info in the inline calendar**
- The parent calendar section: `[data-section-id="AVAILABILITY_CALENDAR_INLINE"]`

### CSS classes → availability
| Class | Meaning |
|-------|---------|
| `_1xnkk5ra` | **Available** — regular available day, valid check-in |
| `_697u988` | **Available** — available day (alternates with `_1xnkk5ra`) |
| `_18qb17hx` | **Available** — last night of available window (checkout-adjacent) |
| `_5nf23wc` | **Available** — far future / end of calendar |
| `_1ytdkbl5` | **Booked/Unavailable** — regular booked day |
| `_emqv0i7` | **Booked/Unavailable** — weekend booked day |
| `_riog819` | **Changeover day** — boundary between bookings (unavailable) |

### Month navigation
```
aria-label="Move forward to switch to the next month."
```
There are TWO sets of nav buttons on the page (inline calendar + booking sidebar). Both use the same aria-label — the first one found is the inline calendar.

### Pricing
- The inline calendar does **not** show prices (only day numbers)
- Prices come from loading: `{listing_url}?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD`
- Parse total from body text: `"Total before taxes $XXX"` or `"$XXX × 2 nights"`

---

## Output CSVs

### available_stays_TIMESTAMP.csv
`link | property_name | unit_number | start_date | end_date | total_price`
- 2-night non-overlapping windows where both nights are available
- `total_price` from booking widget (None if fetch failed)

### booked_nights_TIMESTAMP.csv
`link | property_name | unit_number | date_booked | status`
- `status` = `booked` or `likely_not_open`
- **Trailing block detection**: unavailable dates before the last available date = `booked`; unavailable dates after the last available date = `likely_not_open` (host hasn't opened calendar that far)

### reviews_TIMESTAMP.csv
`link | property_name | unit_number | num_reviews | avg_review_score`

---

## Rate Limiting Strategy
- One listing at a time (sequential, not parallel)
- slow_mo=1000ms between every action
- 6s wait after page load, 2s scroll wait, 2.5s after each of 2 month navigation clicks, 4s per pricing load, 1.5s between pricing requests
- Non-overlapping 2-night windows for pricing (roughly half the requests vs sliding window)
- Estimated ~2-3 min per listing, ~60-90 min total for all 31
- No Airbnb account used — anonymous browsing only

---

## Known Limitations
- CSS class names are obfuscated and **may change** when Airbnb deploys updates — rerun `inspect_calendar.py` to re-identify them if calendar data stops working
- Pricing fetch navigates away from the listing page and back — adds significant time per listing if many available windows exist
- Unit number extraction uses regex heuristics — may miss unusual formats
2026-03-28 16:35:02  
---
## Run started: 2026-03-28 16:35:02  (31 listings)

2026-03-28 16:41:22  
---
## Run started: 2026-03-28 16:41:22  (31 listings)

2026-03-28 16:43:39  [1/31] OK     https://www.airbnb.com/rooms/49931996  unit=?  avail=126  booked=0  windows=15  priced=0  reviews=69  score=4.88
2026-03-28 16:45:23  [2/31] OK     https://www.airbnb.com/rooms/1351674021070226317  unit=?  avail=126  booked=0  windows=10  priced=0  reviews=1  score=5.02
2026-03-28 17:08:11  
---
## Run started: 2026-03-28 17:08:11  (31 listings)

2026-03-28 17:13:53  [1/31] OK     https://www.airbnb.com/rooms/49931996  unit=?  avail=126  booked=0  windows=36  priced=0  reviews=69  score=4.88
2026-03-28 17:14:34  [2/31] ERROR  https://www.airbnb.com/rooms/1351674021070226317  — Page.wait_for_timeout: Target page, context or browser has been closed
2026-03-28 17:14:39  [3/31] ERROR  https://www.airbnb.com/rooms/859411360329483540  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:14:44  [4/31] ERROR  https://www.airbnb.com/rooms/47354990  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:14:49  [5/31] ERROR  https://www.airbnb.com/rooms/564846980716582592  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:14:54  [6/31] ERROR  https://www.airbnb.com/rooms/13225921  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:14:59  [7/31] ERROR  https://www.airbnb.com/rooms/733608330309904024  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:04  [8/31] ERROR  https://www.airbnb.com/rooms/36351502  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:09  [9/31] ERROR  https://www.airbnb.com/rooms/1494594522868451704  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:14  [10/31] ERROR  https://www.airbnb.com/rooms/14895700  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:19  [11/31] ERROR  https://www.airbnb.com/rooms/659882298811850147  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:24  [12/31] ERROR  https://www.airbnb.com/rooms/32961319  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:30  [13/31] ERROR  https://www.airbnb.com/rooms/43390500  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:35  [14/31] ERROR  https://www.airbnb.com/rooms/1173408198220862708  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:40  [15/31] ERROR  https://www.airbnb.com/rooms/20048859  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:45  [16/31] ERROR  https://www.airbnb.com/rooms/573474217916601002  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:50  [17/31] ERROR  https://www.airbnb.com/rooms/983678966634889713  — Page.goto: Target page, context or browser has been closed
2026-03-28 17:15:55  [18/31] ERROR  https://www.airbnb.com/rooms/1515547004809606902  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:56:42  
---
## Run started: 2026-03-28 19:56:42  (31 listings)

2026-03-28 19:57:14  [1/31] ERROR  https://www.airbnb.com/rooms/49931996  — 'charmap' codec can't encode character '\u2192' in position 40: character maps to <undefined>
2026-03-28 19:57:52  [2/31] ERROR  https://www.airbnb.com/rooms/1351674021070226317  — 'charmap' codec can't encode character '\u2192' in position 40: character maps to <undefined>
2026-03-28 19:58:11  [3/31] ERROR  https://www.airbnb.com/rooms/859411360329483540  — 'charmap' codec can't encode character '\u2192' in position 40: character maps to <undefined>
2026-03-28 19:58:16  [4/31] ERROR  https://www.airbnb.com/rooms/47354990  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:58:21  [5/31] ERROR  https://www.airbnb.com/rooms/564846980716582592  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:58:26  [6/31] ERROR  https://www.airbnb.com/rooms/13225921  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:58:31  [7/31] ERROR  https://www.airbnb.com/rooms/733608330309904024  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:58:36  [8/31] ERROR  https://www.airbnb.com/rooms/36351502  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:58:41  [9/31] ERROR  https://www.airbnb.com/rooms/1494594522868451704  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:58:46  [10/31] ERROR  https://www.airbnb.com/rooms/14895700  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:58:51  [11/31] ERROR  https://www.airbnb.com/rooms/659882298811850147  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:58:56  [12/31] ERROR  https://www.airbnb.com/rooms/32961319  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:59:01  [13/31] ERROR  https://www.airbnb.com/rooms/43390500  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:59:06  [14/31] ERROR  https://www.airbnb.com/rooms/1173408198220862708  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:59:11  [15/31] ERROR  https://www.airbnb.com/rooms/20048859  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:59:16  [16/31] ERROR  https://www.airbnb.com/rooms/573474217916601002  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:59:21  [17/31] ERROR  https://www.airbnb.com/rooms/983678966634889713  — Page.goto: Target page, context or browser has been closed
2026-03-28 19:59:26  [18/31] ERROR  https://www.airbnb.com/rooms/1515547004809606902  — Page.goto: Target page, context or browser has been closed
2026-03-28 20:01:52  
---
## Run started: 2026-03-28 20:01:52  (31 listings)

2026-03-28 20:07:24  [1/31] OK     https://www.airbnb.com/rooms/49931996  unit=?  avail=95  booked=0  windows=27  priced=0  reviews=69  score=4.88
2026-03-28 20:08:08  
---
## Run started: 2026-03-28 20:08:08  (31 listings)

2026-03-28 20:11:41  
---
## Run started: 2026-03-28 20:11:41  (31 listings)

2026-03-28 20:17:34  [1/31] OK     https://www.airbnb.com/rooms/49931996  unit=?  avail=95  booked=0  windows=27  priced=25  reviews=69  score=4.88
2026-03-28 20:24:56  [2/31] OK     https://www.airbnb.com/rooms/1351674021070226317  unit=?  avail=95  booked=0  windows=27  priced=23  reviews=1  score=5.02
2026-03-28 20:25:09  [3/31] OK     https://www.airbnb.com/rooms/859411360329483540  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=9  score=5.05
2026-03-28 20:25:21  [4/31] OK     https://www.airbnb.com/rooms/47354990  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=76  score=4.89
2026-03-28 20:25:34  [5/31] OK     https://www.airbnb.com/rooms/564846980716582592  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=6  score=4.67
2026-03-28 20:25:47  [6/31] OK     https://www.airbnb.com/rooms/13225921  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=200  score=4.88
2026-03-28 20:26:00  [7/31] OK     https://www.airbnb.com/rooms/733608330309904024  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=63  score=4.87
2026-03-28 20:26:13  [8/31] OK     https://www.airbnb.com/rooms/36351502  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=145  score=4.99
2026-03-28 20:26:25  [9/31] OK     https://www.airbnb.com/rooms/1494594522868451704  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=7  score=5.0
2026-03-28 20:26:38  [10/31] OK     https://www.airbnb.com/rooms/14895700  unit=8-310  avail=0  booked=0  windows=0  priced=0  reviews=79  score=4.82
2026-03-28 20:26:51  [11/31] OK     https://www.airbnb.com/rooms/659882298811850147  unit=D112  avail=0  booked=0  windows=0  priced=0  reviews=81  score=4.99
2026-03-28 20:27:04  [12/31] OK     https://www.airbnb.com/rooms/32961319  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=135  score=4.94
2026-03-28 20:27:17  [13/31] OK     https://www.airbnb.com/rooms/43390500  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=0  score=5.04
2026-03-28 20:27:29  [14/31] OK     https://www.airbnb.com/rooms/1173408198220862708  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=10  score=4.6
2026-03-28 20:27:43  [15/31] OK     https://www.airbnb.com/rooms/20048859  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=55  score=4.82
2026-03-28 20:27:56  [16/31] OK     https://www.airbnb.com/rooms/573474217916601002  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=46  score=4.98
2026-03-28 20:28:09  [17/31] OK     https://www.airbnb.com/rooms/983678966634889713  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=23  score=4.83
2026-03-28 20:28:22  [18/31] OK     https://www.airbnb.com/rooms/1515547004809606902  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=2  score=5.01
2026-03-28 20:28:35  [19/31] OK     https://www.airbnb.com/rooms/1579709870450109135  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=2  score=5.17
2026-03-28 20:28:48  [20/31] OK     https://www.airbnb.com/rooms/960849307156992001  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=99  score=4.95
2026-03-28 20:29:01  [21/31] OK     https://www.airbnb.com/rooms/46194280  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=203  score=4.87
2026-03-28 20:29:13  [22/31] OK     https://www.airbnb.com/rooms/31704158  unit=on  avail=0  booked=0  windows=0  priced=0  reviews=131  score=4.7
2026-03-28 20:29:26  [23/31] OK     https://www.airbnb.com/rooms/756031921076238815  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=129  score=4.97
2026-03-28 20:29:39  [24/31] OK     https://www.airbnb.com/rooms/582663501443755788  unit=w  avail=0  booked=0  windows=0  priced=0  reviews=190  score=4.96
2026-03-28 20:29:53  [25/31] OK     https://www.airbnb.com/rooms/947888229024493083  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=34  score=4.97
2026-03-28 20:30:06  [26/31] OK     https://www.airbnb.com/rooms/990833735613623342  unit=-  avail=0  booked=0  windows=0  priced=0  reviews=66  score=4.88
2026-03-28 20:30:20  [27/31] OK     https://www.airbnb.com/rooms/849431309111773968  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=99  score=4.83
2026-03-28 20:30:33  [28/31] OK     https://www.airbnb.com/rooms/10656126  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=166  score=4.81
2026-03-28 20:30:46  [29/31] OK     https://www.airbnb.com/rooms/48874217  unit=3307  avail=0  booked=0  windows=0  priced=0  reviews=117  score=4.87
2026-03-28 20:30:59  [30/31] OK     https://www.airbnb.com/rooms/886402393022040490  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=116  score=4.97
2026-03-28 20:31:12  [31/31] OK     https://www.airbnb.com/rooms/1573469505878553212  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=7  score=4.86
2026-03-28 20:31:13  Run finished: 2026-03-28 20:31:13

2026-03-28 20:55:12  
---
## Run started: 2026-03-28 20:55:12  (29 listings)

2026-03-28 21:02:41  
---
## Run started: 2026-03-28 21:02:41  (29 listings)

2026-03-28 21:03:22  [1/29] ERROR  https://www.airbnb.com/rooms/859411360329483540  — Page.wait_for_timeout: Target page, context or browser has been closed
2026-03-28 21:03:37  [2/29] ERROR  https://www.airbnb.com/rooms/47354990  — Page.goto: Target page, context or browser has been closed
2026-03-28 21:03:52  [3/29] ERROR  https://www.airbnb.com/rooms/564846980716582592  — Page.goto: Target page, context or browser has been closed
2026-03-28 21:06:07  
---
## Run started: 2026-03-28 21:06:07  (29 listings)

2026-03-28 21:15:41  [1/29] OK     https://www.airbnb.com/rooms/859411360329483540  unit=?  avail=95  booked=0  windows=33  priced=32  reviews=9  score=5.05
2026-03-28 21:16:02  [2/29] OK     https://www.airbnb.com/rooms/47354990  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=76  score=4.89
2026-03-28 21:16:22  [3/29] OK     https://www.airbnb.com/rooms/564846980716582592  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=6  score=4.67
2026-03-28 21:16:42  [4/29] OK     https://www.airbnb.com/rooms/13225921  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=200  score=4.88
2026-03-28 21:17:02  [5/29] OK     https://www.airbnb.com/rooms/733608330309904024  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=63  score=4.87
2026-03-28 21:17:23  [6/29] OK     https://www.airbnb.com/rooms/36351502  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=145  score=4.99
2026-03-28 21:17:43  [7/29] OK     https://www.airbnb.com/rooms/1494594522868451704  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=7  score=5.17
2026-03-28 21:18:03  [8/29] OK     https://www.airbnb.com/rooms/14895700  unit=8-310  avail=0  booked=0  windows=0  priced=0  reviews=79  score=4.82
2026-03-28 21:18:23  [9/29] OK     https://www.airbnb.com/rooms/659882298811850147  unit=D112  avail=0  booked=0  windows=0  priced=0  reviews=81  score=4.99
2026-03-28 21:18:44  [10/29] OK     https://www.airbnb.com/rooms/32961319  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=135  score=4.94
2026-03-28 21:19:04  [11/29] OK     https://www.airbnb.com/rooms/43390500  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=40  score=5.17
2026-03-28 21:19:24  [12/29] OK     https://www.airbnb.com/rooms/1173408198220862708  unit=?  avail=0  booked=0  windows=0  priced=0  reviews=10  score=4.6
2026-03-28 21:22:39  
---
## Run started: 2026-03-28 21:22:39  (29 listings)

2026-03-28 21:30:15  [1/29] OK     https://www.airbnb.com/rooms/859411360329483540  unit=?  avail=69  booked=26  windows=33  priced=32  reviews=9  score=5.05
2026-03-28 21:35:10  [2/29] OK     https://www.airbnb.com/rooms/47354990  unit=?  avail=37  booked=58  windows=17  priced=17  reviews=76  score=4.89
2026-03-28 21:40:24  [3/29] OK     https://www.airbnb.com/rooms/564846980716582592  unit=?  avail=40  booked=55  windows=18  priced=17  reviews=6  score=4.67
2026-03-28 21:49:28  [4/29] OK     https://www.airbnb.com/rooms/13225921  unit=?  avail=67  booked=28  windows=33  priced=30  reviews=200  score=4.88
2026-03-28 21:57:57  [5/29] OK     https://www.airbnb.com/rooms/733608330309904024  unit=?  avail=72  booked=23  windows=34  priced=12  reviews=63  score=4.87
2026-03-28 22:05:45  [6/29] OK     https://www.airbnb.com/rooms/36351502  unit=?  avail=56  booked=39  windows=27  priced=0  reviews=145  score=4.99
2026-03-28 22:13:00  [7/29] OK     https://www.airbnb.com/rooms/1494594522868451704  unit=?  avail=44  booked=21  windows=21  priced=21  reviews=7  score=5.0
2026-03-28 22:19:16  [8/29] OK     https://www.airbnb.com/rooms/14895700  unit=8-310  avail=33  booked=32  windows=14  priced=14  reviews=79  score=4.82
2026-03-28 22:23:21  [9/29] OK     https://www.airbnb.com/rooms/659882298811850147  unit=D112  avail=16  booked=49  windows=7  priced=7  reviews=81  score=4.99
2026-03-28 22:32:04  [10/29] OK     https://www.airbnb.com/rooms/32961319  unit=?  avail=57  booked=8  windows=28  priced=25  reviews=135  score=4.94
2026-03-28 22:38:56  [11/29] OK     https://www.airbnb.com/rooms/43390500  unit=?  avail=43  booked=52  windows=21  priced=21  reviews=0  score=5.04
2026-03-28 22:50:32  [12/29] OK     https://www.airbnb.com/rooms/1173408198220862708  unit=?  avail=81  booked=14  windows=40  priced=30  reviews=10  score=4.6
2026-03-28 22:56:16  [13/29] OK     https://www.airbnb.com/rooms/20048859  unit=?  avail=53  booked=42  windows=26  priced=9  reviews=55  score=4.82
2026-03-28 23:01:56  [14/29] OK     https://www.airbnb.com/rooms/573474217916601002  unit=?  avail=52  booked=43  windows=25  priced=14  reviews=46  score=4.98
2026-03-28 23:05:18  [15/29] OK     https://www.airbnb.com/rooms/983678966634889713  unit=?  avail=18  booked=47  windows=8  priced=6  reviews=23  score=4.83
2026-03-28 23:11:23  [16/29] OK     https://www.airbnb.com/rooms/1515547004809606902  unit=?  avail=58  booked=37  windows=27  priced=9  reviews=2  score=5.01
2026-03-28 23:27:39  [17/29] OK     https://www.airbnb.com/rooms/1579709870450109135  unit=?  avail=95  booked=0  windows=47  priced=37  reviews=4093  score=4.67
2026-03-28 23:35:39  [18/29] OK     https://www.airbnb.com/rooms/960849307156992001  unit=?  avail=71  booked=24  windows=35  priced=2  reviews=100  score=4.94
2026-03-28 23:44:49  [19/29] OK     https://www.airbnb.com/rooms/46194280  unit=?  avail=64  booked=1  windows=32  priced=15  reviews=203  score=4.87
2026-03-28 23:51:02  [20/29] OK     https://www.airbnb.com/rooms/31704158  unit=on  avail=52  booked=43  windows=25  priced=3  reviews=131  score=4.7
2026-03-28 23:59:02  [21/29] OK     https://www.airbnb.com/rooms/756031921076238815  unit=?  avail=66  booked=29  windows=31  priced=29  reviews=129  score=4.97
2026-03-29 11:16:38  
---
## Run started: 2026-03-29 11:16:38  (8 listings)

2026-03-29 11:20:53  [1/8] OK     https://www.airbnb.com/rooms/582663501443755788  unit=w  avail=50  booked=44  windows=21  priced=15  reviews=190  score=4.96
2026-03-29 11:27:13  [2/8] OK     https://www.airbnb.com/rooms/947888229024493083  unit=?  avail=51  booked=13  windows=25  priced=24  reviews=34  score=4.97
2026-03-29 11:33:13  [3/8] OK     https://www.airbnb.com/rooms/990833735613623342  unit=-  avail=63  booked=31  windows=31  priced=7  reviews=66  score=4.88
2026-03-29 11:41:15  [4/8] OK     https://www.airbnb.com/rooms/849431309111773968  unit=?  avail=79  booked=15  windows=38  priced=7  reviews=99  score=4.83
2026-03-29 11:46:31  [5/8] OK     https://www.airbnb.com/rooms/10656126  unit=?  avail=39  booked=25  windows=19  priced=19  reviews=166  score=4.81
2026-03-29 11:51:40  [6/8] OK     https://www.airbnb.com/rooms/48874217  unit=3307  avail=35  booked=29  windows=17  priced=16  reviews=117  score=4.87
2026-03-29 11:55:55  [7/8] OK     https://www.airbnb.com/rooms/886402393022040490  unit=?  avail=34  booked=59  windows=15  priced=3  reviews=116  score=4.97
2026-03-29 11:59:11  [8/8] OK     https://www.airbnb.com/rooms/1573469505878553212  unit=?  avail=13  booked=51  windows=6  priced=5  reviews=7  score=4.86
2026-03-29 11:59:11  Run finished: 2026-03-29 11:59:11

