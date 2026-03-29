"""
Inspect the inline availability calendar and pricing widget.
Loads a listing with check_in/check_out dates and dumps price-related DOM elements.
"""
import asyncio
from playwright.async_api import async_playwright

PRICED_URL = "https://www.airbnb.com/rooms/859411360329483540"


async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()

        print(f"Loading {PRICED_URL} ...")
        await page.goto(PRICED_URL, wait_until="domcontentloaded", timeout=30000)

        # Wait for network to settle so booking widget API call finishes
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
            print("Network idle reached")
        except Exception:
            print("Network idle timed out, continuing anyway")

        await page.wait_for_timeout(2000)

        # Scroll booking sidebar into view
        try:
            sidebar = page.locator('[data-section-id="BOOK_IT_SIDEBAR"]').first
            if await sidebar.is_visible(timeout=3000):
                await sidebar.scroll_into_view_if_needed()
                await page.wait_for_timeout(1500)
                print("Scrolled to booking sidebar\n")
        except Exception:
            print("Could not find BOOK_IT_SIDEBAR, scrolling to top-right area")
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1500)

        # ── Check if inline calendar section exists ──
        cal_section = await page.evaluate("""
            () => {
                const inline = document.querySelector('[data-section-id="AVAILABILITY_CALENDAR_INLINE"]');
                const fallback = document.querySelector('[data-testid="inline-availability-calendar"]');
                return {
                    inline_found: !!inline,
                    fallback_found: !!fallback,
                    page_title: document.title,
                    body_snippet: (document.body.innerText || '').slice(0, 300),
                };
            }
        """)
        print(f"Page title: {cal_section['page_title']}")
        print(f"AVAILABILITY_CALENDAR_INLINE found: {cal_section['inline_found']}")
        print(f"inline-availability-calendar found: {cal_section['fallback_found']}")
        print(f"Body snippet: {cal_section['body_snippet'][:200]}\n")

        # ── Scroll to calendar and wait ──
        if cal_section['inline_found'] or cal_section['fallback_found']:
            try:
                sel = '[data-section-id="AVAILABILITY_CALENDAR_INLINE"]' if cal_section['inline_found'] else '[data-testid="inline-availability-calendar"]'
                cal = page.locator(sel).first
                await cal.scroll_into_view_if_needed()
                print("Scrolled to calendar section, waiting 4s for calendar to render...")
                await page.wait_for_timeout(4000)
            except Exception as e:
                print(f"Scroll failed: {e}")
        else:
            print("No calendar section found — scrolling to middle of page")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await page.wait_for_timeout(3000)

        # ── Dump all calendar-day divs ──
        days = await page.evaluate("""
            () => {
                const container = document.querySelector('[data-section-id="AVAILABILITY_CALENDAR_INLINE"]')
                               || document.querySelector('[data-testid="inline-availability-calendar"]')
                               || document;
                const results = [];
                container.querySelectorAll('div[data-testid^="calendar-day-"]').forEach(el => {
                    results.push({
                        testid: el.getAttribute('data-testid'),
                        cssClass: el.className,
                        text: (el.textContent || '').trim(),
                    });
                });
                return results;
            }
        """)

        print(f"Calendar-day divs found: {len(days)}")
        if days:
            print(f"\n{'Date':<15} {'Class':<25} {'Text'}")
            print("-" * 55)
            for d in days[:20]:
                date_str = d['testid'].replace('calendar-day-', '')
                print(f"{date_str:<15} {d['cssClass']:<25} {d['text']}")
            if len(days) > 20:
                print(f"  ... and {len(days) - 20} more")

            classes = {}
            for d in days:
                cls = d['cssClass']
                classes[cls] = classes.get(cls, 0) + 1
            print(f"\nUnique CSS classes seen:")
            for cls, count in sorted(classes.items(), key=lambda x: -x[1]):
                print(f"  {cls:<30} x{count}")
        else:
            # Dump all data-section-id values to see what sections ARE present
            sections = await page.evaluate("""
                () => [...document.querySelectorAll('[data-section-id]')].map(el => el.getAttribute('data-section-id'))
            """)
            print(f"\nAll data-section-id values on page ({len(sections)} total):")
            for s in sections:
                print(f"  {s}")

        print("\nWaiting 30s before closing...")
        await page.wait_for_timeout(30000)
        await browser.close()


asyncio.run(inspect())
