"""
Re-fetch pricing for null-price rows in available_stays_20260329.csv.
Only processes the 10 listings identified as having >50% missing prices.
Writes a new available_stays_refetch_TIMESTAMP.csv with results.
"""
import asyncio
import csv
import os
from datetime import datetime
from playwright.async_api import async_playwright
from scraper import fetch_price, scrape_listing, build_available_windows

# The 10 listings with >50% null prices
# Value is min_nights for that listing (default 2; use 3 where enforced)
TARGET_LISTINGS = {
    # "https://www.airbnb.com/rooms/36351502":          2,  # done in partial run
    # "https://www.airbnb.com/rooms/960849307156992001": 2,  # done in partial run
    # "https://www.airbnb.com/rooms/1515547004809606902": 2,  # done in partial run
    # "https://www.airbnb.com/rooms/733608330309904024": 2,  # done in partial run
    # "https://www.airbnb.com/rooms/20048859":          2,  # done in partial run
    # "https://www.airbnb.com/rooms/31704158":          2,  # done in partial run
    "https://www.airbnb.com/rooms/849431309111773968": 3,  # 3-night minimum
    "https://www.airbnb.com/rooms/886402393022040490": 3,  # 3-night minimum
    "https://www.airbnb.com/rooms/990833735613623342": 4,  # 4-night minimum
    "https://www.airbnb.com/rooms/46194280":          3,  # 3-night minimum
}
TARGET_LINKS = set(TARGET_LISTINGS.keys())

SOURCE_CSV = "output/available_stays_20260329.csv"


async def run():
    # Load null-price rows for target listings (only those with min_nights=2)
    # For min_nights>2 listings we re-scrape the calendar to get correct windows
    with open(SOURCE_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        null_rows = [
            r for r in reader
            if r["link"] in TARGET_LINKS
            and not r["total_price"].strip()
            and TARGET_LISTINGS[r["link"]] == 2
        ]

    multi_night_links = {k for k, v in TARGET_LISTINGS.items() if v > 2}

    print(f"Found {len(null_rows)} null-price 2-night rows to refetch")
    print(f"Will re-scrape {len(multi_night_links)} listing(s) with >2-night minimum")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"output/available_stays_refetch_{timestamp}.csv"

    ctx_args = dict(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 900},
        locale="en-US",
    )

    # Get property name mapping from source CSV
    prop_map = {}
    with open(SOURCE_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            prop_map[r["link"]] = (r["property_name"], r["unit_number"])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)

        with open(out_path, "w", newline="", encoding="utf-8") as fout:
            writer = csv.writer(fout)
            writer.writerow(["link", "property_name", "unit_number", "start_date", "end_date", "total_price"])
            fout.flush()

            from collections import defaultdict
            by_listing = defaultdict(list)
            for row in null_rows:
                by_listing[row["link"]].append(row)

            # Add multi-night listings as empty entries so they get processed
            for link in multi_night_links:
                if link not in by_listing:
                    by_listing[link] = []

            total_listings = len(by_listing)
            done = 0

            for i, (link, rows) in enumerate(by_listing.items(), 1):
                min_nights = TARGET_LISTINGS[link]
                prop, unit = prop_map.get(link, ("unknown", ""))

                context = await browser.new_context(**ctx_args)
                page = await context.new_page()

                try:
                    if min_nights > 2:
                        # Re-scrape calendar to build correct 3-night windows
                        print(f"\n[{i}/{total_listings}] Re-scraping calendar for {link} (3-night min)")
                        result = await scrape_listing(page, link, min_nights=3)
                        stays = result.get("stays", [])
                        unit = result.get("unit") or unit
                        print(f"  {len(stays)} 3-night windows found")
                        for stay in stays:
                            writer.writerow([link, prop, unit, stay["start_date"], stay["end_date"], stay["total_price"] or ""])
                            fout.flush()
                            done += 1
                    else:
                        print(f"\n[{i}/{total_listings}] {link}  ({len(rows)} windows to refetch)")
                        for row in rows:
                            price = await fetch_price(page, link, row["start_date"], row["end_date"])
                            writer.writerow([link, prop, unit, row["start_date"], row["end_date"], price or ""])
                            fout.flush()
                            done += 1
                            status = f"${price}" if price else "null"
                            print(f"  {row['start_date']} -> {row['end_date']}  {status}")
                            await page.wait_for_timeout(1500)
                finally:
                    await context.close()

                if i < total_listings:
                    print(f"  pausing 15s...")
                    await asyncio.sleep(15)

        await browser.close()

    print(f"\nDone. Results saved to {out_path}")

    # Summary
    with open(out_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))[1:]
    priced = sum(1 for r in rows if r[5].strip())
    print(f"Priced: {priced}/{len(rows)}")


if __name__ == "__main__":
    asyncio.run(run())
