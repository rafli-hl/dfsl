"""Second market, algorithm side: does the STABILITY dichotomy replicate on crypto? (scope item)

Companion to research_crypto_mechanism.py (which shows the tail mechanism replicates on BTC/USDT).
Here we run the paper's algorithm comparison on the same stream. Crypto hourly returns are very
nearly unpredictable (best-fixed-linear R^2 ~ 0.002), so the ACCURACY ranking is uninformative --
and we report it honestly as such. The load-bearing claim a second market can test is the
STABILITY dichotomy: on a stream whose gradient scale drifts ~22x, do the scale-DEPENDENT methods
(plain OGD, uncapped scale-adaptive OGD) diverge at competitive learning rates while every
bounded scale-free method (SN-OMD, normalized-GD, fixed-tau clip, AdaGrad-Norm, Cutkosky-Mehta)
stays bounded -- as they do on Jane?

(A) learning-rate sweep on window 1: best R^2 and the highest lr that stays bounded (the fig:main
    analogue). (B) ten disjoint windows across 2017-2025, hyperparameters frozen from window 1:
    divergence counts, mirroring the Jane replication table.

Usage:  .venv/Scripts/python.exe scripts/research_crypto_algorithms.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_baselines import (  # noqa: E402  (dataset-agnostic; take X,y,wts,...)
    adagrad_perrow,
    anchor_perrow,
    blockmed_perrow,
    cm_perrow,
    fixedclip_perrow,
)
from research_crypto_mechanism import load_features  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

LRS = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0]
LRS_OGD = [1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 0.1, 0.2, 0.5, 1.0, 2.0]  # OGD needs the low end too
LRS_ADA = [0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 5.0]
TAU = 20.0


def run(name, X, y, w, lr):
    if name == "OGD":
        return anchor_perrow(X, y, w, "ogd", 0.0, lr)
    if name == "Normalized-GD":
        return anchor_perrow(X, y, w, "normgd", 0.0, lr)
    if name == "Scale-adaptive OGD":
        return anchor_perrow(X, y, w, "snomd", 1e9, lr)
    if name == "SN-OMD (M=5)":
        return anchor_perrow(X, y, w, "snomd", 5.0, lr)
    if name == "SN-OMD + block":
        return blockmed_perrow(X, y, w, lr, cap=5.0)
    if name == "fixed-tau clip":
        return fixedclip_perrow(X, y, w, TAU, lr)
    if name == "AdaGrad-Norm":
        return adagrad_perrow(X, y, w, lr)
    if name == "Cutkosky-Mehta":
        return cm_perrow(X, y, w, 600.0, 0.5, lr)
    raise ValueError(name)


def peak_rolling_loss(y, preds, w, window=2000):
    x = w * (preds - y) ** 2
    x = np.where(np.isfinite(x), np.minimum(x, 1e300), 1e300)
    win = max(1, min(window, x.size))
    return float(np.max(np.convolve(x, np.ones(win) / win, mode="valid")))


# True-explosion threshold: crypto returns are unpredictable, so at a large lr every method (even
# bounded ones) accumulates noise and overshoots the O(1) target -- its peak loss grows O(sqrt t)
# to ~10-100 without the iterate exploding. Scale-DEPENDENT methods instead blow up super-linearly
# to 1e4..1e300. A 1e3 cutoff sits in that 2-orders-of-magnitude gap and flags only true divergence.
DIVERGE_PEAK = 1e3


def diverged(y, preds, w):
    r2 = agg_r2(y, preds, w)
    return (not np.isfinite(r2)) or peak_rolling_loss(y, preds, w) > DIVERGE_PEAK


GRIDS = {"OGD": LRS_OGD, "Scale-adaptive OGD": LRS, "AdaGrad-Norm": LRS_ADA}
METHODS = ["OGD", "Normalized-GD", "Scale-adaptive OGD", "SN-OMD (M=5)", "SN-OMD + block",
           "fixed-tau clip", "AdaGrad-Norm", "Cutkosky-Mehta"]


def main() -> None:
    X, y, w, day_id, dt, cols = load_features()
    # Rescale the target by a CONSTANT (its global std) to an O(1) scale. Hourly returns are ~0.005,
    # so a Jane-calibrated learning rate would make even bounded methods overshoot the tiny target
    # and score R^2<-1 (flagged as "divergence") without the iterates actually exploding. A constant
    # rescale leaves R^2 unchanged (scale-invariant) and preserves the volatility-clustering drift
    # (high-vol hours still have larger |y|); it only calibrates the loss/lr scale to match Jane.
    y = y / float(np.std(y))
    n = len(y)
    # ten disjoint windows across the record (~6000 bars each with gaps)
    win = 6000; gap = (n - 10 * win) // 9
    windows = [(i * (win + gap), i * (win + gap) + win) for i in range(10)]
    print("=" * 96)
    print(f"CRYPTO ALGORITHMS  BTC/USDT 1h  n={n}  {str(dt[0])[:10]}..{str(dt[-1])[:10]}  "
          f"10 windows x {win} bars")
    print("=" * 96)

    lo, hi = windows[0]
    Xw, yw, ww = X[lo:hi], y[lo:hi], w[lo:hi]

    # ---- (A) lr sweep on window 1: peak rolling loss + highest bounded lr (the fig:main analogue) ----
    print("\n(A) LEARNING-RATE SWEEP, window 1 --- peak rolling loss (does it TRULY explode?)")
    print(f"    {'method':22s} {'peak@min-lr':>12} {'peak@max-lr':>12}  highest-bounded-lr")
    sweep_rows = []
    for name in METHODS:
        grid = GRIDS.get(name, LRS)
        max_stable, pk = 0.0, {}
        for lr in grid:
            p = run(name, Xw, yw, ww, lr)
            peak = peak_rolling_loss(yw, p, ww)
            pk[lr] = peak
            if np.isfinite(peak) and peak <= DIVERGE_PEAK:
                max_stable = max(max_stable, lr)
            sweep_rows.append({"method": name, "lr": lr, "peak_loss": float(peak),
                               "r2": round(float(agg_r2(yw, p, ww)), 5)})
        scale_dep = name in ("OGD", "Scale-adaptive OGD")
        print(f"    {name:22s} {pk[grid[0]]:>12.3g} {pk[grid[-1]]:>12.3g}  lr<= {max_stable:<5g}"
              f"  (grid {grid[0]:g}..{grid[-1]:g}){'  <-- scale-DEPENDENT' if scale_dep else ''}")
    pl.DataFrame(sweep_rows).write_csv(RES / "crypto_lr_sweep.csv")

    # ---- (B) ten windows at a fixed COMPETITIVE rate lr=2 (not the tiny R^2-optimal rate) ----
    # On unpredictable crypto every method's accuracy-optimal lr is tiny (all stable there), so the
    # dichotomy only shows at a competitive rate: does the scale-dependent step blow up across
    # regimes while the bounded scale-free step does not? (Jane's "frozen competitive rate diverges".)
    LR_FIX = 2.0
    print(f"\n(B) TEN WINDOWS at a fixed competitive lr={LR_FIX} (divergence = true blow-up, peak>{DIVERGE_PEAK:g})")
    out = []
    for name in METHODS:
        ndiv, peaks, r2s = 0, [], []
        for (a, b) in windows:
            p = run(name, X[a:b], y[a:b], w[a:b], LR_FIX)
            dv = diverged(y[a:b], p, w[a:b])
            ndiv += int(dv); peaks.append(peak_rolling_loss(y[a:b], p, w[a:b]))
            if not dv:
                r2s.append(float(agg_r2(y[a:b], p, w[a:b])))
        medpeak = float(np.median(peaks))
        meanr2 = float(np.mean(r2s)) if r2s else float("nan")
        out.append({"method": name, "lr": LR_FIX, "diverged": f"{ndiv}/10",
                    "median_peak_loss": round(medpeak, 3), "mean_r2_bounded": round(meanr2, 5)})
        scale_dep = name in ("OGD", "Scale-adaptive OGD")
        print(f"    {name:22s} diverged={ndiv}/10  median peak-loss={medpeak:.3g}"
              f"  {'<-- scale-DEPENDENT' if scale_dep else ''}")
    pl.DataFrame(out).write_csv(RES / "crypto_algorithms.csv")

    div_free = [r["method"] for r in out if r["diverged"] == "0/10"]
    diverging = [f"{r['method']}({r['diverged']})" for r in out if r["diverged"] != "0/10"]
    print("\nVERDICT (stability dichotomy at a competitive rate):")
    print(f"  0/10 divergences (bounded scale-free): {div_free}")
    print(f"  diverges on >=1 window:               {diverging}")
    print("  accuracy: all R^2 ~ 0 (hourly returns are unpredictable) -- the second market's value")
    print("  is the mechanism (tail) + the stability dichotomy, not an accuracy ranking.")
    print(f"\n[saved {(RES/'crypto_algorithms.csv').relative_to(ROOT)}, crypto_lr_sweep.csv]")


if __name__ == "__main__":
    main()
