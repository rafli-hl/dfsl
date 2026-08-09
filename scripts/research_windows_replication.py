"""Replication across ten disjoint time windows with hyperparameters FROZEN from
window 1 -- the experiment the audit (item 1) says decides the paper.

Table 2 (``research_baselines.py``) is measured on a single 150k-row slice of
date[0,120), with every method tuned in-sample on that slice. The audit's central
objection is that the paper's thesis -- *the stream is strongly regime-dependent* --
makes a single contiguous window close to self-refuting: a claim about regime
dependence must show its results are not themselves regime-dependent.

This script answers that directly:

  1. Tune every Table-2 method on WINDOW 1 (date[0,120)) exactly as Table 2 does.
  2. FREEZE those hyperparameters and run every method, unchanged, on nine further
     disjoint windows spanning the full 1,699-day record.
  3. Report the across-window distribution of each method's weighted R^2 and its
     divergence flag, and whether the *ranking* among methods is stable or flips.

If the ranking is stable and SN-OMD stays in the bounded scale-free pack across all
windows, the "none dominates / bounded scale-free is what matters" claim replicates.
If it flips or SN-OMD diverges on a frozen lr in a turbulent window, that is a real
finding and must be reported as such.

Methods (identical to Table 2): OGD, normalized-GD (M->0), scale-adaptive OGD
(M->inf), SN-OMD (M=5), fixed-tau clip, AdaGrad-Norm.

Usage::

    python scripts/research_windows_replication.py                 # full run (~1-2 h)
    python scripts/research_windows_replication.py --smoke          # fast sanity check
    python scripts/research_windows_replication.py --rows 80000     # cheaper full run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_baselines import (  # noqa: E402  (validated harnesses)
    adagrad_batched,
    adagrad_perrow,
    anchor_batched,
    anchor_perrow,
    fixedclip_batched,
    fixedclip_perrow,
)
from research_batched_check import group_boundaries  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

# Ten disjoint ~120-day windows spanning the full 1,699-day record, with 30-day
# gaps so no window bleeds into the next. Window 1 is date[0,120), the exact slice
# Table 2 is reported on.
WINDOWS = [
    (0, 120), (150, 270), (300, 420), (450, 570), (600, 720),
    (750, 870), (900, 1020), (1050, 1170), (1200, 1320), (1350, 1470),
]

# Per-method tuning grids (window 1 only). Scale-free methods tolerate order-1 rates;
# OGD is fragile and tuned over a small-rate grid (it diverges above ~1e-2).
LRS_SF = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
LRS_OGD = [1e-3, 2e-3, 5e-3, 1e-2, 2e-2]
LRS_ADAGRAD = [0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0]
TAUS = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 300.0]

DIVERGED_R2 = -1.0  # any r2 <= this (or non-finite) is treated as divergence


def _peak_rolling_loss(y, preds, wts, window=2000):
    x = wts * (preds - y) ** 2
    x = np.where(np.isfinite(x), np.minimum(x, 1e300), 1e300)
    w = max(1, min(window, x.size))
    return float(np.max(np.convolve(x, np.ones(w) / w, mode="valid")))


def _diverged(y, preds, wts):
    r2 = agg_r2(y, preds, wts)
    return (not np.isfinite(r2)) or r2 <= DIVERGED_R2 or _peak_rolling_loss(y, preds, wts) > 50.0


def _run_method(name, setting, X, y, wts, starts, protocol):
    """Run one method at a fixed setting; return prediction vector."""
    batched = protocol == "per-step"
    extra = (starts,) if batched else ()
    lr = setting["lr"]
    if name == "OGD":
        fn = anchor_batched if batched else anchor_perrow
        return fn(X, y, wts, *extra, "ogd", 0.0, lr)
    if name == "Normalized-GD":
        fn = anchor_batched if batched else anchor_perrow
        return fn(X, y, wts, *extra, "normgd", 0.0, lr)
    if name == "Scale-adaptive OGD":
        fn = anchor_batched if batched else anchor_perrow
        return fn(X, y, wts, *extra, "snomd", 1e9, lr)
    if name == "SN-OMD (M=5)":
        fn = anchor_batched if batched else anchor_perrow
        return fn(X, y, wts, *extra, "snomd", 5.0, lr)
    if name == "fixed-tau clip":
        fn = fixedclip_batched if batched else fixedclip_perrow
        return fn(X, y, wts, *extra, setting["tau"], lr)
    if name == "AdaGrad-Norm":
        fn = adagrad_batched if batched else adagrad_perrow
        return fn(X, y, wts, *extra, lr)
    raise ValueError(name)


def _grid(name):
    if name == "OGD":
        return [{"lr": lr} for lr in LRS_OGD]
    if name == "AdaGrad-Norm":
        return [{"lr": lr} for lr in LRS_ADAGRAD]
    if name == "fixed-tau clip":
        return [{"lr": lr, "tau": tau} for lr in LRS_SF for tau in TAUS]
    return [{"lr": lr} for lr in LRS_SF]


METHODS = [
    "OGD", "Normalized-GD", "Scale-adaptive OGD",
    "SN-OMD (M=5)", "fixed-tau clip", "AdaGrad-Norm",
]


def _load(lo, hi, rows):
    ds = JaneStreetDataset(date_range=(lo, hi), max_rows=rows, standardize=True)
    return ds.X, ds.y, ds.weights, group_boundaries(ds.meta)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true", help="tiny/fast validation run")
    ap.add_argument("--n-windows", type=int, default=len(WINDOWS))
    args = ap.parse_args()

    rows = args.rows
    windows = WINDOWS[: args.n_windows]
    protocols = ["per-row", "per-step"]
    if args.smoke:
        rows = 4000
        windows = WINDOWS[:3]
        global LRS_SF, LRS_OGD, LRS_ADAGRAD, TAUS
        LRS_SF = [0.1, 0.5, 2.0]
        LRS_OGD = [2e-3, 1e-2]
        LRS_ADAGRAD = [0.03, 0.3]
        TAUS = [5.0, 20.0]
        print(">>> SMOKE MODE: rows=4000, 3 windows, coarse grids <<<")

    print("=" * 96)
    print(f"WINDOW REPLICATION  --  freeze hyperparameters from window {windows[0]}, "
          f"apply to {len(windows)} disjoint windows; rows<= {rows}")
    print("=" * 96)

    frozen: dict[tuple[str, str], dict] = {}
    all_rows: list[dict] = []

    for protocol in protocols:
        print(f"\n########## PROTOCOL: {protocol} ##########")

        # ---- 1. tune on window 1 ----
        lo, hi = windows[0]
        X, y, wts, starts = _load(lo, hi, rows)
        print(f"\n[tune] window date[{lo},{hi})  n={len(y)}")
        for name in METHODS:
            best = (None, -np.inf, None)
            for setting in _grid(name):
                p = _run_method(name, setting, X, y, wts, starts, protocol)
                r2 = agg_r2(y, p, wts)
                if np.isfinite(r2) and r2 > best[1]:
                    best = (setting, r2, p)
            frozen[(protocol, name)] = best[0] or {"lr": LRS_SF[0]}
            tune_str = ",".join(f"{k}={v:g}" for k, v in frozen[(protocol, name)].items())
            print(f"  {name:22s} frozen: {tune_str:20s} window1 R2={best[1]:+.4f}")

        # ---- 2. apply frozen settings to every window ----
        for wi, (lo, hi) in enumerate(windows):
            if wi == 0:
                X_w, y_w, wts_w, starts_w = X, y, wts, starts
            else:
                X_w, y_w, wts_w, starts_w = _load(lo, hi, rows)
            print(f"\n[eval] window {wi+1} date[{lo},{hi})  n={len(y_w)}")
            for name in METHODS:
                setting = frozen[(protocol, name)]
                p = _run_method(name, setting, X_w, y_w, wts_w, starts_w, protocol)
                r2 = agg_r2(y_w, p, wts_w)
                div = _diverged(y_w, p, wts_w)
                all_rows.append({
                    "protocol": protocol, "window": f"[{lo},{hi})", "window_idx": wi + 1,
                    "method": name, "setting": ",".join(f"{k}={v:g}" for k, v in setting.items()),
                    "weighted_r2": round(float(r2) if np.isfinite(r2) else float("nan"), 5),
                    "diverged": bool(div),
                })
                flag = "  <-- DIVERGED" if div else ""
                print(f"  {name:22s} R2={r2:+.4f}{flag}")

    df = pl.DataFrame(all_rows)
    out = RES / ("windows_replication_smoke.csv" if args.smoke else "windows_replication.csv")
    df.write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    # ---- 3. across-window summary + ranking stability ----
    print("\n" + "=" * 96)
    print("ACROSS-WINDOW SUMMARY (mean +/- std weighted R^2 at frozen settings)")
    print("=" * 96)
    sumrows: list[dict] = []
    for protocol in protocols:
        print(f"\n{protocol}:")
        sub = df.filter(pl.col("protocol") == protocol)
        agg = (
            sub.group_by("method")
            .agg(
                pl.col("weighted_r2").mean().alias("mean"),
                pl.col("weighted_r2").std().alias("std"),
                pl.col("weighted_r2").min().alias("min"),
                pl.col("weighted_r2").max().alias("max"),
                pl.col("diverged").sum().alias("n_diverged"),
            )
            .sort("mean", descending=True)
        )
        for r in agg.iter_rows(named=True):
            print(f"  {r['method']:22s} mean={r['mean']:+.4f}  std={r['std'] or 0:.4f}  "
                  f"[{r['min']:+.4f},{r['max']:+.4f}]  diverged={r['n_diverged']}/{len(windows)}")
            sumrows.append({"protocol": protocol, **r})

        # top-1 stability: how often is each method the per-window winner?
        wins: dict[str, int] = {m: 0 for m in METHODS}
        for wi in range(1, len(windows) + 1):
            wsub = sub.filter((pl.col("window_idx") == wi) & (~pl.col("diverged")))
            if wsub.height:
                top = wsub.sort("weighted_r2", descending=True).row(0, named=True)
                wins[top["method"]] += 1
        win_str = ", ".join(f"{m.split(' ')[0]}:{c}" for m, c in wins.items() if c)
        print(f"  per-window top-1 count: {win_str}")

    pl.DataFrame(sumrows).write_csv(
        RES / ("windows_replication_summary_smoke.csv" if args.smoke else "windows_replication_summary.csv")
    )
    print("\nHONEST READING: the paper's 'none dominates / bounded scale-free is what matters'")
    print("claim replicates iff the bounded scale-free methods stay in a tight pack with 0")
    print("divergences across windows and the top-1 winner varies among them (no single method")
    print("dominates). A frozen-lr divergence, or OGD/clip overtaking the pack, is a real finding.")


if __name__ == "__main__":
    main()
