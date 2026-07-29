"""Firm up the 'sqrt(T) is unreachable' wall across the FULL 1,699-day record.

THEORY.md section 3 predicts that if infinite-variance (tail index < 2) spells are
frequent enough, the *dynamic* regret lower bound

    R_T^dyn  >=  Sum_r  sigma_r * L_r^{1/p_r}      (comparator may change per regime)

exceeds the light-tailed sqrt(T), making a near-sqrt(T) rate unreachable. The 60-day
probe found 20% infinite-variance days and a heavy budget ~6.8x sqrt(T). This script
checks whether that holds across the whole record by strided day sampling.

For each sampled day we use the learner-independent gradient-at-w=0 proxy
g0 = 2*omega*|y|*||x|| (validated in RQ2: Hill alpha 2.40 vs 2.43 at w*), which needs
no fixed predictor. The Hill index is scale-invariant, so per-day standardization is
fine. We report the daily-alpha distribution across the record, and both the dynamic
(sum) and static (max) heavy-budget lower bounds vs sqrt(T_full).

Usage::  python scripts/research_heavybudget.py --stride 13 --max-rows-per-day 40000
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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "research"
N_DATES = 1699                 # date_id 0..1698
TOTAL_ROWS = 47_127_338        # full record (for sqrt(T_full))

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "cm",
        "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
        "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "axes.linewidth": 0.6, "lines.linewidth": 1.0, "legend.frameon": False,
        "axes.spines.top": False, "axes.spines.right": False,
        "savefig.dpi": 300, "savefig.bbox": "tight",
    }
)


def hill_alpha(a: np.ndarray, k: int) -> float:
    a = np.sort(a[np.isfinite(a) & (a > 0)])[::-1]
    k = min(k, a.size - 2)
    if k <= 0 or a[k] <= 0:
        return float("nan")
    return 1.0 / float(np.mean(np.log(a[:k]) - np.log(a[k])))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stride", type=int, default=13)
    ap.add_argument("--max-rows-per-day", type=int, default=40000)
    args = ap.parse_args()

    days = list(range(0, N_DATES, args.stride))
    print(f"Sampling {len(days)} days across the full record (stride={args.stride})")

    rows = []
    for i, d in enumerate(days):
        try:
            ds = JaneStreetDataset(date_range=(d, d + 1), max_rows=args.max_rows_per_day, standardize=True)
        except Exception as exc:
            print(f"  day {d}: skip ({exc})")
            continue
        n = len(ds.y)
        if n < 1000:
            continue
        xnorm = np.linalg.norm(ds.X, axis=1)
        g0 = 2.0 * ds.weights * np.abs(ds.y) * xnorm     # ||gradient at w=0||
        alpha = hill_alpha(g0, k=min(500, n // 10))
        rows.append({"date_id": d, "n": n, "median_g0": float(np.median(g0)), "hill_alpha": alpha})
        if i % 20 == 0:
            print(f"  day {d:4d}: n={n:6d}  alpha={alpha:.2f}")

    daily = pl.DataFrame(rows).sort("date_id")
    daily.write_csv(OUT / "heavybudget_daily.csv")

    a = daily["hill_alpha"].to_numpy()
    n = daily["n"].to_numpy().astype(float)
    finite = np.isfinite(a)
    a, n = a[finite], n[finite]
    frac_sub2 = float(np.mean(a < 2.0))
    sqrtT_full = np.sqrt(TOTAL_ROWS)

    # Heavy-budget lower bounds (scale-normalized: sigma_r := 1, isolating the tail).
    # Each sampled day represents ~stride days of the record -> scale the sum.
    heavy = a < 2.0
    per_day_budget = np.where(heavy, n ** (1.0 / np.maximum(a, 1e-6)), 0.0)
    dyn_budget_full = args.stride * float(per_day_budget.sum())     # SUM  -> dynamic regret
    static_budget = float(per_day_budget.max()) if heavy.any() else 0.0  # MAX -> static regret

    print("\n=== FULL-RECORD HEAVY-TAIL SUMMARY ===")
    print(f"  sampled days with finite alpha: {a.size}")
    print(f"  infinite-variance (alpha<2) days: {100*frac_sub2:.0f}%   "
          f"min alpha={a.min():.2f}  median alpha={np.median(a):.2f}")
    print(f"  worst-case exponent 1/alpha_min = {1/a.min():.3f}  (vs 0.5 for sqrt(T))")
    print(f"  sqrt(T_full) = {sqrtT_full:,.0f}")
    print(f"  DYNAMIC heavy budget (Sum L^(1/a) over heavy days, x stride) "
          f"= {dyn_budget_full:,.0f}  = {dyn_budget_full/sqrtT_full:.1f}x sqrt(T_full)")
    print(f"  STATIC heavy budget (max single day L^(1/a)) "
          f"= {static_budget:,.0f}  = {static_budget/sqrtT_full:.2f}x sqrt(T_full)")

    _figure(daily.filter(pl.col("hill_alpha").is_finite()))
    print(f"\nFindings written to {OUT.relative_to(ROOT)}")


def _figure(daily) -> None:
    d = daily["date_id"].to_numpy()
    a = daily["hill_alpha"].to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.4), gridspec_kw={"width_ratios": [2.3, 1]})
    ax = axes[0]
    ax.plot(d, a, color="#2ca02c", marker="o", ms=2.5, lw=0.8)
    ax.axhline(2, color="#d62728", ls="--", lw=0.9)
    ax.axhline(4, color="k", ls=":", lw=0.8)
    below = a < 2
    ax.scatter(d[below], a[below], color="#d62728", s=14, zorder=5, label=r"$\hat\alpha<2$ (inf. var.)")
    ax.set_xlabel("date_id (full 1,699-day record)")
    ax.set_ylabel(r"daily gradient Hill $\hat\alpha$")
    ax.set_title("(a) Tail index across the whole record")
    ax.legend(loc="upper right", fontsize=6)

    ax = axes[1]
    ax.hist(a, bins=20, color="#1f77b4", edgecolor="white", linewidth=0.3, orientation="horizontal")
    ax.axhline(2, color="#d62728", ls="--", lw=0.9)
    ax.set_ylabel(r"daily $\hat\alpha$")
    ax.set_xlabel("count")
    ax.set_title("(b) Distribution")
    fig.savefig(OUT / "fig_fullrecord_tail.png")
    plt.close(fig)
    print("  wrote results/research/fig_fullrecord_tail.png")


if __name__ == "__main__":
    main()
