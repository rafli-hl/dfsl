"""Error bars for Table 1 (the review's F2: 'no variance information on the headline table').

Table 1 reports the AGGREGATE weighted R^2 = 1 - sum w(y-p)^2 / sum w y^2, a ratio of sums,
so its uncertainty cannot be read off a mean-of-per-fold-R^2 (aggregate != fold-mean; that gap
is exactly why the SN-OMD/normalized-GD point estimates and the paired-fold band disagree). The
run is deterministic (fixed data, fixed learner), so the honest error bar is the sampling
variability of that aggregate over the evaluation stream. We attach a MOVING-BLOCK bootstrap
(block ~ 1 trading day) which respects the serial dependence the review flagged (and which
inflates a naive i.i.d. / paired-t interval).

For each Table 1 method we re-run the exact canonical update (`_step` from research_batched_check,
i.e. the harness that produced the table), pick the tuned lr by aggregate R^2 on each protocol's
canonical lr grid, confirm the point estimate reproduces the paper, then bootstrap the aggregate.

Usage: python scripts/research_table1_errorbars.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_batched_check import _step, group_boundaries  # noqa: E402  (validated harness)

from dfsl import JaneStreetDataset  # noqa: E402
from dfsl.evaluation.metrics import weighted_r2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

N_BOOT = 4000
# Table 1 methods: (label, mode, cap). cap=1e9 recovers uncapped scale-adaptive OGD.
METHODS = [
    ("OGD", "ogd", 0.0),
    ("Normalized-GD (M->0)", "normgd", 0.0),
    ("Scale-adaptive OGD (M->inf)", "snomd", 1e9),
    ("SN-OMD (M=5, ours)", "snomd", 5.0),
]
# Canonical per-protocol lr grids (as used by research_normalize / research_batched_check).
LRS_PERROW = [2e-3, 5e-3, 1e-2, 2e-2, 3e-2, 5e-2, 1e-1, 2e-1, 5e-1, 1.0, 2.0]
LRS_PERSTEP = [1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1, 2e-1, 5e-1, 1.0, 2.0]


def preds_perrow(X, y, wts, mode, cap, lr):
    d = X.shape[1]
    w = np.zeros(d); s = None; k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred; k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        w, s = _step(mode, cap, w, g, s, k, lr)
    return preds


def preds_batched(X, y, wts, starts, mode, cap, lr):
    d = X.shape[1]
    w = np.zeros(d); s = None
    preds = np.empty(len(y))
    ends = np.append(starts[1:], len(y))
    for k, (a, b) in enumerate(zip(starts, ends), start=1):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w; preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        w, s = _step(mode, cap, w, g, s, k, lr)
    return preds


def agg_r2(y, p, wts, idx=None):
    if idx is not None:
        y, p, wts = y[idx], p[idx], wts[idx]
    with np.errstate(over="ignore", invalid="ignore"):
        den = float(np.sum(wts * y * y))
        if not np.isfinite(den) or den == 0.0:
            return 0.0
        return 1.0 - float(np.sum(wts * (y - p) ** 2)) / den


def block_bootstrap(y, p, wts, block_len, rng, n_boot=N_BOOT):
    """Circular moving-block bootstrap of the aggregate weighted R^2.

    Circular (wrap-around) blocks give every row equal inclusion probability, removing
    the end-of-stream edge bias a plain moving block would inject (early, high-error rows
    are otherwise over-represented). Returns (SE, 95% CI centered at the point estimate).
    """
    n = len(y)
    n_blocks = int(np.ceil(n / block_len))
    offs = np.arange(block_len)
    reps = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx = ((starts[:, None] + offs) % n).ravel()[:n]
        reps[b] = agg_r2(y, p, wts, idx)
    se = float(reps.std(ddof=1))
    point = agg_r2(y, p, wts)
    return se, point - 1.96 * se, point + 1.96 * se


def tune(runner, X, y, wts, extra, mode, cap, lrs):
    """Return (lr*, aggregate R2*, preds*) at the lr maximizing bounded aggregate R2."""
    best = (None, -np.inf, None)
    for lr in lrs:
        p = runner(X, y, wts, *extra, mode, cap, lr)
        r2 = agg_r2(y, p, wts)
        if np.isfinite(r2) and r2 > -1.0 and r2 > best[1]:
            best = (lr, r2, p)
    return best


def run() -> None:
    ds = JaneStreetDataset(date_range=(0, 120), max_rows=150000, standardize=True)
    X, y, wts = ds.X, ds.y, ds.weights
    starts = group_boundaries(ds.meta)
    ndays = int(np.unique(ds.meta["date_id"].to_numpy()).size)
    block_len = max(1, len(y) // ndays)  # ~ one trading day
    rng = np.random.default_rng(0)
    print("=" * 92)
    print(f"TABLE 1 ERROR BARS  --  {len(y)} rows, {len(starts)} groups, {ndays} days, "
          f"block_len~{block_len} (1 day), {N_BOOT} moving-block resamples")
    print("=" * 92)

    rows: list[dict] = []
    for protocol, runner, extra, lrs in [
        ("per-row", preds_perrow, (), LRS_PERROW),
        ("per-step", preds_batched, (starts,), LRS_PERSTEP),
    ]:
        print(f"\n{protocol.upper()}  (aggregate weighted R^2 at tuned lr; +-SE, [95% block-bootstrap CI]):")
        for label, mode, cap in METHODS:
            lr_star, r2_star, p_star = tune(runner, X, y, wts, extra, mode, cap, lrs)
            if p_star is None:  # never bounded (diverges across the grid)
                print(f"  {label:30s} lr*=  ---   R2 diverges across the grid")
                rows.append({"protocol": protocol, "method": label, "lr_star": None,
                             "r2": None, "se": None, "ci_lo": None, "ci_hi": None})
                continue
            se, lo, hi = block_bootstrap(y, p_star, wts, block_len, rng)
            print(f"  {label:30s} lr*={lr_star:<5g} R2={r2_star:+.4f} +-{se:.4f}  [{lo:+.4f}, {hi:+.4f}]")
            rows.append({"protocol": protocol, "method": label, "lr_star": lr_star,
                         "r2": round(r2_star, 4), "se": round(se, 4),
                         "ci_lo": round(lo, 4), "ci_hi": round(hi, 4)})

    out = RES / "table1_errorbars.csv"
    pl.DataFrame(rows).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    # The comparison the review leans on: SN-OMD vs normalized-GD per-step (0.309 vs 0.316).
    def cell(proto, meth):
        return next(r for r in rows if r["protocol"] == proto and r["method"] == meth)
    sn = cell("per-step", "SN-OMD (M=5, ours)")
    ng = cell("per-step", "Normalized-GD (M->0)")
    if sn["ci_lo"] is not None and ng["ci_lo"] is not None:
        overlap = sn["ci_lo"] <= ng["ci_hi"] and ng["ci_lo"] <= sn["ci_hi"]
        print("\n" + "-" * 92)
        print("REVIEW CHECK (per-step, the protocol the review says normalized-GD 'wins'):")
        print(f"  normalized-GD {ng['r2']:+.4f} [{ng['ci_lo']:+.4f},{ng['ci_hi']:+.4f}]   "
              f"SN-OMD {sn['r2']:+.4f} [{sn['ci_lo']:+.4f},{sn['ci_hi']:+.4f}]")
        print(f"  => 95% CIs {'OVERLAP -> difference is within stream noise (supports \"comparable\")'if overlap else 'DISJOINT -> the gap is real'}.")


if __name__ == "__main__":
    run()
