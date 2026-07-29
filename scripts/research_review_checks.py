"""Reviewer-driven diagnostics: (1) does the dynamic 'budget' actually grow
super-sqrt(T), or is it Theta(sqrt(T)) with a big constant? (2) is the gradient
tail still heavy AFTER causal scale-normalization, or is alpha~2.4 an artifact of
pooling a drifting-scale mixture?

Runs entirely off saved artifacts (no raw parquet needed):
  results/research/heavybudget_daily.csv   (per sampled day: n, hill_alpha)
  results/research/gradnorm_at_wstar.npy    (time-ordered ||g_t|| at fixed w*)

Usage:  python scripts/research_review_checks.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"


def hill_alpha(a: np.ndarray, k: int) -> float:
    a = np.sort(a[np.isfinite(a) & (a > 0)])[::-1]
    k = min(k, a.size - 2)
    if k <= 0 or a[k] <= 0:
        return float("nan")
    return 1.0 / float(np.mean(np.log(a[:k]) - np.log(a[k])))


def check1_budget_exponent() -> None:
    print("=" * 68)
    print("CHECK 1  --  does the dynamic budget grow super-sqrt(T)?")
    print("=" * 68)
    daily = pl.read_csv(RES / "heavybudget_daily.csv").filter(
        pl.col("hill_alpha").is_finite()
    ).sort("date_id")
    n = daily["n"].to_numpy().astype(float)
    a = daily["hill_alpha"].to_numpy()
    stride = 13  # each sampled day represents ~stride days (research_heavybudget.py default)

    heavy = a < 2.0
    per_day = np.where(heavy, n ** (1.0 / np.maximum(a, 1e-6)), 0.0)

    # cumulative dynamic budget and cumulative horizon (rows), scaled by stride
    cum_budget = stride * np.cumsum(per_day)
    cum_T = stride * np.cumsum(n)

    # fit exponent on the region where the budget is positive
    m = cum_budget > 0
    lx, ly = np.log(cum_T[m]), np.log(cum_budget[m])
    slope, intercept = np.polyfit(lx, ly, 1)

    print(f"  sampled days (finite alpha): {a.size},  heavy (alpha<2): {int(heavy.sum())}")
    print(f"  fitted  log B_dyn = {slope:.3f} * log T + const")
    print(f"  --> exponent = {slope:.3f}   (0.5 = Theta(sqrt T);  1.0 = Theta(T))")
    # ratio to sqrt(T) at a few horizons
    print("\n  horizon T (rows)     B_dyn        B_dyn/sqrt(T)")
    idx = np.linspace(m.argmax(), len(cum_T) - 1, 6).astype(int)
    for i in idx:
        if cum_budget[i] > 0:
            print(f"   {cum_T[i]:14,.0f}   {cum_budget[i]:12,.0f}     {cum_budget[i]/np.sqrt(cum_T[i]):8.2f}")
    r0 = cum_budget[m][0] / np.sqrt(cum_T[m][0])
    r1 = cum_budget[-1] / np.sqrt(cum_T[-1])
    print(f"\n  ratio B_dyn/sqrt(T):  first={r0:.2f}  last={r1:.2f}  "
          f"({'GROWS' if r1 > 1.5 * r0 else 'roughly FLAT'})")


def check2_normalized_tail() -> None:
    print("\n" + "=" * 68)
    print("CHECK 2  --  is ||g|| still heavy AFTER causal scale-normalization?")
    print("=" * 68)
    g = np.load(RES / "gradnorm_at_wstar.npy").astype(float)
    g = g[np.isfinite(g) & (g > 0)]
    N = g.size
    fracs = [0.005, 0.01, 0.02, 0.05, 0.10]

    def report(name: str, x: np.ndarray) -> None:
        xs = x[np.isfinite(x) & (x > 0)]
        alphas = [hill_alpha(xs, int(f * xs.size)) for f in fracs]
        print(f"  {name:34s} " + "  ".join(f"k={f:.3f}:{al:5.2f}" for f, al in zip(fracs, alphas)))

    print(f"  time-ordered ||g_t|| at fixed w*,  N={N:,}")
    print("  Hill alpha at Hill-threshold fractions k (lower alpha = heavier):")
    report("raw ||g||  (pooled)", g)

    # causal winsorized-EMA scale (the tracker SN-OMD actually uses)
    try:
        from dfsl.preprocessing import OnlineScaleTracker

        tr = OnlineScaleTracker(decay=0.99, winsor=8.0)
        s = np.empty(N)
        for i, v in enumerate(g):
            s[i] = tr.scale
            tr.step(float(v))
        ema_norm = (g / np.maximum(s, 1e-12))[200:]  # drop warm-up
        report("||g||/s_t  (causal EMA tracker)", ema_norm)
    except Exception as exc:  # pragma: no cover
        print(f"  [EMA tracker unavailable: {exc}]")

    # causal trailing-median scale (predictable: shift by 1)
    for W in (250, 1000):
        med = pl.Series(g).rolling_median(window_size=W, min_periods=1).shift(1).to_numpy()
        med[0] = g[0]
        med_norm = (g / np.maximum(med, 1e-12))[W:]
        report(f"||g||/median_{W}  (causal)", med_norm)


if __name__ == "__main__":
    check1_budget_exponent()
    check2_normalized_tail()
