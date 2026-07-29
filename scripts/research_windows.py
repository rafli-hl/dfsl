"""RQ4 -- stability of the method ranking across disjoint time windows.

Uses each method's *own* best learning rate (from ``fair_tuning_best.csv``, the
output of ``research_fairness.py``) and runs every method on several disjoint
Jane Street date windows. If the ranking flips window to window, no single
method can be claimed "best"; if it is stable, the ranking is real.

Usage::

    python scripts/research_windows.py --rows 60000
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

# Disjoint date windows spanning early / mid / late in the 1,699-day record.
WINDOWS = [(0, 20), (30, 50), (100, 120), (400, 420), (900, 920)]

# Fallback learning rates if fair_tuning_best.csv is absent.
DEFAULT_LR = {
    "ogd": 1e-3,
    "adaptive_clip": 1e-2,
    "robust_omd[catoni]": 5e-3,
    "robust_omd[median_of_means]": 5e-3,
    "robust_omd[trimmed_mean]": 5e-3,
}


def load_best_lrs() -> dict[str, float]:
    path = OUT / "fair_tuning_best.csv"
    if not path.exists():
        print("  (fair_tuning_best.csv not found; using default learning rates)")
        return dict(DEFAULT_LR)
    df = pl.read_csv(path)
    lrs = {r["method"]: float(r["learning_rate"]) for r in df.iter_rows(named=True)}
    for k, v in DEFAULT_LR.items():
        lrs.setdefault(k, v)
    return lrs


def make_learner(name: str, dim: int, lr: float):
    if name == "ogd":
        return OnlineGradientDescent(dim=dim, learning_rate=lr)
    if name == "adaptive_clip":
        return AdaptiveClip(dim=dim, learning_rate=lr, window=512)
    estimator = name.split("[")[1].rstrip("]")
    return RobustOMD(dim=dim, learning_rate=lr, estimator=estimator, window=512, clip_multiplier=3.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=60000)
    ap.add_argument(
        "--clip-lr",
        type=float,
        default=None,
        help="Override: force this (conservative) lr for every clipped method, "
        "to test the deployable operating point instead of the in-sample optimum.",
    )
    ap.add_argument("--ogd-lr", type=float, default=None, help="Override lr for OGD.")
    args = ap.parse_args()

    if args.clip_lr is not None:
        lrs = {m: args.clip_lr for m in DEFAULT_LR}
        lrs["ogd"] = args.ogd_lr if args.ogd_lr is not None else 2e-3
        print(f"OVERRIDE: clipped methods lr={args.clip_lr:.0e}, ogd lr={lrs['ogd']:.0e}")
    else:
        lrs = load_best_lrs()
    methods = list(DEFAULT_LR)
    print("Per-method learning rates:", {m: f"{lrs[m]:.0e}" for m in methods})

    rows = []
    for lo, hi in WINDOWS:
        ds = JaneStreetDataset(date_range=(lo, hi), max_rows=args.rows, standardize=True)
        X, y, w = ds.X, ds.y, ds.weights
        dim = X.shape[1]
        comp = linear_losses(X, y, best_fixed_linear(X, y, w), w)
        stream = list(zip(X, y, w))
        print(f"\nwindow date[{lo},{hi})  n={len(y)}")
        window_scores = {}
        for name in methods:
            res = make_learner(name, dim, lrs[name]).run(stream)
            r2 = float(weighted_r2(res.targets, res.predictions, res.weights))
            reg = float(regret_curve(res.losses, comp)[-1])
            window_scores[name] = r2
            rows.append({"window": f"[{lo},{hi})", "method": name, "weighted_r2": r2, "final_regret": reg})
            print(f"  {name:28s} R2={r2:+.5f}  regret={reg:+.3g}")
        ranking = sorted(window_scores, key=window_scores.get, reverse=True)
        print("  rank:", " > ".join(m.replace("robust_omd", "").strip("[]") for m in ranking))

    suffix = "" if args.clip_lr is None else f"_cliplr{args.clip_lr:.0e}"
    df = pl.DataFrame(rows)
    df.write_csv(OUT / f"window_stability{suffix}.csv")

    print("\n=== Ranking stability (mean +/- std weighted R2 across windows) ===")
    agg = (
        df.group_by("method")
        .agg(
            pl.col("weighted_r2").mean().alias("mean_r2"),
            pl.col("weighted_r2").std().alias("std_r2"),
            pl.col("weighted_r2").min().alias("min_r2"),
            pl.col("weighted_r2").max().alias("max_r2"),
        )
        .sort("mean_r2", descending=True)
    )
    for r in agg.iter_rows(named=True):
        print(
            f"  {r['method']:28s} mean={r['mean_r2']:+.5f}  std={r['std_r2']:.5f}  "
            f"[{r['min_r2']:+.5f}, {r['max_r2']:+.5f}]"
        )
    agg.write_csv(OUT / f"window_stability_summary{suffix}.csv")
    print(f"\nFindings written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
