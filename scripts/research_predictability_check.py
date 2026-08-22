"""Decompose the SN-OMD gap between Table 1 (0.2845) and the schedule sweep (0.2467).

Two things differ between those two runs, and the appendix previously attributed the gap
to the first alone:

  (a) the tuning grid -- ``research_baselines.LRS`` contains lr=2 (the optimum),
      the schedule sweep's grid stops at lr=1;
  (b) the tracker's measurability -- ``research_batched_check._step`` USED TO normalize by
      the POST-update scale s_t (which already contains ||g_t||), where Algorithm 1 requires
      the PRE-update, predictable s_{t-1}.

(b) is the algorithm's defining property, not a free implementation choice: the
high-probability analysis needs s_t to be F_{t-1}-measurable. ``_step`` has since been
corrected, so (b) no longer varies in the shipped code -- this script keeps both variants
locally as a standing regression check and as the record of how the gap decomposed.

It crosses the two factors -- {post-update, predictable} x the full baselines grid -- on the
reported window, with a *paired* circular block bootstrap on each contrast (the marginal SEs
are ~.08, far too wide to resolve a ~.04 difference between two runs on the same rows).

Result: the grid accounts for +0.0379 of the +0.0378 total gap; the measurability contrast is
+0.0001 at lr=2 and +0.0009 at lr=1. The defect was real; it was not what moved the number.

Usage::

    .venv/Scripts/python.exe scripts/research_predictability_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_baselines import LRS  # noqa: E402
from research_batched_check import group_boundaries  # noqa: E402
from research_table1_errorbars import N_BOOT, agg_r2, block_bootstrap  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

CAP = 5.0
DECAY = 0.99
WINSOR = 8.0


def snomd_perrow(X, y, wts, lr, predictable, cap=CAP, decay=DECAY, winsor=WINSOR):
    """SN-OMD per-row with the tracker's measurability as a switch.

    ``predictable=True`` is Algorithm 1: normalize by s_{t-1}, then fold ||g_t|| in.
    ``predictable=False`` is the shipped ``_step``: fold ||g_t|| in first, then normalize
    by the updated s_t. Identical in every other respect, including the t=1 round (both
    normalize by ||g_1||) and the k that drives the eta/sqrt(k) schedule.
    """
    d = X.shape[1]; w = np.zeros(d); s = None; k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred; k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0:
            continue
        if predictable:
            sc = max(s if s is not None else gn, 1e-8)
            s = gn if s is None else decay * s + (1.0 - decay) * min(gn, winsor * s)
        else:
            s = gn if s is None else decay * s + (1.0 - decay) * min(gn, winsor * s)
            sc = max(s, 1e-8)
        ghat = g / sc
        gnn = float(np.linalg.norm(ghat))
        if gnn > cap:
            ghat = ghat * (cap / gnn)
        w = w - (lr / np.sqrt(k)) * ghat
    return preds


def paired_bootstrap(y, pa, pb, wts, block_len, rng, n_boot=N_BOOT):
    """Circular block bootstrap of the R^2 DIFFERENCE, resampling both arms on the same
    blocks. Paired because the two arms are the same rows under two updates."""
    n = len(y)
    n_blocks = int(np.ceil(n / block_len))
    offs = np.arange(block_len)
    reps = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx = ((starts[:, None] + offs) % n).ravel()[:n]
        reps[b] = agg_r2(y, pa, wts, idx) - agg_r2(y, pb, wts, idx)
    se = float(reps.std(ddof=1))
    point = agg_r2(y, pa, wts) - agg_r2(y, pb, wts)
    return point, se, point - 1.96 * se, point + 1.96 * se


def run() -> None:
    ds = JaneStreetDataset(date_range=(0, 120), max_rows=150000, standardize=True)
    X, y, wts = ds.X, ds.y, ds.weights
    starts = group_boundaries(ds.meta)
    ndays = int(np.unique(ds.meta["date_id"].to_numpy()).size)
    block_len = max(1, len(y) // ndays)
    rng = np.random.default_rng(0)

    print("=" * 96)
    print(f"PREDICTABILITY x GRID decomposition (per-row)  --  {len(y)} rows, {ndays} days, "
          f"block~{block_len}, {N_BOOT} resamples")
    print(f"grid = {LRS}")
    print("=" * 96)

    preds: dict[tuple[bool, float], np.ndarray] = {}
    rows: list[dict] = []
    for predictable in (False, True):
        tag = "predictable s_{t-1} (Alg. 1)" if predictable else "post-update s_t (shipped)"
        print(f"\n  tracker = {tag}")
        best = (None, -np.inf)
        for lr in LRS:
            p = snomd_perrow(X, y, wts, lr, predictable)
            preds[(predictable, lr)] = p
            r2 = agg_r2(y, p, wts)
            flag = ""
            if np.isfinite(r2) and r2 > -1.0 and r2 > best[1]:
                best = (lr, r2)
            print(f"    lr={lr:<6g} R2={r2:+.4f}{flag}")
        lr_star, r2_star = best
        se, lo, hi = block_bootstrap(y, preds[(predictable, lr_star)], wts, block_len,
                                     np.random.default_rng(0))
        edge = "boundary" if lr_star in (LRS[0], LRS[-1]) else "interior"
        print(f"    -> tuned lr*={lr_star:g}  R2={r2_star:+.4f} +-{se:.4f} "
              f"[{lo:+.4f}, {hi:+.4f}] ({edge})")
        rows.append({"tracker": "predictable" if predictable else "post-update",
                     "lr_star": lr_star, "r2": round(r2_star, 4), "se": round(se, 4),
                     "ci_lo": round(lo, 4), "ci_hi": round(hi, 4), "grid": edge})

    # ---- the 2x2 that separates the two factors, paired on identical blocks
    print("\n" + "-" * 96)
    print("  PAIRED contrasts (same rows, same resampled blocks; +- 1.96 SE)")
    print("-" * 96)
    contrasts = [
        ("code path @ lr=2   (predictable - post-update)", (True, 2.0), (False, 2.0)),
        ("code path @ lr=1   (predictable - post-update)", (True, 1.0), (False, 1.0)),
        ("grid @ predictable (lr=2 - lr=1)             ", (True, 2.0), (True, 1.0)),
        ("grid @ post-update (lr=2 - lr=1)             ", (False, 2.0), (False, 1.0)),
        ("TOTAL reported gap (Table 1 - sweep)         ", (False, 2.0), (True, 1.0)),
    ]
    for label, ka, kb in contrasts:
        d, se, lo, hi = paired_bootstrap(y, preds[ka], preds[kb], wts, block_len,
                                         np.random.default_rng(0))
        verdict = "significant" if (lo > 0 or hi < 0) else "inconclusive"
        print(f"    {label}  {d:+.4f} +-{se:.4f}  [{lo:+.4f}, {hi:+.4f}]  {verdict}")
        rows.append({"tracker": "contrast", "lr_star": label.strip(), "r2": round(d, 4),
                     "se": round(se, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                     "grid": verdict})

    # ---- reproduction check against the two published numbers
    print("\n" + "-" * 96)
    r_t1 = agg_r2(y, preds[(False, 2.0)], wts)
    r_sw = agg_r2(y, preds[(True, 1.0)], wts)
    print(f"  reproduction: post-update @ lr=2 = {r_t1:+.4f}  (Table 1 reports +0.2845)")
    print(f"  reproduction: predictable @ lr=1 = {r_sw:+.4f}  (sweep reports  +0.2467)")
    print("-" * 96)

    pl.DataFrame(rows).write_csv(RES / "predictability_decomposition.csv")
    print(f"\n  [saved {(RES / 'predictability_decomposition.csv').relative_to(ROOT)}]")


if __name__ == "__main__":
    run()
