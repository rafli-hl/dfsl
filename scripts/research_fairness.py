"""Fair-comparison probes: per-method learning-rate tuning and the
standardization-vs-clipping confound.

Motivated by the finding that OGD's apparent "divergence" on Jane Street is a
learning-rate artifact: at a shared lr tuned for the clipped methods OGD blows
up, but at its own best lr it is positive. A defensible comparison must tune the
learning rate *per method*. This script does that, and separately asks whether
online standardization or gradient clipping is doing the real work.

Usage::

    python scripts/research_fairness.py --rows 100000
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
OUT.mkdir(parents=True, exist_ok=True)

# Grid must extend high enough to bracket the clipped optimum: clipped methods
# keep improving past 1e-2 and only break down around 4-5e-2, whereas OGD already
# diverges by 1e-2. A grid that stops at 1e-2 understates the clipping advantage.
LRS = [1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 3e-2, 4e-2]


def make_learner(name: str, dim: int, lr: float):
    if name == "ogd":
        return OnlineGradientDescent(dim=dim, learning_rate=lr)
    if name == "adaptive_clip":
        return AdaptiveClip(dim=dim, learning_rate=lr, window=512)
    estimator = name.split("[")[1].rstrip("]")
    return RobustOMD(dim=dim, learning_rate=lr, estimator=estimator, window=512, clip_multiplier=3.0)


def run_r2(learner, stream, X, y, w, comp) -> dict:
    result = learner.run(stream)
    r2 = weighted_r2(result.targets, result.predictions, result.weights)
    reg = float(regret_curve(result.losses, comp)[-1])
    return {"weighted_r2": float(r2), "final_regret": reg}


def probe_fair_tuning(X, y, w) -> pl.DataFrame:
    print("\n=== RQ1b: per-method learning-rate tuning (fair ranking) ===")
    dim = X.shape[1]
    comp = linear_losses(X, y, best_fixed_linear(X, y, w), w)
    stream = list(zip(X, y, w))
    methods = [
        "ogd",
        "adaptive_clip",
        "robust_omd[catoni]",
        "robust_omd[median_of_means]",
        "robust_omd[trimmed_mean]",
    ]
    rows = []
    for name in methods:
        for lr in LRS:
            stats = run_r2(make_learner(name, dim, lr), stream, X, y, w, comp)
            rows.append({"method": name, "learning_rate": lr, **stats})
            print(f"  {name:28s} lr={lr:.0e}  R2={stats['weighted_r2']:+.5f}  regret={stats['final_regret']:+.3g}")
    df = pl.DataFrame(rows)
    df.write_csv(OUT / "fair_tuning.csv")

    print("\n  >> Best-achievable weighted R2 per method (fair, lr-tuned):")
    best = (
        df.sort("weighted_r2", descending=True)
        .group_by("method", maintain_order=True)
        .first()
        .sort("weighted_r2", descending=True)
    )
    for r in best.iter_rows(named=True):
        print(f"     {r['method']:28s} R2={r['weighted_r2']:+.5f}  @ lr={r['learning_rate']:.0e}")
    best.write_csv(OUT / "fair_tuning_best.csv")
    return df


def probe_standardization(date_lo: int, date_hi: int, rows: int) -> pl.DataFrame:
    print("\n=== RQ5: standardization vs clipping (confound) ===")
    results = []
    for std in (True, False):
        ds = JaneStreetDataset(date_range=(date_lo, date_hi), max_rows=rows, standardize=std)
        X, y, w = ds.X, ds.y, ds.weights
        dim = X.shape[1]
        comp = linear_losses(X, y, best_fixed_linear(X, y, w), w)
        stream = list(zip(X, y, w))
        for name in ("ogd", "adaptive_clip", "robust_omd[catoni]"):
            # Give each configuration a small, safe lr so raw-scale features do
            # not trivially overflow; the question is whether clipping alone can
            # substitute for standardization.
            lr = 1e-3 if std else 1e-6
            stats = run_r2(make_learner(name, dim, lr), stream, X, y, w, comp)
            results.append({"standardize": std, "method": name, "learning_rate": lr, **stats})
            print(
                f"  standardize={str(std):5s} {name:28s} lr={lr:.0e}  "
                f"R2={stats['weighted_r2']:+.5f}  regret={stats['final_regret']:+.3g}"
            )
    df = pl.DataFrame(results)
    df.write_csv(OUT / "standardization_ablation.csv")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=100000)
    ap.add_argument("--date-lo", type=int, default=0)
    ap.add_argument("--date-hi", type=int, default=30)
    ap.add_argument("--skip-std", action="store_true", help="skip the standardization ablation")
    args = ap.parse_args()

    print(f"Loading Jane slice: date[{args.date_lo},{args.date_hi}) rows<= {args.rows} (standardized)")
    ds = JaneStreetDataset(date_range=(args.date_lo, args.date_hi), max_rows=args.rows, standardize=True)
    probe_fair_tuning(ds.X, ds.y, ds.weights)
    if not args.skip_std:
        probe_standardization(args.date_lo, args.date_hi, args.rows)
    print(f"\nFindings written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
