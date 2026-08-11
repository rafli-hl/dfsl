"""Cutkosky & Mehta (2021) as a live baseline across the ten frozen windows (audit round-3).

The audit names Cutkosky--Mehta as the closest prior method and the single most predictable
rebuttal question, because the paper cites it as "normalize and clip" and had not run it.
This runs their high-probability method---normalized SGD with momentum on *clipped* gradients
(``cm_perrow``/``cm_batched`` in ``research_baselines.py``)---on exactly the ten disjoint
windows of ``research_windows_replication.py``, tuned on window 1 over (lr, tau, beta) then
FROZEN, both protocols, with the same divergence criterion. The output is a Cutkosky--Mehta
row for Table 2.

The distinction the paper claims is concrete: CM clips at a *fixed* tau and steps in the fully
*normalized* momentum direction; SN-OMD divides by a *predictable tracked scale* and *caps*
(not normalizes) the result. This measures whether that distinction buys anything on a
drifting-scale stream.

Usage::

    .venv/Scripts/python.exe scripts/research_windows_cm.py            # full (~10-20 min)
    .venv/Scripts/python.exe scripts/research_windows_cm.py --smoke
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

from research_baselines import cm_batched, cm_perrow  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS, _diverged, _load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

# Grid widened after the round-4 tuning-curve diagnostic (research_cm_diag.py): the momentum
# beta must be tuned down toward 0 (where CM degenerates to clip+normalize) --- heavy momentum
# (beta>=0.9) collapses under batched gradients, so the earlier beta in {0.9, 0.99} grid missed
# CM's operating regime and produced a misconfigured per-step cell.
# tau/lr ceilings raised after the round-5 grid-adequacy check (research_cm_widen.py): the
# round-4 optima sat at tau=300 and lr=5 (both grid maxima). The widened window-1 sweep shows
# CM's R^2 is FLAT in tau for tau>=100 (tau=300 was a benign plateau, not a cutoff) and peaks
# at lr=5 per-step, declining by lr=8 --- so tau=600 and lr=8 make both optima interior and CM's
# numbers are essentially unchanged (per-row 0.3636->0.3652, per-step 0.3712).
LRS = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 8.0]
TAUS = [5.0, 20.0, 50.0, 100.0, 300.0, 600.0]
BETAS = [0.0, 0.5, 0.9, 0.99]


def _run(X, y, wts, starts, protocol, tau, beta, lr):
    if protocol == "per-step":
        return cm_batched(X, y, wts, starts, tau, beta, lr)
    return cm_perrow(X, y, wts, tau, beta, lr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    rows = 4000 if args.smoke else args.rows
    windows = WINDOWS[:3] if args.smoke else WINDOWS
    lrs = [0.1, 0.5, 2.0] if args.smoke else LRS
    taus = [20.0, 300.0] if args.smoke else TAUS
    betas = [0.0, 0.9] if args.smoke else BETAS

    print("=" * 92)
    print(f"CUTKOSKY-MEHTA (2021) across {len(windows)} frozen windows; rows<= {rows}")
    print("=" * 92)

    rows_out: list[dict] = []
    for protocol in ["per-row", "per-step"]:
        print(f"\n########## {protocol} ##########")
        lo, hi = windows[0]
        X, y, wts, starts = _load(lo, hi, rows)

        # tune (lr, tau, beta) on window 1
        best = (-np.inf, None)
        for tau in taus:
            for beta in betas:
                for lr in lrs:
                    r2 = agg_r2(y, _run(X, y, wts, starts, protocol, tau, beta, lr), wts)
                    if np.isfinite(r2) and r2 > best[0]:
                        best = (r2, {"tau": tau, "beta": beta, "lr": lr})
        frozen = best[1]
        print(f"  [tune] Cutkosky-Mehta frozen tau={frozen['tau']:g} beta={frozen['beta']:g} "
              f"lr={frozen['lr']:g}  window1 R2={best[0]:+.4f}")

        # freeze, evaluate on every window
        for wi, (lo, hi) in enumerate(windows):
            if wi == 0:
                Xw, yw, ww, sw = X, y, wts, starts
            else:
                Xw, yw, ww, sw = _load(lo, hi, rows)
            p = _run(Xw, yw, ww, sw, protocol, frozen["tau"], frozen["beta"], frozen["lr"])
            r2 = agg_r2(yw, p, ww)
            div = _diverged(yw, p, ww)
            rows_out.append({"protocol": protocol, "window": f"[{lo},{hi})", "window_idx": wi + 1,
                             "method": "Cutkosky-Mehta",
                             "setting": f"tau={frozen['tau']:g},beta={frozen['beta']:g},lr={frozen['lr']:g}",
                             "weighted_r2": round(float(r2) if np.isfinite(r2) else float("nan"), 5),
                             "diverged": bool(div)})
            print(f"  window {wi+1} [{lo},{hi})  R2={r2:+.4f}{'  <-- DIVERGED' if div else ''}")

    df = pl.DataFrame(rows_out)
    out = RES / ("windows_cm_smoke.csv" if args.smoke else "windows_cm.csv")
    df.write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    print("\n" + "=" * 92)
    print("ACROSS-WINDOW SUMMARY (mean +/- std weighted R^2; divergences)")
    print("=" * 92)
    for protocol in ["per-row", "per-step"]:
        s = df.filter(pl.col("protocol") == protocol)
        r2 = s["weighted_r2"]
        print(f"  {protocol:9s} Cutkosky-Mehta  mean={r2.mean():+.4f}  std={r2.std() or 0:.4f}  "
              f"[{r2.min():+.4f},{r2.max():+.4f}]  diverged={int(s['diverged'].sum())}/{len(windows)}")
    print("\nREADING: compare to Table 2's bounded scale-free pack. CM clips+normalizes but does")
    print("not track a predictable scale; whether it matches SN-OMD/normalized-GD under frozen")
    print("hyperparameters across regimes is the closest-prior question the audit flagged.")


if __name__ == "__main__":
    main()
