#!/usr/bin/env python3
"""
Airbnb transaction history CSV exporter.

First run: opens a browser for manual login, then saves session to disk.
Subsequent runs: reuses saved session — no login needed.

Usage:
    python airbnb_export.py
    python airbnb_export.py --output ~/Documents/airbnb

Dependencies:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

SESSION_FILE = Path(__file__).parent / ".airbnb_session.json"
TRANSACTION_URL = "https://www.airbnb.com/users/transaction_history"


def save_session(context):
    storage = context.storage_state()
    SESSION_FILE.write_text(json.dumps(storage))
    print(f"Session saved to {SESSION_FILE}")


def manual_login(playwright):
    """Open a visible browser, let the user log in, then save session."""
    print("No saved session found. Opening browser for manual login...")
    print("Log in to Airbnb, then press Enter here to continue.")

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.airbnb.com/login")

    input("  --> Press Enter once you are fully logged in: ")

    save_session(context)
    browser.close()


DOWNLOADS_DIR = Path.home() / "Downloads"


def wait(seconds: int, reason: str):
    print(f"Waiting {seconds}s — {reason}...")
    time.sleep(seconds)



def screenshot(page, label):
    path = DOWNLOADS_DIR / f"airbnb_debug_{label}.png"
    page.screenshot(path=str(path))
    print(f"  [debug] screenshot saved: {path}")


def click_paid_tab(page):
    """Click the 'Paid' tab — tries multiple selectors in case Airbnb changed their DOM."""
    selectors = [
        lambda: page.get_by_role("link", name="Paid").click(),
        lambda: page.get_by_role("tab",  name="Paid").click(),
        lambda: page.get_by_text("Paid", exact=True).first.click(),
        lambda: page.locator("[data-testid='sidebar-navigation-row']", has_text="Paid").click(),
    ]
    for attempt in selectors:
        try:
            attempt()
            return
        except Exception:
            continue
    screenshot(page, "paid_tab_not_found")
    raise RuntimeError(
        "Could not find the 'Paid' tab. A debug screenshot was saved to Downloads. "
        "Airbnb may have changed their page layout."
    )


def export_csv(playwright) -> Path:
    """Reuse saved session to export the CSV and return the saved file path."""
    storage_state = json.loads(SESSION_FILE.read_text())

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
        storage_state=storage_state,
        accept_downloads=True,
    )
    page = context.new_page()

    print(f"Navigating to {TRANSACTION_URL} ...")
    page.goto(TRANSACTION_URL, wait_until="networkidle", timeout=60_000)
    wait(3, "page fully loaded")

    print("Clicking 'Paid' tab...")
    click_paid_tab(page)
    wait(4, "Paid tab loaded")

    print("Clicking 'Export CSV' to open dialog...")
    try:
        # There may be two 'Export CSV' buttons — the page-level one opens the modal
        page.get_by_role("button", name="Export CSV").first.click(timeout=15_000)
    except Exception:
        screenshot(page, "export_csv_not_found")
        raise RuntimeError(
            "Could not find the 'Export CSV' button. A debug screenshot was saved to Downloads."
        )
    wait(4, "export dialog loaded")

    print("Clicking 'Export CSV' in the dialog to download...")
    try:
        with page.expect_download(timeout=300_000) as download_info:
            # The modal has a black 'Export CSV' button — it's the last/nth(1) one on the page
            page.get_by_role("button", name="Export CSV").last.click(timeout=15_000)
    except Exception:
        # Fallback: try the 'Download CSV' option inside the modal
        try:
            with page.expect_download(timeout=300_000) as download_info:
                page.get_by_text("Download CSV").click(timeout=15_000)
        except Exception:
            screenshot(page, "download_button_not_found")
            raise RuntimeError(
                "Could not find the download button in the export dialog. "
                "A debug screenshot was saved to Downloads."
            )

    download = download_info.value
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = DOWNLOADS_DIR / f"airbnb_{timestamp}.csv"
    download.save_as(dest)

    print(f"\nReport downloaded to: {dest}")

    # Persist refreshed cookies
    save_session(context)
    browser.close()

    return dest


def main():
    parser = argparse.ArgumentParser(description="Export Airbnb transaction history to CSV.")
    parser.add_argument(
        "--relogin",
        action="store_true",
        help="Force a fresh manual login even if a session file exists",
    )
    args = parser.parse_args()

    with sync_playwright() as playwright:
        if not SESSION_FILE.exists() or args.relogin:
            manual_login(playwright)

        export_csv(playwright)


if __name__ == "__main__":
    main()
