"""Discharge assumption A1: a predictable scale tracker that (i) brackets the true
local scale (A1), and (ii) has upward variation W_s comparable to the true scale's
V_sigma^+ (so the Theorem-2 regret degrades only with genuine nonstationarity).

Theory (THEORY_SNOGD.md §7): any A1 tracker has W_s >= c1 * V_sigma^+ (unavoidable).
We test empirically on the real Jane Street gradient-scale process whether a tracker
achieves A1 AND W_s = O(V_sigma^+), comparing:
  (A) single-timescale trailing robust median (lags at jumps),
  (B) two-timescale envelope: react UP fast, decay DOWN slowly (peak-hold w/ release).

Ground-truth local scale sigma_t := centered (non-causal) rolling median of ||g||.
All trackers are predictable (use ||g|| strictly before t).

Usage::  python scripts/research_tracker.py --date-lo 0 --date-hi 40
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dfsl import JaneStreetDataset
from dfsl.evaluation import best_fixed_linear

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "research"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "cm", "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "legend.fontsize": 6.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.6, "lines.linewidth": 1.0, "legend.frameon": False,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 300, "savefig.bbox": "tight",
})


def upward_variation(x):
    return float(x[0] + np.sum(np.maximum(np.diff(x), 0.0)))


def trailing_median(g, W):
    """Predictable trailing median of |g| over window W (uses indices < t)."""
    s = pl.Series(g).shift(1).rolling_median(window_size=W, min_samples=max(5, W // 10))
    out = s.to_numpy().astype(float)
    # fill the warm-up with the first finite value
    first = out[np.isfinite(out)][0] if np.isfinite(out).any() else 1.0
    out[~np.isfinite(out)] = first
    return np.maximum(out, 1e-8)


def two_timescale(g, Wf=64, rho=0.001, C=1.0):
    """React up fast (short trailing median), decay down slowly (rate rho).

        s_t = max( C * median(|g|_{t-Wf..t-1}),  (1-rho) * s_{t-1} ).
    Predictable; the max gives an upper envelope that never under-shoots a recent
    scale rise (helps A1 lower bracket), while the (1-rho) release keeps W_s small.
    """
    fast = trailing_median(g, Wf) * C
    s = np.empty_like(fast)
    s[0] = fast[0]
    for t in range(1, len(fast)):
        s[t] = max(fast[t], (1.0 - rho) * s[t - 1])
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-lo", type=int, default=0)
    ap.add_argument("--date-hi", type=int, default=40)
    ap.add_argument("--max-rows", type=int, default=400000)
    args = ap.parse_args()

    print(f"Loading date[{args.date_lo},{args.date_hi}) for gradient-scale tracking")
    ds = JaneStreetDataset(date_range=(args.date_lo, args.date_hi), max_rows=args.max_rows, standardize=True)
    X, y, w = ds.X, ds.y, ds.weights
    wstar = best_fixed_linear(X, y, w)
    g = np.linalg.norm(2.0 * w[:, None] * (X @ wstar - y)[:, None] * X, axis=1)
    n = g.size
    print(f"  n={n:,}  ||g|| median={np.median(g):.3f}")

    # Ground-truth local scale: centered (non-causal) rolling median, window Wc.
    Wc = 4001
    sigma = pl.Series(g).rolling_median(window_size=Wc, min_samples=Wc // 2, center=True).to_numpy().astype(float)
    m = np.median(g)
    sigma[~np.isfinite(sigma)] = m
    sigma = np.maximum(sigma, 1e-8)
    Vsig = upward_variation(sigma)

    trackers = {
        "trailing-median W=500 (1-timescale)": trailing_median(g, 500),
        "trailing-median W=64 (fast, noisy)": trailing_median(g, 64),
        "two-timescale envelope (ours)": two_timescale(g, Wf=64, rho=0.0008, C=1.0),
    }

    print(f"\n  ground-truth V_sigma^+ (upward variation of sigma_t) = {Vsig:,.1f}")
    print(f"  {'tracker':42s} {'A1@[.5,2]':>9s} {'lower>=.5':>9s} {'W_s':>10s} {'W_s/Vsig':>9s}")
    rows = []
    for name, s in trackers.items():
        ratio = s / sigma
        a1 = float(np.mean((ratio >= 0.5) & (ratio <= 2.0)))
        lower = float(np.mean(ratio >= 0.5))
        Ws = upward_variation(s)
        rows.append({"tracker": name, "A1_bracket": a1, "lower_ok": lower,
                     "W_s": Ws, "W_s_over_Vsig": Ws / Vsig})
        print(f"  {name:42s} {a1:9.3f} {lower:9.3f} {Ws:10,.1f} {Ws/Vsig:9.2f}")
    pl.DataFrame(rows).write_csv(OUT / "tracker_a1.csv")

    _figure(g, sigma, trackers)
    print(f"\nFindings written to {OUT.relative_to(ROOT)}")


def _figure(g, sigma, trackers):
    fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.5), gridspec_kw={"width_ratios": [2.2, 1]})
    # zoom into a segment that contains a jump for legibility
    lo, hi = 60000, 120000
    xs = np.arange(lo, hi)
    ax = axes[0]
    ax.plot(xs, g[lo:hi], color="#dddddd", lw=0.3, zorder=1, label=r"$\|g_t\|$")
    ax.plot(xs, sigma[lo:hi], color="k", lw=1.2, zorder=4, label=r"true $\sigma_t$ (centered)")
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    for (name, s), c in zip(trackers.items(), colors):
        ax.plot(xs, s[lo:hi], color=c, lw=0.9, zorder=3, label=name.split(" (")[0])
    ax.set_yscale("log")
    ax.set_xlabel("step $t$")
    ax.set_ylabel("scale")
    ax.set_title("(a) Predictable trackers vs. true local scale")
    ax.legend(loc="upper right", fontsize=5.5)

    ax = axes[1]
    names = [n.split(" (")[0] for n in trackers]
    lower = [float(np.mean((s / sigma) >= 0.5)) for s in trackers.values()]
    ax.barh(range(len(names)), lower, color=colors)
    for i, v in enumerate(lower):
        ax.text(min(v, 0.98), i, f" {v:.2f}", va="center", ha="right" if v > 0.2 else "left", fontsize=6, color="white" if v > 0.2 else "black")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=5.5)
    ax.set_xlim(0, 1)
    ax.set_xlabel(r"lower-bracket $s_t\geq\frac{1}{2}\sigma_t$")
    ax.set_title("(b) Stability-critical bracket")
    fig.savefig(OUT / "fig_tracker.png")
    plt.close(fig)
    print("  wrote results/research/fig_tracker.png")


if __name__ == "__main__":
    main()
