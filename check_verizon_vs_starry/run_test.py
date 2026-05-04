"""
run_test.py — continuously run speed tests and log results to a CSV + log file.

Usage:
    python run_test.py verizon          # run every 10 minutes (default)
    python run_test.py starry           # same for Starry
    python run_test.py verizon --interval 5   # every 5 minutes instead

Results are saved to: results_<provider>.csv
Logs are saved to:    log_<provider>.txt
Run this for a full day on each provider, then use compare.py to compare.
"""

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import speedtest

HERE = Path(__file__).parent


def log(log_file, msg):
    """Print to console and append to log file."""
    print(msg)
    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write(msg + "\n")


def run_single_test():
    st = speedtest.Speedtest(secure=True)
    st.get_best_server()
    st.download()
    st.upload()
    results = st.results.dict()
    return (
        round(results["download"] / 1e6, 2),
        round(results["upload"] / 1e6, 2),
        round(results["ping"], 1),
        results["server"]["name"] + ", " + results["server"]["country"],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", help="Name of the provider (e.g. verizon or starry)")
    parser.add_argument("--interval", type=int, default=10, help="Minutes between tests (default: 10)")
    parser.add_argument("--duration", type=int, default=24, help="Total hours to run (default: 24)")
    args = parser.parse_args()

    provider = args.provider.lower()
    interval_sec = args.interval * 60
    total_tests = (args.duration * 60) // args.interval

    csv_path = HERE / f"results_{provider}.csv"
    log_path = HERE / f"log_{provider}.txt"
    file_exists = csv_path.exists()

    header = "\n".join([
        f"Provider : {provider}",
        f"Interval : every {args.interval} minutes",
        f"Duration : {args.duration} hours (~{total_tests} tests)",
        f"CSV      : {csv_path}",
        f"Log      : {log_path}",
        "-" * 50,
    ])
    log(log_path, header)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "download_mbps", "upload_mbps", "ping_ms", "server", "status"])

        for i in range(1, total_tests + 1):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log(log_path, f"[{timestamp}] Test {i}/{total_tests} ...")
            try:
                dl, ul, ping, server = run_single_test()
                writer.writerow([timestamp, dl, ul, ping, server, "ok"])
                f.flush()
                log(log_path, f"  down: {dl} Mbps  up: {ul} Mbps  ping: {ping} ms  server: {server}")
            except Exception as e:
                err = str(e)
                writer.writerow([timestamp, "", "", "", "", f"error: {err}"])
                f.flush()
                log(log_path, f"  FAILED: {err}")

            if i < total_tests:
                time.sleep(interval_sec)

    log(log_path, "-" * 50)
    log(log_path, "Done. Run compare.py to see the results.")


if __name__ == "__main__":
    main()
