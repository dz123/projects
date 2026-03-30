"""
Generate per-listing summary and property-level aggregate.
avg_nightly = ((total_price - cleaning_fee) / nights) * 0.75
"""
import csv
import statistics
from datetime import date, datetime

AVAIL_CSV   = "output/available_stays_20260329_final.csv"
BOOKED_CSV  = "output/booked_nights_20260329.csv"
REVIEWS_CSV = "output/reviews_20260329.csv"
OUT_SUMMARY = "output/summary_20260329_v2.csv"

CLEANING_FEES = {"kamaole_sands": 170, "maui_vista": 150}
CUTOFF = date(2026, 6, 30)
RATE   = 0.75


def main():
    # ── Load reviews ──────────────────────────────────────────────────────────
    reviews = {}
    with open(REVIEWS_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            link = r["link"]
            if link not in reviews:
                nr = int(r["num_reviews"]) if r["num_reviews"].strip() else None
                sc = float(r["avg_review_score"]) if r["avg_review_score"].strip() else None
                reviews[link] = (nr, sc)

    # ── Load booked nights (up to cutoff) ─────────────────────────────────────
    booked_counts = {}
    last_avail = {}
    with open(BOOKED_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            link = r["link"]
            d = date.fromisoformat(r["date_booked"])
            if d > CUTOFF:
                continue
            if r["status"] == "booked":
                booked_counts[link] = booked_counts.get(link, 0) + 1

    # ── Load available stays ──────────────────────────────────────────────────
    prop_map  = {}
    avail_counts = {}
    nightly_prices = {}

    with open(AVAIL_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            link  = r["link"]
            prop  = r["property_name"]
            prop_map[link] = prop

            start = date.fromisoformat(r["start_date"])
            end   = date.fromisoformat(r["end_date"])
            if start > CUTOFF:
                continue

            avail_counts[link] = avail_counts.get(link, 0) + (end - start).days

            price_str = r["total_price"].strip()
            if not price_str:
                continue
            total = float(price_str)
            nights = (end - start).days
            fee = CLEANING_FEES.get(prop, 0)
            nightly = ((total - fee) / nights) * RATE
            nightly_prices.setdefault(link, []).append(nightly)

    # ── Track last available date from available stays ────────────────────────
    last_avail_map = {}
    with open(AVAIL_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            link = r["link"]
            end  = date.fromisoformat(r["end_date"])
            end_cap = min(end, CUTOFF)
            if link not in last_avail_map or end_cap > last_avail_map[link]:
                last_avail_map[link] = end_cap

    # ── Build per-listing summary ─────────────────────────────────────────────
    all_links = sorted(set(list(prop_map.keys()) + list(reviews.keys())))

    rows = []
    for link in all_links:
        prop   = prop_map.get(link, "unknown")
        avail  = avail_counts.get(link, 0)
        booked = booked_counts.get(link, 0)
        total_days = avail + booked
        pct_booked = f"{round(booked / total_days * 100)}%" if total_days else "0%"
        last_av = last_avail_map.get(link, "")
        nr, sc = reviews.get(link, (None, None))
        prices = nightly_prices.get(link, [])
        avg_n = round(statistics.mean(prices)) if prices else ""
        rows.append([link, prop, avg_n, avail, booked, last_av, pct_booked, nr or "", sc or ""])

    with open(OUT_SUMMARY, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["link", "property", "avg_nightly", "avail", "booked", "last_avail", "pct_booked", "num_reviews", "avg_score"])
        w.writerows(rows)

    print(f"Saved {OUT_SUMMARY}\n")

    # ── Print per-listing table ───────────────────────────────────────────────
    hdr = f"{'link':<55} {'property':<15} {'avg_nightly':>11} {'avail':>5} {'booked':>6} {'last_avail':>12} {'pct_booked':>10} {'reviews':>7} {'score':>6}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        link, prop, avg_n, avail, booked, last_av, pct_b, nr, sc = r
        print(f"{link:<55} {prop:<15} {str(avg_n):>11} {avail:>5} {booked:>6} {str(last_av):>12} {pct_b:>10} {str(nr):>7} {str(sc):>6}")

    # ── Property aggregate ────────────────────────────────────────────────────
    print("\n\n=== GROUP BY PROPERTY ===\n")
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        link, prop, avg_n, avail, booked, last_av, pct_b, nr, sc = r
        total_days = avail + booked
        pct_num = booked / total_days * 100 if total_days else 0
        groups[prop].append({
            "avg_n": avg_n,
            "pct": pct_num,
            "score": sc,
        })

    agg_rows = []
    for prop in sorted(groups.keys()):
        items = groups[prop]
        count = len(items)
        nightlies = [x["avg_n"] for x in items if x["avg_n"] != ""]
        pcts      = [x["pct"] for x in items]
        scores    = [float(x["score"]) for x in items if x["score"] != ""]
        avg_n  = round(statistics.mean(nightlies)) if nightlies else ""
        med_n  = round(statistics.median(nightlies)) if nightlies else ""
        avg_p  = f"{round(statistics.mean(pcts))}%"
        med_p  = f"{round(statistics.median(pcts))}%"
        avg_s  = round(statistics.mean(scores), 2) if scores else ""
        med_s  = round(statistics.median(scores), 2) if scores else ""
        agg_rows.append([prop, count, avg_n, med_n, avg_p, med_p, avg_s, med_s])

    print(f"{'property':<15} {'count':>5} {'avg_nightly':>11} {'med_nightly':>11} {'avg_%booked':>11} {'med_%booked':>11} {'avg_score':>9} {'med_score':>9}")
    print("-" * 90)
    for r in agg_rows:
        print(f"{r[0]:<15} {r[1]:>5} {str(r[2]):>11} {str(r[3]):>11} {str(r[4]):>11} {str(r[5]):>11} {str(r[6]):>9} {str(r[7]):>9}")


if __name__ == "__main__":
    main()
