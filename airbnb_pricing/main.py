import asyncio
import csv
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright
from scraper import scrape_listing, build_booked_nights

INTER_LISTING_PAUSE = 15  # seconds between listings

# ── Airbnb listing URLs ────────────────────────────────────────────────────────
KAMAOLE_SANDS = [
    # "https://www.airbnb.com/rooms/49931996",              # done
    # "https://www.airbnb.com/rooms/1351674021070226317",   # done
    # "https://www.airbnb.com/rooms/859411360329483540",    # done
    # "https://www.airbnb.com/rooms/47354990",              # done
    # "https://www.airbnb.com/rooms/564846980716582592",    # done
    # "https://www.airbnb.com/rooms/13225921",              # done
    # "https://www.airbnb.com/rooms/733608330309904024",    # done
    # "https://www.airbnb.com/rooms/36351502",              # done
    # "https://www.airbnb.com/rooms/1494594522868451704",   # done
    # "https://www.airbnb.com/rooms/14895700",              # done
    # "https://www.airbnb.com/rooms/659882298811850147",    # done
    # "https://www.airbnb.com/rooms/32961319",              # done
    # "https://www.airbnb.com/rooms/43390500",              # done
    # "https://www.airbnb.com/rooms/1173408198220862708",   # done
    # "https://www.airbnb.com/rooms/20048859",              # done
    # "https://www.airbnb.com/rooms/573474217916601002",    # done
    # "https://www.airbnb.com/rooms/983678966634889713",    # done
]

MAUI_VISTA = [
    # "https://www.airbnb.com/rooms/1515547004809606902",   # done
    # "https://www.airbnb.com/rooms/1579709870450109135",   # done
    # "https://www.airbnb.com/rooms/960849307156992001",    # done
    # "https://www.airbnb.com/rooms/46194280",              # done
    # "https://www.airbnb.com/rooms/31704158",              # done
    # "https://www.airbnb.com/rooms/756031921076238815",    # done
    "https://www.airbnb.com/rooms/582663501443755788",
    "https://www.airbnb.com/rooms/947888229024493083",
    "https://www.airbnb.com/rooms/990833735613623342",
    "https://www.airbnb.com/rooms/849431309111773968",
    "https://www.airbnb.com/rooms/10656126",
    "https://www.airbnb.com/rooms/48874217",
    "https://www.airbnb.com/rooms/886402393022040490",
    "https://www.airbnb.com/rooms/1573469505878553212",
]

URLS = KAMAOLE_SANDS + MAUI_VISTA
GROUP_MAP = {u: "kamaole_sands" for u in KAMAOLE_SANDS}
GROUP_MAP.update({u: "maui_vista" for u in MAUI_VISTA})
# ──────────────────────────────────────────────────────────────────────────────


CLAUDE_MD = os.path.join(os.path.dirname(__file__), "CLAUDE.md")


def log_to_claude_md(text: str):
    """Append a timestamped line to CLAUDE.md under the Run Log section."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CLAUDE_MD, "a", encoding="utf-8") as f:
        f.write(f"{ts}  {text}\n")


async def run(urls: list[str]):
    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    available_path = f"output/available_stays_{timestamp}.csv"
    booked_path    = f"output/booked_nights_{timestamp}.csv"
    reviews_path   = f"output/reviews_{timestamp}.csv"

    run_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_to_claude_md(f"\n---\n## Run started: {run_start}  ({len(urls)} listings)\n")

    ctx_args = dict(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 900},
        locale="en-US",
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)

        with (
            open(available_path, "w", newline="", encoding="utf-8") as af,
            open(booked_path,    "w", newline="", encoding="utf-8") as bf,
            open(reviews_path,   "w", newline="", encoding="utf-8") as rf,
        ):
            avail_w   = csv.writer(af)
            booked_w  = csv.writer(bf)
            reviews_w = csv.writer(rf)

            avail_w.writerow(["link", "property_name", "unit_number", "start_date", "end_date", "total_price"])
            booked_w.writerow(["link", "property_name", "unit_number", "date_booked", "status"])
            reviews_w.writerow(["link", "property_name", "unit_number", "num_reviews", "avg_review_score"])
            af.flush(); bf.flush(); rf.flush()

            for i, url in enumerate(urls, 1):
                group = GROUP_MAP.get(url, "unknown")
                print(f"\n[{i}/{len(urls)}] [{group}] {url}")

                # Fresh context per listing — resets cookies/session so Airbnb
                # can't flag the session after many pricing page navigations.
                context = await browser.new_context(**ctx_args)
                page    = await context.new_page()

                try:
                    result = await scrape_listing(page, url)
                finally:
                    await context.close()

                days   = result.get("days", {})
                stays  = result.get("stays", [])
                error  = result.get("error")

                if error:
                    print(f"  ERROR: {error}")
                    log_to_claude_md(f"[{i}/{len(urls)}] ERROR  {url}  — {error}")
                else:
                    unit = result.get("unit") or ""

                    for stay in stays:
                        avail_w.writerow([url, group, unit, stay["start_date"], stay["end_date"], stay["total_price"]])

                    for night in build_booked_nights(days):
                        booked_w.writerow([url, group, unit, night["date"], night["status"]])

                    reviews_w.writerow([url, group, unit, result.get("num_reviews", ""), result.get("avg_review_score", "")])

                    af.flush(); bf.flush(); rf.flush()

                    avail_n  = len([v for v in days.values() if v in {"_1xnkk5ra", "_697u988", "_18qb17hx", "_5nf23wc"}])
                    booked_n = len([v for v in days.values() if v in {"_1ytdkbl5", "_emqv0i7", "_riog819", "_1rl50hqv"}])
                    priced   = sum(1 for s in stays if s["total_price"] is not None)
                    summary  = (
                        f"unit={unit or '?'}  avail={avail_n}  booked={booked_n}  "
                        f"windows={len(stays)}  priced={priced}  "
                        f"reviews={result.get('num_reviews','?')}  score={result.get('avg_review_score','?')}"
                    )
                    print(f"  done  {summary}")
                    log_to_claude_md(f"[{i}/{len(urls)}] OK     {url}  {summary}")

                if i < len(urls):
                    print(f"  pausing {INTER_LISTING_PAUSE}s before next listing...")
                    await asyncio.sleep(INTER_LISTING_PAUSE)

        await browser.close()

    log_to_claude_md(f"Run finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"\nDone.\n  {available_path}\n  {booked_path}\n  {reviews_path}")


if __name__ == "__main__":
    urls = sys.argv[1:] if len(sys.argv) > 1 else URLS

    if not urls:
        print("No URLs provided.")
        sys.exit(1)

    print(f"Scraping {len(urls)} listings sequentially...\n")
    asyncio.run(run(urls))
