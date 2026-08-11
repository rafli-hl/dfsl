"""Ten-window mean R^2 as a function of learning rate, per method (audit round-6, item 3).

Round-5 showed that a rate tuned to maximize ONE window (window 1) can overfit it and generalize
worse across the other nine (normalized-GD per-step: lr 2->5 raised window-1 R^2 but collapsed the
ten-window mean). Table 2 freezes every method at its window-1-optimal rate, so its rankings are,
in principle, properties of that one tuning window. This script checks whether they are robust:

  * For each method it sweeps the learning rate across ALL ten frozen windows (per-row -- the
    protocol the ranking claims live in), recording each window's R^2.
  * It then reports, per method, the window-1-optimal rate (what Table 2 uses) beside the
    TEN-WINDOW-optimal rate (the rate maximizing the across-window mean), and the resulting mean
    R^2 under each criterion.
  * Finally it prints the method ranking under both criteria. If the ranking is stable "across the
    top of each curve", Table 2's comparison is real; if it flips, the ranking cannot be supported
    and only the stability partition survives.

Usage::

    .venv/Scripts/python.exe scripts/research_lr_curves_windows.py            # full (~40 min)
    .venv/Scripts/python.exe scripts/research_lr_curves_windows.py --smoke
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

from research_baselines import (  # noqa: E402
    adagrad_perrow,
    anchor_perrow,
    blockmed_perrow,
    cm_perrow,
    fixedclip_perrow,
)
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS, _load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

SF = [0.5, 1.0, 2.0, 3.0, 5.0, 8.0]


# method -> (callable(X,y,wts,lr), lr grid).  Non-lr hyperparameters fixed at their Table-2 optima.
def methods():
    return {
        "Normalized-GD":      (lambda X, y, w, lr: anchor_perrow(X, y, w, "normgd", 0.0, lr), SF),
        "SN-OMD EMA (M=5)":   (lambda X, y, w, lr: anchor_perrow(X, y, w, "snomd", 5.0, lr), SF),
        "SN-OMD block (M=5)": (lambda X, y, w, lr: blockmed_perrow(X, y, w, lr, cap=5.0), SF),
        "Fixed-tau clip":     (lambda X, y, w, lr: fixedclip_perrow(X, y, w, 20.0, lr),
                               [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]),
        "AdaGrad-Norm":       (lambda X, y, w, lr: adagrad_perrow(X, y, w, lr),
                               [0.1, 0.3, 1.0, 3.0, 5.0]),
        "Cutkosky-Mehta":     (lambda X, y, w, lr: cm_perrow(X, y, w, 600.0, 0.5, lr), SF),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    rows = 4000 if args.smoke else args.rows
    windows = WINDOWS[:3] if args.smoke else WINDOWS
    meths = methods()
    if args.smoke:
        meths = {k: (fn, g[:3]) for k, (fn, g) in meths.items()}

    print("=" * 100)
    print(f"TEN-WINDOW lr CURVES (per-row) across {len(windows)} frozen windows; rows<= {rows}")
    print("=" * 100)

    # load all windows once
    data = [(_load(lo, hi, rows)) for lo, hi in windows]

    # results[method][lr] = list of per-window R^2
    results: dict[str, dict[float, list[float]]] = {m: {} for m in meths}
    rows_out: list[dict] = []
    for name, (fn, grid) in meths.items():
        print(f"\n########## {name} ##########")
        for lr in grid:
            per_win = []
            for wi, (X, y, wts, starts) in enumerate(data):
                r2 = agg_r2(y, fn(X, y, wts, lr), wts)
                per_win.append(float(r2) if np.isfinite(r2) else float("nan"))
            results[name][lr] = per_win
            m = float(np.nanmean(per_win)); s = float(np.nanstd(per_win))
            rows_out.append({"method": name, "lr": lr, "window1_r2": round(per_win[0], 5),
                             "tenwin_mean": round(m, 5), "tenwin_std": round(s, 5)})
            print(f"  lr={lr:<5g}  window1={per_win[0]:+.4f}   ten-window mean={m:+.4f} +- {s:.4f}")

    pl.DataFrame(rows_out).write_csv(RES / ("lr_curves_windows_smoke.csv" if args.smoke else "lr_curves_windows.csv"))

    # ---- window-1-optimal vs ten-window-optimal rate, per method ----
    print("\n" + "=" * 100)
    print("WINDOW-1-OPTIMAL (Table 2) vs TEN-WINDOW-OPTIMAL learning rate")
    print("=" * 100)
    summary = []
    for name, (fn, grid) in meths.items():
        w1_lr = max(grid, key=lambda lr: results[name][lr][0])
        w1_mean = float(np.nanmean(results[name][w1_lr]))
        tw_lr = max(grid, key=lambda lr: np.nanmean(results[name][lr]))
        tw_mean = float(np.nanmean(results[name][tw_lr]))
        summary.append({"method": name, "w1_lr": w1_lr, "w1_frozen_mean": round(w1_mean, 4),
                        "tenwin_opt_lr": tw_lr, "tenwin_opt_mean": round(tw_mean, 4),
                        "gain_from_reopt": round(tw_mean - w1_mean, 4)})
        print(f"  {name:20s} window1-opt lr={w1_lr:<5g} -> ten-win mean={w1_mean:+.4f}   |   "
              f"ten-win-opt lr={tw_lr:<5g} -> mean={tw_mean:+.4f}   (reopt gain {tw_mean-w1_mean:+.4f})")
    pl.DataFrame(summary).write_csv(RES / ("lr_curves_summary_smoke.csv" if args.smoke else "lr_curves_summary.csv"))

    # ---- ranking under both criteria ----
    print("\n" + "-" * 100)
    print("RANKING (per-row ten-window mean R^2):")
    w1_rank = sorted(summary, key=lambda r: r["w1_frozen_mean"], reverse=True)
    tw_rank = sorted(summary, key=lambda r: r["tenwin_opt_mean"], reverse=True)
    print("  at window-1-optimal (Table 2) rates:")
    for r in w1_rank:
        print(f"     {r['w1_frozen_mean']:+.3f}  {r['method']}")
    print("  at ten-window-optimal rates:")
    for r in tw_rank:
        print(f"     {r['tenwin_opt_mean']:+.3f}  {r['method']}")
    same = [r["method"] for r in w1_rank] == [r["method"] for r in tw_rank]
    print(f"\n  ranking identical under both criteria? {'YES -> Table 2 ranking is robust' if same else 'NO -> re-optimizing reshuffles; see which pairs cross'}")
    print(f"[saved {(RES / 'lr_curves_summary.csv').relative_to(ROOT)}]")


if __name__ == "__main__":
    main()
