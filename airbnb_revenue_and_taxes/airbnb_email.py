#!/usr/bin/env python3
"""
airbnb_email.py — Sends a Gmail with the YTD Airbnb tax summary (complete
months only) as an HTML table, and attaches the xlsx report.

Usage:
    python airbnb_email.py <path/to/airbnb_taxes_*.xlsx>

Gmail setup:
    Requires a Gmail App Password (Google account → Security → App Passwords).
    Set it via the GMAIL_APP_PASSWORD environment variable, or enter it when
    prompted.
"""

import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("Missing dependency: pip install openpyxl")
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────────

SENDER        = "danielzhou123@gmail.com"
RECIPIENT     = ["danielzhou123@gmail.com", "daisy.rukawa@gmail.com"]
APP_PASSWORD  = "mqzd zhlh yonj ebyw"  # fill in your Gmail App Password here

# ── Read summaries from xlsx ──────────────────────────────────────────────────

def read_summaries(xlsx_path: Path):
    """
    Returns a list of dicts, one per complete sheet (sheets with '(incomplete)'
    in the title are skipped), each containing:
        { "heading": "January 2026",
          "headers": ["MV 1321", "PM 2505", "PM 1105", "Total"],
          "rows": [
              ("AIRBNB GROSS (for Tax)", [v1, v2, v3, total]),
              ("Airbnb Fee",             [v1, v2, v3, total]),
              ("Airbnb Net Income",      [v1, v2, v3, total]),
          ]
        }
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    summaries = []

    for ws in wb.worksheets:
        if "(incomplete)" in ws.title.lower():
            continue

        # Row 1: blank | prop1 | prop2 | prop3 | Total
        header_row = [ws.cell(row=1, column=c).value for c in range(2, 6)]
        headers = [h for h in header_row if h]  # drop trailing None

        # Rows 2-4: label | values...
        rows = []
        for r in (2, 3, 4):
            label = ws.cell(row=r, column=1).value
            if not label:
                continue
            values = [ws.cell(row=r, column=c).value or 0.0 for c in range(2, 6)]
            rows.append((label, values))

        if not rows:
            continue

        summaries.append({
            "heading": ws.title,
            "headers": headers,
            "rows":    rows,
        })

    return summaries

# ── HTML generation ───────────────────────────────────────────────────────────

def fmt_money(v):
    if v is None:
        v = 0.0
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.2f}"

CSS = """
<style>
  body  { font-family: Calibri, Arial, sans-serif; font-size: 13px; color: #222; }
  h2    { margin-top: 28px; margin-bottom: 6px; }
  table { border-collapse: collapse; margin-bottom: 8px; }
  th, td { border: 1px solid #bbb; padding: 5px 12px; text-align: right; }
  th     { background: #2e4057; color: #fff; text-align: center; }
  th.lbl { text-align: left; }
  td.lbl { text-align: left; }
  tr.gross { background: #ffff00; font-weight: bold; }
  tr.net   { background: #e2efda; font-weight: bold; }
  td.note  { border: none; font-style: italic; color: #595959;
             text-align: left; padding-left: 10px; }
</style>
"""

ROW_STYLES = {
    "airbnb gross": "gross",
    "airbnb net income": "net",
}

def build_html(summaries):
    sections = []
    for s in summaries:
        heading = s["heading"]
        header_cells = "".join(f"<th>{h}</th>" for h in s["headers"])
        header = (f"<tr><th class='lbl'>Month: {heading}</th>"
                  f"{header_cells}</tr>")

        data_rows = ""
        for label, values in s["rows"]:
            key = label.lower().strip()
            cls = ROW_STYLES.get(key, "")
            cells = "".join(f"<td>{fmt_money(v)}</td>" for v in values)
            note = (" <td class='note'>use this to file taxes</td>"
                    if "net income" in key else "<td class='note'></td>")
            data_rows += (f"<tr class='{cls}'>"
                          f"<td class='lbl'>{label}</td>{cells}{note}</tr>")

        sections.append(
            f"<h2>{heading}</h2>"
            f"<table>{header}{data_rows}</table>"
        )

    return f"<html><head>{CSS}</head><body>{''.join(sections)}</body></html>"

# ── Email sending ─────────────────────────────────────────────────────────────

def send_email(subject, html_body, attachment_path, app_password):
    msg = MIMEMultipart("mixed")
    msg["From"]    = SENDER
    msg["To"]      = ", ".join(RECIPIENT)
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    with open(attachment_path, "rb") as f:
        part = MIMEBase("application",
                        "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition",
                    f'attachment; filename="{attachment_path.name}"')
    msg.attach(part)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(SENDER, app_password)
        server.sendmail(SENDER, RECIPIENT, msg.as_string())  # list is fine for sendmail

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python airbnb_email.py <path/to/airbnb_taxes_*.xlsx>")

    xlsx_path = Path(sys.argv[1])
    if not xlsx_path.exists():
        sys.exit(f"File not found: {xlsx_path}")

    summaries = read_summaries(xlsx_path)
    if not summaries:
        sys.exit("No complete month sheets found in the xlsx — nothing to email.")

    latest = summaries[-1:]  # only the most recent complete month
    last   = latest[0]["heading"]  # e.g. "Mar 2026"
    subject = f"Airbnb Taxes Report {last}"

    html_body = build_html(latest)

    if not APP_PASSWORD:
        sys.exit("Set APP_PASSWORD in the script before running.")
    app_password = APP_PASSWORD

    print(f"Sending '{subject}' to {', '.join(RECIPIENT)} ...")
    send_email(subject, html_body, xlsx_path, app_password)
    print("Sent.")


if __name__ == "__main__":
    main()
