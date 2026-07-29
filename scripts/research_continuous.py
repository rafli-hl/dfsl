"""Continuous-stream deployability test.

The per-window restart experiment (research_windows.py) is unfair to the clipped
methods: it restarts the lr/sqrt(t) schedule and the clipping warm-up on every
window, so each turbulent window is met with a large effective step size and an
unprotected first few steps. The realistic question is different:

    Streaming ONE learner continuously through calm -> turbulent -> calm regimes,
    does gradient clipping let you run a base learning rate that (a) wins on the
    calm regimes and (b) survives the turbulent regime mid-stream, where plain
    OGD at the same base rate would blow up?

If yes, clipping has a genuine, deployable advantage. If clipping diverges at
every base rate where it beats OGD, it does not.

We stream date[0,120) in chronological order (this span contains the turbulent
date[30,50) patch that broke the clipped methods on restart) and, for a grid of
base learning rates, report each learner's final weighted R^2 and its peak
rolling loss (a divergence flag).

Usage::

    python scripts/research_continuous.py --date-lo 0 --date-hi 120 --rows 300000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dfsl import AdaptiveClip, JaneStreetDataset, OnlineGradientDescent, RobustOMD
from dfsl.evaluation import best_fixed_linear, linear_losses, regret_curve
from dfsl.evaluation.metrics import weighted_r2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "research"

BASE_LRS = [2e-3, 5e-3, 1e-2, 2e-2, 3e-2]
METHODS = ["ogd", "adaptive_clip", "robust_omd[catoni]", "robust_omd[median_of_means]", "robust_omd[trimmed_mean]"]


def make_learner(name: str, dim: int, lr: float):
    if name == "ogd":
        return OnlineGradientDescent(dim=dim, learning_rate=lr)
    if name == "adaptive_clip":
        return AdaptiveClip(dim=dim, learning_rate=lr, window=512)
    estimator = name.split("[")[1].rstrip("]")
    return RobustOMD(dim=dim, learning_rate=lr, estimator=estimator, window=512, clip_multiplier=3.0)


def rolling_max_loss(losses: np.ndarray, window: int = 2000) -> float:
    x = np.asarray(losses, dtype=np.float64)
    x = np.where(np.isfinite(x), x, np.inf)
    w = max(1, min(window, x.size))
    roll = np.convolve(np.minimum(x, 1e300), np.ones(w) / w, mode="valid")
    return float(np.max(roll))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-lo", type=int, default=0)
    ap.add_argument("--date-hi", type=int, default=120)
    ap.add_argument("--rows", type=int, default=300000)
    args = ap.parse_args()

    print(f"Loading continuous slice date[{args.date_lo},{args.date_hi}) rows<= {args.rows}")
    ds = JaneStreetDataset(date_range=(args.date_lo, args.date_hi), max_rows=args.rows, standardize=True)
    X, y, w = ds.X, ds.y, ds.weights
    dim = X.shape[1]
    print(f"  n={len(y)}  (streamed continuously, t grows across the whole span)")
    comp = linear_losses(X, y, best_fixed_linear(X, y, w), w)
    stream = list(zip(X, y, w))

    rows = []
    for lr in BASE_LRS:
        print(f"\nbase lr = {lr:.0e}")
        for name in METHODS:
            res = make_learner(name, dim, lr).run(stream)
            r2 = float(weighted_r2(res.targets, res.predictions, res.weights))
            reg = float(regret_curve(res.losses, comp)[-1])
            peak = rolling_max_loss(res.losses)
            diverged = (not np.isfinite(r2)) or r2 < -1.0 or peak > 50.0
            flag = "  <-- DIVERGED" if diverged else ""
            rows.append(
                {"learning_rate": lr, "method": name, "weighted_r2": r2, "final_regret": reg,
                 "peak_rolling_loss": peak, "diverged": diverged}
            )
            print(f"  {name:28s} R2={r2:+.5f}  peak_roll_loss={peak:9.3f}{flag}")

    df = pl.DataFrame(rows)
    df.write_csv(OUT / "continuous_stream.csv")

    print("\n=== Largest base lr that stays stable (not diverged), per method ===")
    for name in METHODS:
        sub = df.filter((pl.col("method") == name) & (~pl.col("diverged")))
        if sub.height:
            best = sub.sort("weighted_r2", descending=True).row(0, named=True)
            hi = sub.sort("learning_rate", descending=True).row(0, named=True)
            print(
                f"  {name:28s} best stable R2={best['weighted_r2']:+.5f}@lr={best['learning_rate']:.0e}"
                f"  | max stable lr={hi['learning_rate']:.0e} (R2={hi['weighted_r2']:+.5f})"
            )
        else:
            print(f"  {name:28s} diverged at every tested lr")
    print(f"\nFindings written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
