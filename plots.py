"""Draw the three required graphs (project section 7.2) from experiment CSV files.

Usage:
    python plots.py                    # reads results/*.csv, writes results/figures/*.png
    python plots.py --in results --out results/figures

Needs matplotlib (pip install matplotlib). Only reads CSV files; it never runs
the hotel code, so experiments and plotting stay separate.

Expected CSV files (one row per run; each setting is run with salt 0, 1, 2):

  exp_A.csv  K,N,V,salt,build_ring_ms,assign_guests_ms,search_us,sort_ms,
             mem_current_mib,mem_peak_mib
  exp_B.csv  N,V,K,salt,method,action,moved,move_rate,time_ms
             method = consistent | mod_n      action = add | remove
  exp_C.csv  V,N,K,salt,cv,max,min,ring_mem_kib,mem_current_mib,mem_peak_mib
             ring_mem_kib = memory of the ring alone (init with no guests)

Every graph shows the median of the 3 salts as the line and the min-max range
of the 3 salts as error bars.
"""
import argparse
import csv
import os
import statistics
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")  # write files only, no window
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Validated categorical colors (fixed order) + neutral ink for text and axes.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
INK = "#3d3d3a"
MUTED = "#73726c"
GRID = "#e4e2dc"


# --------------------------------------------------------------- #
# Reading and summarising
# --------------------------------------------------------------- #
def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarise(rows, x_key, y_key, keep=lambda r: True):
    """Group rows by x and return xs, medians, lower errors, upper errors."""
    groups = defaultdict(list)
    for r in rows:
        if keep(r) and r[y_key] not in ("", "None"):
            groups[float(r[x_key])].append(float(r[y_key]))
    xs = sorted(groups)
    med = [statistics.median(groups[x]) for x in xs]
    lo = [m - min(groups[x]) for x, m in zip(xs, med)]
    hi = [max(groups[x]) - m for x, m in zip(xs, med)]
    runs = sorted({len(v) for v in groups.values()})
    return xs, med, (lo, hi), runs


def first(rows, key):
    return rows[0][key] if rows else "?"


# --------------------------------------------------------------- #
# Shared styling
# --------------------------------------------------------------- #
def style_axes(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=11, color=INK, loc="left")
    ax.set_xlabel(xlabel, fontsize=10, color=MUTED)
    ax.set_ylabel(ylabel, fontsize=10, color=MUTED)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)


def line(ax, xs, ys, err, color, label=None, dashed=False):
    ax.errorbar(xs, ys, yerr=err, color=color, linewidth=2,
                linestyle="--" if dashed else "-",
                marker="o", markersize=7, markeredgecolor="white",
                markeredgewidth=2, capsize=4, elinewidth=1.2, label=label)


def legend(ax, items):
    """items: (label, color, linestyle, marker) - drawn explicitly so each
    symbol matches its line exactly."""
    handles = [Line2D([0], [0], color=c, linestyle=ls, linewidth=2,
                      marker=m, markersize=7 if m else 0,
                      markeredgecolor="white", markeredgewidth=1.5, label=lab)
               for lab, c, ls, m in items]
    ax.legend(handles=handles, frameon=False, fontsize=9, labelcolor=INK)


def footer(fig, text):
    fig.text(0.01, 0.01, text, fontsize=8.5, color=MUTED, ha="left", va="bottom")


def save(fig, out_dir, name):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved {path}")


# --------------------------------------------------------------- #
# Graph (a): time vs K
# --------------------------------------------------------------- #
def plot_time_vs_k(rows, out_dir):
    panels = [
        ("assign_guests_ms", "Assign all guests", "time (ms)"),
        ("search_us", "Search by guest (per search)", "time (µs)"),
        ("sort_ms", "Sort room list", "time (ms)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    runs = set()
    for ax, (key, title, unit) in zip(axes, panels):
        xs, med, err, r = summarise(rows, "K", key)
        runs.update(r)
        line(ax, xs, med, err, BLUE)
        ax.set_xscale("log")
        ax.set_xticks(xs, [f"{int(x):,}" for x in xs])
        ax.minorticks_off()
        style_axes(ax, title, "number of guests K (log scale)", unit)
    fig.suptitle("(a) Time vs number of guests — consistent hashing",
                 x=0.01, ha="left", fontsize=13, color=INK)
    footer(fig, f"N = {first(rows, 'N')}, V = {first(rows, 'V')}. "
                f"Line = median of {max(runs)} runs (salts); bars = min–max. "
                "Search measured as a batch of 1,000 then divided.")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    save(fig, out_dir, "graph_a_time_vs_K.png")


# --------------------------------------------------------------- #
# Graph (b): move rate vs N, both methods
# --------------------------------------------------------------- #
def plot_move_rate_vs_n(rows, out_dir):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    runs = set()
    for ax, action, title in zip(axes, ("add", "remove"),
                                 ("Add 1 building (N → N+1)",
                                  "Remove 1 building (N → N−1)")):
        for method, color, label in (("consistent", BLUE, "Consistent hashing"),
                                     ("mod_n", ORANGE, "hash mod N")):
            xs, med, err, r = summarise(
                rows, "N", "move_rate",
                keep=lambda row, m=method, a=action:
                    row["method"] == m and row["action"] == a)
            runs.update(r)
            pct = [m * 100 for m in med]
            pct_err = ([e * 100 for e in err[0]], [e * 100 for e in err[1]])
            line(ax, xs, pct, pct_err, color, label)
        expected = [100 / (n + 1) if action == "add" else 100 / n for n in xs]
        exp_label = "expected (CH): 1/(N+1)" if action == "add" else "expected (CH): 1/N"
        ax.plot(xs, expected, color=MUTED, linewidth=1.5, linestyle=":", zorder=5)
        ax.set_xticks(xs, [str(int(x)) for x in xs])
        ax.set_ylim(0, 105)
        style_axes(ax, title, "buildings before the change N", "guests moved (% of K)")
        legend(ax, [("hash mod N", ORANGE, "-", "o"),
                    ("Consistent hashing", BLUE, "-", "o"),
                    (exp_label, MUTED, ":", None)])
    fig.suptitle("(b) Move rate vs number of buildings",
                 x=0.01, ha="left", fontsize=13, color=INK)
    footer(fig, f"K = {int(float(first(rows, 'K'))):,}, V = {first(rows, 'V')}. "
                f"Same guests, building IDs and hashes for both methods. "
                f"Line = median of {max(runs)} salts; bars = min–max.")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    save(fig, out_dir, "graph_b_move_rate_vs_N.png")


# --------------------------------------------------------------- #
# Graph (c): effect of V on CV and memory (two panels, never two y-axes)
# --------------------------------------------------------------- #
def plot_v_effect(rows, out_dir):
    has_ring = "ring_mem_kib" in rows[0]
    fig, axes = plt.subplots(1, 3 if has_ring else 2,
                             figsize=(16 if has_ring else 12, 4.2))
    ax1, ax_mem = axes[0], axes[-1]

    xs, med, err, runs = summarise(rows, "V", "cv")
    line(ax1, xs, med, err, BLUE)
    ax1.set_ylim(bottom=0)
    style_axes(ax1, "Load balance", "virtual nodes per building V",
               "CV = SD / mean (lower = more balanced)")

    if has_ring:
        ax2 = axes[1]
        xs2, med2, err2, _ = summarise(rows, "V", "ring_mem_kib")
        line(ax2, xs2, med2, err2, BLUE)
        ax2.set_ylim(bottom=0)
        style_axes(ax2, "Ring only (no guests)", "virtual nodes per building V",
                   "memory (KiB)")

    # current first, peak dashed on top, so both stay visible when they overlap
    for key, color, dashed in (("mem_current_mib", AQUA, False),
                               ("mem_peak_mib", ORANGE, True)):
        xs3, med3, err3, _ = summarise(rows, "V", key)
        line(ax_mem, xs3, med3, err3, color, dashed=dashed)
    ax_mem.set_ylim(bottom=0)
    style_axes(ax_mem, "Whole system (ring + guests)",
               "virtual nodes per building V", "memory (MiB)")
    legend(ax_mem, [("current", AQUA, "-", "o"), ("peak", ORANGE, "--", "o")])

    for ax in axes:
        ax.set_xticks(xs, [str(int(x)) for x in xs])
    fig.suptitle("(c) Effect of virtual nodes on balance and memory",
                 x=0.01, ha="left", fontsize=13, color=INK)
    footer(fig, f"N = {first(rows, 'N')}, K = {int(float(first(rows, 'K'))):,}. "
                "Memory = tracemalloc (memory traced by Python, not the whole process), "
                "measured in separate runs from timing. "
                f"Line = median of {max(runs)} salts; bars = min–max.")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    save(fig, out_dir, "graph_c_V_effect.png")


# --------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Plot experiment results.")
    parser.add_argument("--in", dest="in_dir", default="results")
    parser.add_argument("--out", dest="out_dir", default=os.path.join("results", "figures"))
    args = parser.parse_args()

    jobs = [("exp_A.csv", plot_time_vs_k),
            ("exp_B.csv", plot_move_rate_vs_n),
            ("exp_C.csv", plot_v_effect)]
    for name, plot in jobs:
        path = os.path.join(args.in_dir, name)
        if not os.path.exists(path):
            print(f"skip {name}: file not found ({path})")
            continue
        rows = read_rows(path)
        if not rows:
            print(f"skip {name}: no rows")
            continue
        plot(rows, args.out_dir)


if __name__ == "__main__":
    main()