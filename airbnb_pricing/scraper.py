import re
from calendar import monthrange
from datetime import date, timedelta
from playwright.async_api import Page


MONTHS_TO_CHECK = 3

# CSS classes observed on the inline availability calendar
# day_map stores the primary CSS class (first token) per date
AVAILABLE_CLASSES   = {"_1xnkk5ra", "_697u988", "_18qb17hx", "_5nf23wc"}
UNAVAILABLE_CLASSES = {"_1ytdkbl5", "_emqv0i7", "_riog819", "_1rl50hqv"}

UNIT_PATTERNS = [
    r'\b(\d{1,2}-\d{2,4})\b',
    r'(?:unit|apt|apartment|#)\s*([A-Z0-9-]+)',
    r'\bsuite\s+([A-Z0-9-]+)',
    r'\b([A-Z]?\d{3,4}[A-Z]?)\b',
]


def extract_unit(title: str) -> str | None:
    for pattern in UNIT_PATTERNS:
        m = re.search(pattern, title, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def primary_class(css_class: str) -> str:
    """Return the first meaningful CSS class (ignore 'notranslate')."""
    for cls in css_class.split():
        if cls != "notranslate":
            return cls
    return ""


def is_available(cls: str) -> bool:
    return cls in AVAILABLE_CLASSES


def is_checkin_eligible(cls: str) -> bool:
    return cls in AVAILABLE_CLASSES


async def scrape_listing(page: Page, url: str) -> dict:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)

        # ── Title & unit number ────────────────────────────────────────────
        title = ""
        for sel in ['h1', '[data-testid="listing-title"]', 'title']:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    title = (await el.text_content() or "").strip()
                    if title:
                        break
            except Exception:
                continue

        unit = extract_unit(title)

        # ── Reviews ────────────────────────────────────────────────────────
        num_reviews = None
        avg_score = None
        try:
            body_text = await page.locator("body").text_content() or ""
            combined = re.search(
                r'(\d\.\d{1,2})\s*(?:·|•|/|out of 5)?\s*[\(]?\s*(\d+)\s*review',
                body_text, re.IGNORECASE
            )
            if combined:
                avg_score = float(combined.group(1))
                num_reviews = int(combined.group(2))
            else:
                rev = re.search(r'(\d+)\s*review[s]?\s*(?:·|•|,)?\s*(\d\.\d{1,2})', body_text, re.IGNORECASE)
                if rev:
                    num_reviews = int(rev.group(1))
                    avg_score = float(rev.group(2))
                else:
                    c = re.search(r'(\d+)\s+review', body_text, re.IGNORECASE)
                    if c:
                        num_reviews = int(c.group(1))
                    s = re.search(r'\b([45]\.\d{1,2})\b', body_text)
                    if s:
                        avg_score = float(s.group(1))
        except Exception:
            pass

        # ── Scroll to inline availability calendar ─────────────────────────
        try:
            cal = page.locator('[data-section-id="AVAILABILITY_CALENDAR_INLINE"]').first
            if await cal.is_visible(timeout=3000):
                await cal.scroll_into_view_if_needed()
                await page.wait_for_timeout(2000)
        except Exception:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await page.wait_for_timeout(2000)

        # ── Scrape calendar day divs across 3 months ───────────────────────
        today = date.today()
        # Cutoff = last day of the 3rd calendar month from today
        cutoff_month = today.month + 3
        cutoff_year = today.year + (cutoff_month - 1) // 12
        cutoff_month = ((cutoff_month - 1) % 12) + 1
        cutoff = date(cutoff_year, cutoff_month, monthrange(cutoff_year, cutoff_month)[1])

        day_map: dict[date, str] = {}  # date → primary CSS class

        for month_offset in range(MONTHS_TO_CHECK):
            if month_offset > 0:
                advanced = False
                for selector in [
                    '[aria-label="Move forward to switch to the next month."]',
                    'button[aria-label*="next month" i]',
                    'button[aria-label*="forward" i]',
                ]:
                    try:
                        btn = page.locator(selector).first
                        if await btn.is_visible(timeout=2000):
                            await btn.scroll_into_view_if_needed()
                            await btn.click()
                            await page.wait_for_timeout(3000)
                            advanced = True
                            break
                    except Exception:
                        continue
                if not advanced:
                    print(f"  WARNING: could not advance to month {month_offset + 1}")
                    break

            divs = await page.evaluate("""
                () => {
                    const results = [];
                    // Scope ONLY to the inline availability calendar, not the booking sidebar
                    const container = document.querySelector('[data-section-id="AVAILABILITY_CALENDAR_INLINE"]')
                                   || document.querySelector('[data-testid="inline-availability-calendar"]')
                                   || document;
                    container.querySelectorAll('div[data-testid^="calendar-day-"]').forEach(el => {
                        results.push({
                            testid: el.getAttribute('data-testid'),
                            cssClass: el.className,
                        });
                    });
                    return results;
                }
            """)

            found = 0
            for div in divs:
                testid = div["testid"]
                date_str = testid.replace("calendar-day-", "")
                try:
                    m, d, y = date_str.split("/")
                    d_obj = date(int(y), int(m), int(d))
                except Exception:
                    continue

                if d_obj < today or d_obj > cutoff:
                    continue

                if d_obj not in day_map:
                    day_map[d_obj] = primary_class(div["cssClass"])
                    found += 1

            print(f"  month {month_offset + 1}: {found} new future dates collected")

        # ── Get pricing for valid check-in 2-night windows only ────────────
        stays = build_available_windows(day_map)
        print(f"  fetching prices for {len(stays)} check-in-eligible 2-night windows...")

        for stay in stays:
            stay["total_price"] = await fetch_price(page, url, stay["start_date"], stay["end_date"])
            await page.wait_for_timeout(1500)

        return {
            "url": url,
            "title": title,
            "unit": unit,
            "days": day_map,
            "stays": stays,
            "num_reviews": num_reviews,
            "avg_review_score": avg_score,
        }

    except Exception as e:
        return {"url": url, "title": "", "unit": None, "days": {}, "stays": [], "error": str(e)}


async def fetch_price(page: Page, base_url: str, check_in: str, check_out: str) -> float | None:
    """Load listing with check-in/check-out dates and parse the total price."""
    try:
        priced_url = f"{base_url}?check_in={check_in}&check_out={check_out}"
        await page.goto(priced_url, wait_until="domcontentloaded", timeout=30000)
        # Wait for network to go idle so the booking widget API call finishes
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)  # extra buffer after network idle

        # Scroll booking sidebar into view to trigger rendering
        try:
            sidebar = page.locator('[data-section-id="BOOK_IT_SIDEBAR"]').first
            if await sidebar.is_visible(timeout=3000):
                await sidebar.scroll_into_view_if_needed()
                await page.wait_for_timeout(1500)
        except Exception:
            pass

        # Read booking sidebar text — price elements have no data-testid so we parse text
        body = ""
        try:
            sidebar_el = page.locator('[data-section-id="BOOK_IT_SIDEBAR"]').first
            if await sidebar_el.is_visible(timeout=3000):
                body = await sidebar_el.text_content() or ""
        except Exception:
            pass
        if not body:
            body = await page.locator("body").text_content() or ""

        # "$737 for 2 nights" — Airbnb shows total directly in this format
        for_nights = re.search(r'\$([\d,]+)\s+for\s+\d+\s+nights?', body, re.IGNORECASE)
        if for_nights:
            return float(for_nights.group(1).replace(",", ""))

        # "$X per night" × N nights line item (fallback format)
        nightly = re.search(r'\$([\d,]+)\s*(?:x|×)\s*\d+\s*night', body, re.IGNORECASE)
        if nightly:
            # In this format the number before × is the nightly rate; multiply by 2
            return float(nightly.group(1).replace(",", "")) * 2

        # "Total before taxes $X" or "Total $X"
        total = re.search(r'total\s*(?:before\s*taxes?)?\s*\$\s*([\d,]+)', body, re.IGNORECASE)
        if total:
            return float(total.group(1).replace(",", ""))

        # Debug: print a snippet of body text to help diagnose
        snippet = body.replace("\n", " ")[:600].encode("ascii", errors="replace").decode("ascii")
        print(f"  [price debug] no price found for {check_in}->{check_out}. body snippet: {snippet}")

    except Exception as e:
        print(f"  [price debug] exception for {check_in}->{check_out}: {e}")
    return None


def build_available_windows(day_map: dict[date, str]) -> list[dict]:
    """
    Find non-overlapping 2-night windows where:
    - Night 1 (check-in) must be _1ytdkbl5 (check-in eligible)
    - Night 2 can be _1ytdkbl5 or _emqv0i7 (available to sleep, even if checkout-only)
    Non-overlapping: after window (D, D+1), next window starts at D+2.
    """
    checkin_dates = sorted(d for d, cls in day_map.items() if is_checkin_eligible(cls))
    windows = []
    i = 0
    while i < len(checkin_dates):
        d = checkin_dates[i]
        next_d = d + timedelta(days=1)
        if next_d in day_map and is_available(day_map[next_d]):
            windows.append({
                "start_date": d.isoformat(),
                "end_date": (next_d + timedelta(days=1)).isoformat(),
                "total_price": None,
            })
            i += 2  # skip to next non-overlapping window
        else:
            i += 1
    return windows


def build_booked_nights(day_map: dict[date, str]) -> list[dict]:
    """Tag unavailable dates as booked or likely_not_open."""
    available_dates = [d for d, cls in day_map.items() if is_available(cls)]
    last_available = max(available_dates) if available_dates else None

    booked = []
    for d in sorted(day_map.keys()):
        if not is_available(day_map[d]):
            status = "likely_not_open" if (last_available is None or d > last_available) else "booked"
            booked.append({"date": d.isoformat(), "status": status})
    return booked
