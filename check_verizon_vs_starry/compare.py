"""
compare.py — compare speed test results between two providers.

Usage:
    python compare.py                          # compares results_verizon.csv vs results_starry.csv
    python compare.py --a results_verizon.csv --b results_starry.csv
"""

import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

HERE = Path(__file__).parent


def load(path):
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df[df["status"] == "ok"].copy()
    df = df.dropna(subset=["download_mbps", "upload_mbps", "ping_ms"])
    return df


def print_stats(label, df):
    print(f"\n{'='*40}")
    print(f"  {label}  ({len(df)} successful tests)")
    print(f"{'='*40}")
    for col, name in [("download_mbps", "Download (Mbps)"), ("upload_mbps", "Upload (Mbps)"), ("ping_ms", "Ping (ms)")]:
        s = df[col]
        print(f"  {name:20s}  avg={s.mean():.1f}  median={s.median():.1f}  min={s.min():.1f}  max={s.max():.1f}  stddev={s.std():.1f}")

    # Outage = failed tests (status != ok)
    total = len(pd.read_csv(path_map[label], parse_dates=["timestamp"]))
    failed = total - len(df)
    print(f"  {'Failed tests':20s}  {failed}/{total}  ({100*failed/total:.1f}% outage rate)")


def plot(df_a, label_a, df_b, label_b):
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=False)
    fig.suptitle("Internet Provider Comparison", fontsize=14, fontweight="bold")

    metrics = [
        ("download_mbps", "Download Speed (Mbps)", "tab:blue"),
        ("upload_mbps",   "Upload Speed (Mbps)",   "tab:green"),
        ("ping_ms",       "Ping (ms)",              "tab:orange"),
    ]

    for ax, (col, ylabel, _) in zip(axes, metrics):
        ax.plot(df_a["timestamp"], df_a[col], label=label_a, color="tab:blue", alpha=0.8, linewidth=1)
        ax.plot(df_b["timestamp"], df_b[col], label=label_b, color="tab:red",  alpha=0.8, linewidth=1)
        ax.axhline(df_a[col].mean(), color="tab:blue", linestyle="--", linewidth=0.8, alpha=0.5)
        ax.axhline(df_b[col].mean(), color="tab:red",  linestyle="--", linewidth=0.8, alpha=0.5)
        ax.set_ylabel(ylabel)
        ax.legend(loc="upper right")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time")
    plt.tight_layout()
    out = HERE / "comparison.png"
    plt.savefig(out, dpi=150)
    print(f"\nChart saved to: {out}")
    plt.show()


path_map = {}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", default="results_verizon.csv")
    parser.add_argument("--b", default="results_starry.csv")
    args = parser.parse_args()

    path_a = HERE / args.a
    path_b = HERE / args.b

    for p in [path_a, path_b]:
        if not os.path.exists(p):
            print(f"File not found: {p}")
            return

    label_a = args.a.replace("results_", "").replace(".csv", "").capitalize()
    label_b = args.b.replace("results_", "").replace(".csv", "").capitalize()

    path_map[label_a] = path_a
    path_map[label_b] = path_b

    df_a = load(path_a)
    df_b = load(path_b)

    print_stats(label_a, df_a)
    print_stats(label_b, df_b)

    print("\n--- Winner by category ---")
    for col, name in [("download_mbps", "Download"), ("upload_mbps", "Upload"), ("ping_ms", "Ping (lower=better)")]:
        a_avg, b_avg = df_a[col].mean(), df_b[col].mean()
        if col == "ping_ms":
            winner = label_a if a_avg < b_avg else label_b
        else:
            winner = label_a if a_avg > b_avg else label_b
        print(f"  {name:20s}  {winner}  ({label_a}={a_avg:.1f}  {label_b}={b_avg:.1f})")

    plot(df_a, label_a, df_b, label_b)


if __name__ == "__main__":
    main()
