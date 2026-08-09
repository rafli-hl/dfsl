"""Deep research probes for the distribution-free sequential learning paper.

This is *investigation* code, not part of the paper build. It pressure-tests the
headline claims (OGD divergence, clipping wins, Catoni best) against the threats
to validity an ICML reviewer would raise, and writes machine-readable findings
to ``results/research/`` for later write-up.

Probes
------
RQ1  OGD / AdaptiveClip learning-rate sensitivity: is OGD's blow-up a learning
     rate artifact, or intrinsic? What is OGD's *best achievable* weighted R^2?
RQ2  Intrinsic gradient-norm tails at the fixed best predictor w* (and at 0),
     i.e. a learner-independent measure of gradient heavy-tailedness.
RQ3  Decomposition: does the gradient tail come from feature norms or residuals?

Usage::

    python scripts/research_findings.py --rows 200000 --date-lo 0 --date-hi 30
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

# The Windows console defaults to cp1252, which cannot encode polars' table
# borders; force UTF-8 so the diagnostic prints do not crash the run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dfsl import AdaptiveClip, JaneStreetDataset, OnlineGradientDescent, RobustOMD
from dfsl.evaluation import best_fixed_linear, linear_losses, regret_curve
from dfsl.evaluation.metrics import weighted_r2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "research"
OUT.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Tail-index tooling
# --------------------------------------------------------------------------- #
def hill_alpha(x: np.ndarray, k: int = 2000) -> float:
    """Hill tail-index estimate from the top-k order statistics of |x|.

    P(|X| > t) ~ t^{-alpha}. Returns np.nan if there is not enough tail mass.
    """
    a = np.abs(np.asarray(x, dtype=np.float64))
    a = a[np.isfinite(a) & (a > 0)]
    if a.size < k + 2:
        k = max(1, a.size - 2)
    order = np.sort(a)[::-1]
    if k <= 0 or order[k] <= 0:
        return float("nan")
    logs = np.log(order[:k]) - np.log(order[k])
    denom = float(np.mean(logs))
    return float("nan") if denom <= 0 else 1.0 / denom


def excess_kurtosis(x: np.ndarray) -> float:
    a = np.asarray(x, dtype=np.float64)
    a = a[np.isfinite(a)]
    m = a.mean()
    s = a.std()
    if s <= 0:
        return 0.0
    return float(np.mean(((a - m) / s) ** 4) - 3.0)


def tail_report(name: str, x: np.ndarray) -> dict:
    a = np.abs(np.asarray(x, dtype=np.float64))
    a = a[np.isfinite(a)]
    mean = float(a.mean())
    return {
        "quantity": name,
        "hill_alpha": hill_alpha(x),
        "excess_kurtosis": excess_kurtosis(x),
        "mean": mean,
        "p99": float(np.percentile(a, 99)),
        "p999": float(np.percentile(a, 99.9)),
        "max": float(a.max()),
        "p999_over_mean": float(np.percentile(a, 99.9) / max(mean, 1e-12)),
    }


# --------------------------------------------------------------------------- #
# RQ2 / RQ3 -- intrinsic gradient tails at a fixed predictor
# --------------------------------------------------------------------------- #
def probe_intrinsic_gradients(X, y, w) -> pl.DataFrame:
    print("\n=== RQ2/RQ3: intrinsic gradient tails at fixed predictors ===")
    w_star = best_fixed_linear(X, y, w)

    # Gradient of the weighted squared loss at a fixed predictor v:
    #   g_t(v) = 2 * omega_t * (x_t . v - y_t) * x_t
    def grads(v):
        r = X @ v - y
        return 2.0 * w[:, None] * r[:, None] * X, r

    g_star, r_star = grads(w_star)
    g_zero, r_zero = grads(np.zeros(X.shape[1]))

    rows = [
        tail_report("gradient_norm@w*", np.linalg.norm(g_star, axis=1)),
        tail_report("gradient_norm@0", np.linalg.norm(g_zero, axis=1)),
        tail_report("residual@w*", r_star),
        tail_report("feature_norm||x||", np.linalg.norm(X, axis=1)),
        tail_report("target|y|", y),
        tail_report("weight", w),
    ]
    df = pl.DataFrame(rows)
    with pl.Config(tbl_rows=20, tbl_cols=12, fmt_str_lengths=40):
        print(df)
    df.write_csv(OUT / "intrinsic_gradient_tails.csv")

    # Save the raw gradient-norm sample at w* for an honest motivation figure.
    np.save(OUT / "gradnorm_at_wstar.npy", np.linalg.norm(g_star, axis=1))
    print(f"  (saved gradnorm_at_wstar.npy, n={g_star.shape[0]})")
    return df


# --------------------------------------------------------------------------- #
# RQ1 -- learning-rate sensitivity / fairness
# --------------------------------------------------------------------------- #
def _run_r2(learner, X, y, w) -> dict:
    result = learner.run(list(zip(X, y, w)))
    r2 = weighted_r2(result.targets, result.predictions, result.weights)
    comp = linear_losses(X, y, best_fixed_linear(X, y, w), w)
    reg = float(regret_curve(result.losses, comp)[-1])
    finite = np.isfinite(result.losses)
    return {
        "weighted_r2": float(r2),
        "final_regret": reg,
        "mean_loss": float(np.mean(result.losses[finite])) if finite.any() else float("inf"),
        "n_nonfinite": int((~finite).sum()),
    }


def probe_lr_sensitivity(X, y, w) -> pl.DataFrame:
    print("\n=== RQ1: learning-rate sensitivity (OGD vs AdaptiveClip) ===")
    dim = X.shape[1]
    lrs = [5e-2, 1e-2, 5e-3, 1e-3, 5e-4, 1e-4, 5e-5, 1e-5]
    rows = []
    for lr in lrs:
        for name, make in (
            ("ogd", lambda lr=lr: OnlineGradientDescent(dim=dim, learning_rate=lr)),
            ("adaptive_clip", lambda lr=lr: AdaptiveClip(dim=dim, learning_rate=lr, window=512)),
        ):
            stats = _run_r2(make(), X, y, w)
            rows.append({"learner": name, "learning_rate": lr, **stats})
            print(
                f"  {name:14s} lr={lr:.0e}  R2={stats['weighted_r2']:+.5f}  "
                f"regret={stats['final_regret']:+.3g}  nonfinite={stats['n_nonfinite']}"
            )
    # One Catoni reference point at its config lr.
    cat = _run_r2(RobustOMD(dim=dim, learning_rate=5e-3, estimator="catoni", window=512), X, y, w)
    rows.append({"learner": "robust_omd[catoni]", "learning_rate": 5e-3, **cat})
    print(f"  robust_omd[catoni] lr=5e-03  R2={cat['weighted_r2']:+.5f}  regret={cat['final_regret']:+.3g}")

    df = pl.DataFrame(rows)
    df.write_csv(OUT / "lr_sensitivity.csv")

    best_ogd = df.filter(pl.col("learner") == "ogd").sort("weighted_r2", descending=True).row(0, named=True)
    best_clip = df.filter(pl.col("learner") == "adaptive_clip").sort("weighted_r2", descending=True).row(0, named=True)
    print(
        f"\n  >> OGD best R2 = {best_ogd['weighted_r2']:+.5f} at lr={best_ogd['learning_rate']:.0e}"
        f"  |  AdaptiveClip best R2 = {best_clip['weighted_r2']:+.5f} at lr={best_clip['learning_rate']:.0e}"
    )
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=200000)
    ap.add_argument("--date-lo", type=int, default=0)
    ap.add_argument("--date-hi", type=int, default=30)
    args = ap.parse_args()

    print(f"Loading Jane slice: date[{args.date_lo},{args.date_hi}) rows<= {args.rows} (standardized)")
    ds = JaneStreetDataset(
        date_range=(args.date_lo, args.date_hi), max_rows=args.rows, standardize=True
    )
    X, y, w = ds.X, ds.y, ds.weights
    print(f"  loaded X={X.shape}, y={y.shape}, weight mean={w.mean():.3f}")

    summary = {}
    tails = probe_intrinsic_gradients(X, y, w)
    summary["intrinsic_tails"] = tails.to_dicts()
    lr = probe_lr_sensitivity(X, y, w)
    summary["lr_sensitivity"] = lr.to_dicts()

    (OUT / "findings_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nFindings written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
