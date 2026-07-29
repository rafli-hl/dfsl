"""Characterize the nonstationarity of the heavy-tailed gradient scale.

This turns the open problem (PROBLEM.md section 5 -- distribution-free, high-prob,
*dynamic* online learning under a *drifting* heavy tail) into measurements. On a
long contiguous Jane Street span that contains a turbulent regime, we ask, all at
a fixed learner-independent predictor w*:

  1. How fast does the gradient *scale* (median / p99 of ||g_t||) drift day to day?
  2. Does the *tail index* (Hill alpha of ||g_t||) drift too, or only the scale?
  3. What is an adaptive clipping threshold up against? For a causal trailing
     threshold tau_t = c * rolling_median(||g||, W), we measure its *dynamic
     range* p95(tau)/p5(tau) -- the factor by which a fixed learning rate becomes
     mis-scaled across regimes (the divergence mechanism of FINDINGS Finding 7) --
     and how the trade-off changes with the window W (fast reaction vs low
     variance).

Outputs CSVs + PNG figures under results/research/.

Usage::  python scripts/research_nonstationarity.py --date-lo 0 --date-hi 60
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
OUT.mkdir(parents=True, exist_ok=True)

WINDOWS = [250, 1000, 4000, 16000]  # trailing threshold windows (steps)
CLIP_MULT = 3.0

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "cm",
        "font.size": 8,
        "axes.titlesize": 8,
        "axes.labelsize": 8,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "axes.linewidth": 0.6,
        "lines.linewidth": 1.1,
        "legend.frameon": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    }
)


def hill_alpha(a: np.ndarray, k: int) -> float:
    a = np.sort(np.abs(a[np.isfinite(a)]))[::-1]
    k = min(k, a.size - 2)
    if k <= 0 or a[k] <= 0:
        return float("nan")
    return 1.0 / float(np.mean(np.log(a[:k]) - np.log(a[k])))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-lo", type=int, default=0)
    ap.add_argument("--date-hi", type=int, default=60)
    ap.add_argument("--max-rows", type=int, default=600000)
    args = ap.parse_args()

    print(f"Loading contiguous span date[{args.date_lo},{args.date_hi}) (standardized)")
    ds = JaneStreetDataset(
        date_range=(args.date_lo, args.date_hi), max_rows=args.max_rows, standardize=True
    )
    X, y, w = ds.X, ds.y, ds.weights
    date_id = ds.meta["date_id"].to_numpy().astype(np.int64)
    print(f"  n={len(y):,}  days={date_id.min()}..{date_id.max()}")

    # Learner-independent gradient norms at the fixed optimum.
    wstar = best_fixed_linear(X, y, w)
    resid = X @ wstar - y
    gnorm = np.linalg.norm(2.0 * w[:, None] * resid[:, None] * X, axis=1)
    print(f"  ||g|| median={np.median(gnorm):.3f}  p99={np.percentile(gnorm,99):.3f}  max={gnorm.max():.3f}")

    # --- (1,2) daily scale & tail drift -------------------------------------
    df = pl.DataFrame({"date_id": date_id, "gnorm": gnorm})
    daily = (
        df.group_by("date_id")
        .agg(
            pl.len().alias("n"),
            pl.col("gnorm").median().alias("median_gnorm"),
            pl.col("gnorm").quantile(0.99).alias("p99_gnorm"),
            pl.col("gnorm").max().alias("max_gnorm"),
        )
        .sort("date_id")
    )
    # Hill alpha per day (needs per-day arrays).
    alphas = []
    for d in daily["date_id"].to_list():
        g = gnorm[date_id == d]
        alphas.append(hill_alpha(g, k=min(500, g.size // 4)))
    daily = daily.with_columns(pl.Series("hill_alpha", alphas))
    daily.write_csv(OUT / "nonstationarity_daily.csv")

    med = daily["median_gnorm"].to_numpy()
    scale_drift = float(med.max() / med.min())
    logjump = np.abs(np.diff(np.log(med)))
    print(f"\n  daily median ||g||: min={med.min():.3f} max={med.max():.3f} "
          f"drift(max/min)={scale_drift:.2f}x")
    print(f"  day-over-day |Δlog median|: mean={logjump.mean():.3f} max={logjump.max():.3f} "
          f"(={np.exp(logjump.max()):.2f}x jump)")
    a = np.array(alphas, dtype=float)
    print(f"  daily Hill alpha: min={np.nanmin(a):.2f} max={np.nanmax(a):.2f} "
          f"(tail index {'drifts' if np.nanmax(a)-np.nanmin(a)>0.5 else 'stable'})")

    # --- (3) what an adaptive threshold is up against -----------------------
    print("\n  causal trailing threshold tau_t = 3 * rolling_median(||g||, W):")
    gser = pl.Series("g", gnorm)
    tension_rows = []
    tau_traces = {}
    for W in WINDOWS:
        tau = (CLIP_MULT * gser.rolling_median(window_size=W, min_samples=max(10, W // 20))).to_numpy()
        valid = np.isfinite(tau) & (tau > 0)
        tau_v = tau[valid]
        g_v = gnorm[valid]
        dyn_range = float(np.percentile(tau_v, 95) / np.percentile(tau_v, 5))
        clip_rate = float(np.mean(g_v > tau_v))
        shock = g_v / tau_v
        tension_rows.append(
            {
                "window": W,
                "tau_dynamic_range_p95_p5": dyn_range,
                "clip_rate": clip_rate,
                "shock_p99_9": float(np.percentile(shock, 99.9)),
                "tau_min": float(tau_v.min()),
                "tau_max": float(tau_v.max()),
            }
        )
        tau_traces[W] = tau
        print(
            f"    W={W:6d}  tau dynamic range={dyn_range:6.2f}x  clip_rate={clip_rate:.4f}  "
            f"shock_p99.9={np.percentile(shock,99.9):.2f}"
        )
    tension = pl.DataFrame(tension_rows)
    tension.write_csv(OUT / "nonstationarity_threshold_tension.csv")

    _figures(daily, gnorm, date_id, tau_traces, tension)
    print(f"\nFindings written to {OUT.relative_to(ROOT)}")


def _figures(daily, gnorm, date_id, tau_traces, tension) -> None:
    d = daily["date_id"].to_numpy()
    med = daily["median_gnorm"].to_numpy()
    p99 = daily["p99_gnorm"].to_numpy()
    alpha = daily["hill_alpha"].to_numpy()

    # Figure 1 -- scale & tail drift over days
    fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.4))
    ax = axes[0]
    ax.plot(d, med, color="#1f77b4", marker="o", ms=2.5, label="median")
    ax.plot(d, p99, color="#d62728", marker="^", ms=2.5, label="p99")
    ax.axvspan(30, 50, color="orange", alpha=0.12)
    ax.text(40, ax.get_ylim()[1], "turbulent", ha="center", va="top", fontsize=6, color="darkorange")
    ax.set_yscale("log")
    ax.set_xlabel("date_id")
    ax.set_ylabel(r"daily $\|g\|$ scale")
    ax.set_title("(a) Gradient scale drifts across days")
    ax.legend(loc="upper right")

    ax = axes[1]
    ax.plot(d, alpha, color="#2ca02c", marker="s", ms=2.5)
    ax.axhline(2, color="k", ls="--", lw=0.8)
    ax.axhline(4, color="k", ls=":", lw=0.8)
    ax.axvspan(30, 50, color="orange", alpha=0.12)
    ax.set_xlabel("date_id")
    ax.set_ylabel(r"daily Hill $\hat\alpha$")
    ax.set_title(r"(b) Tail index drifts below $\alpha{=}2$")
    fig.savefig(OUT / "fig_scale_drift.png")
    plt.close(fig)
    print("  wrote results/research/fig_scale_drift.png")

    # Figure 2 -- what the adaptive threshold is up against
    fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.4))
    ax = axes[0]
    step = max(1, gnorm.size // 4000)
    xs = np.arange(gnorm.size)[::step]
    ax.plot(xs, gnorm[::step], color="#cccccc", lw=0.4, label=r"$\|g_t\|$", zorder=1)
    for W, color in [(WINDOWS[0], "#1f77b4"), (WINDOWS[-1], "#d62728")]:
        ax.plot(xs, tau_traces[W][::step], color=color, lw=1.0, label=f"$\\tau_t$, W={W}", zorder=3)
    ax.set_yscale("log")
    ax.set_xlabel("step $t$")
    ax.set_ylabel(r"$\|g_t\|$ and threshold $\tau_t$")
    ax.set_title("(a) Fast vs. slow threshold tracking")
    ax.legend(loc="upper right", fontsize=6)

    ax = axes[1]
    Ws = tension["window"].to_numpy()
    dyn = tension["tau_dynamic_range_p95_p5"].to_numpy()
    clip = tension["clip_rate"].to_numpy()
    ax.plot(Ws, dyn, color="#9467bd", marker="o", label="threshold dynamic range")
    ax.set_xscale("log")
    ax.set_xlabel("threshold window $W$")
    ax.set_ylabel(r"$\tau$ dynamic range (p95/p5)")
    ax.set_title("(b) Reaction speed vs. stability")
    ax2 = ax.twinx()
    ax2.plot(Ws, clip, color="#ff7f0e", marker="s", ls="--", label="clip rate")
    ax2.set_ylabel("clip rate", color="#ff7f0e")
    ax2.tick_params(axis="y", labelcolor="#ff7f0e")
    ax2.spines["top"].set_visible(False)
    fig.savefig(OUT / "fig_threshold_tension.png")
    plt.close(fig)
    print("  wrote results/research/fig_threshold_tension.png")


if __name__ == "__main__":
    main()
