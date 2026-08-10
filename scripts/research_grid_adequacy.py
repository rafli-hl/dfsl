"""Grid-adequacy diagnostic: is every Table-2 method's window-1 optimum INTERIOR? (audit round-5)

The round-4 correction exposed a general risk: the misconfigured Cutkosky--Mehta cell came
from a tuning grid whose optimum sat on a boundary (beta in {0.9,0.99}, with the true optimum
at beta->0, off the edge). If any *other* Table-2 method was tuned on a grid whose window-1
argmax lies on an endpoint, its reported number is a grid artifact too, and the comparison is
not defensible until shown otherwise.

This script sweeps each method's FULL window-1 grid (the exact grids used to tune Table 2 /
the replication / the CM baseline), both protocols, and reports for every tuned axis whether
the argmax is strictly interior (not at the min or max of the grid). A method is "grid-adequate"
on a protocol iff every tuned axis's optimum is interior. Single-value axes (SN-OMD's cap M,
decay, winsorization --- fixed a priori, see Limitations) are reported as fixed, and for the two
SN-OMD variants we additionally sweep the cap M at the tuned lr to show the fixed M=5 is not on
a cliff (neutralizing the "SN-OMD is the under-searched method" asymmetry).

Window 1 == date[0,120), 150k rows, exactly the slice Table 2 is tuned on.

Usage::

    .venv/Scripts/python.exe scripts/research_grid_adequacy.py            # full (~10-20 min)
    .venv/Scripts/python.exe scripts/research_grid_adequacy.py --smoke
"""

from __future__ import annotations

import argparse
import sys
from itertools import product
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_baselines import (  # noqa: E402
    adagrad_batched,
    adagrad_perrow,
    anchor_batched,
    anchor_perrow,
    blockmed_batched,
    blockmed_perrow,
    cm_batched,
    cm_perrow,
    fixedclip_batched,
    fixedclip_perrow,
)
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS, _load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

# --- grids, copied verbatim from the scripts that tune each Table-2 number (widened round-5) ---
LRS_SF = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0]  # replication.py scale-free
LRS_OGD = [1e-3, 2e-3, 5e-3, 1e-2, 2e-2]                 # replication.py OGD (diverges above ~1e-2)
LRS_ADAGRAD = [0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 5.0]   # replication.py AdaGrad
TAUS_CLIP = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 300.0]  # replication.py fixed-tau
LRS_BLOCK = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0]   # windows_tracker.py block/EMA
LRS_CM = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 8.0]     # windows_cm.py
TAUS_CM = [5.0, 20.0, 50.0, 100.0, 300.0, 600.0]
BETAS_CM = [0.0, 0.5, 0.9, 0.99]
M_SWEEP = [2.0, 3.0, 5.0, 10.0, 20.0]                   # cap robustness for the two SN-OMD rows


def run_method(name, params, X, y, wts, starts, protocol):
    """Prediction vector for `name` at hyperparameters `params`, under `protocol`."""
    batched = protocol == "per-step"
    lr = params["lr"]
    cap = params.get("M", 5.0)
    if name == "OGD":
        return anchor_batched(X, y, wts, starts, "ogd", 0.0, lr) if batched \
            else anchor_perrow(X, y, wts, "ogd", 0.0, lr)
    if name == "Normalized-GD":
        return anchor_batched(X, y, wts, starts, "normgd", 0.0, lr) if batched \
            else anchor_perrow(X, y, wts, "normgd", 0.0, lr)
    if name == "Scale-adaptive OGD":
        return anchor_batched(X, y, wts, starts, "snomd", 1e9, lr) if batched \
            else anchor_perrow(X, y, wts, "snomd", 1e9, lr)
    if name == "SN-OMD (M=5)":
        return anchor_batched(X, y, wts, starts, "snomd", cap, lr) if batched \
            else anchor_perrow(X, y, wts, "snomd", cap, lr)
    if name == "SN-OMD + block":
        return blockmed_batched(X, y, wts, starts, lr, cap=cap) if batched \
            else blockmed_perrow(X, y, wts, lr, cap=cap)
    if name == "fixed-tau clip":
        return fixedclip_batched(X, y, wts, starts, params["tau"], lr) if batched \
            else fixedclip_perrow(X, y, wts, params["tau"], lr)
    if name == "AdaGrad-Norm":
        return adagrad_batched(X, y, wts, starts, lr) if batched \
            else adagrad_perrow(X, y, wts, lr)
    if name == "Cutkosky-Mehta":
        return cm_batched(X, y, wts, starts, params["tau"], params["beta"], lr) if batched \
            else cm_perrow(X, y, wts, params["tau"], params["beta"], lr)
    raise ValueError(name)


# method -> {axis: grid}. Order fixes the product order; every axis here is a *tuned* axis.
def method_axes(smoke):
    lrs_sf = [0.1, 0.5, 2.0] if smoke else LRS_SF
    return {
        "OGD": {"lr": [2e-3, 1e-2] if smoke else LRS_OGD},
        "Normalized-GD": {"lr": lrs_sf},
        "Scale-adaptive OGD": {"lr": lrs_sf},
        "SN-OMD (M=5)": {"lr": lrs_sf},
        "SN-OMD + block": {"lr": [0.1, 0.5, 2.0] if smoke else LRS_BLOCK},
        "fixed-tau clip": {"lr": lrs_sf, "tau": [20.0, 300.0] if smoke else TAUS_CLIP},
        "AdaGrad-Norm": {"lr": [0.03, 0.3] if smoke else LRS_ADAGRAD},
        "Cutkosky-Mehta": {"lr": [0.1, 0.5, 2.0] if smoke else LRS_CM,
                           "tau": [20.0, 300.0] if smoke else TAUS_CM,
                           "beta": [0.0, 0.9] if smoke else BETAS_CM},
    }


def _interior(values, best):
    if len(values) <= 1:
        return "fixed"
    i = values.index(best)
    return "interior" if 0 < i < len(values) - 1 else "boundary"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    rows = 4000 if args.smoke else args.rows

    lo, hi = WINDOWS[0]
    X, y, wts, starts = _load(lo, hi, rows)
    axes_by_method = method_axes(args.smoke)

    print("=" * 100)
    print(f"GRID-ADEQUACY on window 1 date[{lo},{hi})  n={len(y)}  rows<= {rows}")
    print("Is each Table-2 method's window-1 optimum INTERIOR to its tuning grid?")
    print("=" * 100)

    rows_out: list[dict] = []
    all_interior = True
    for protocol in ["per-row", "per-step"]:
        print(f"\n########## {protocol} ##########")
        for name, axes in axes_by_method.items():
            keys = list(axes)
            best = (-np.inf, None)
            for combo in product(*(axes[k] for k in keys)):
                params = dict(zip(keys, combo))
                r2 = agg_r2(y, run_method(name, params, X, y, wts, starts, protocol), wts)
                if np.isfinite(r2) and r2 > best[0]:
                    best = (r2, params)
            argmax = best[1] or {k: axes[k][0] for k in keys}
            statuses = {k: _interior(axes[k], argmax[k]) for k in keys}
            method_ok = all(s != "boundary" for s in statuses.values())
            all_interior &= method_ok
            desc = ", ".join(
                f"{k}={argmax[k]:g}[{statuses[k]}: {axes[k][0]:g}..{axes[k][-1]:g}]" for k in keys)
            print(f"  {name:20s} R2={best[0]:+.4f}  {desc}   -> "
                  f"{'OK' if method_ok else 'BOUNDARY!'}")
            for k in keys:
                rows_out.append({"protocol": protocol, "method": name, "axis": k,
                                 "argmax": float(argmax[k]), "grid_lo": float(axes[k][0]),
                                 "grid_hi": float(axes[k][-1]), "n_points": len(axes[k]),
                                 "status": statuses[k], "window1_r2": round(float(best[0]), 5)})

    # --- cap-M robustness for the two SN-OMD rows (M is fixed a priori; show it isn't a cliff) ---
    print("\n########## SN-OMD cap-M robustness at the tuned lr (window 1) ##########")
    for name in ["SN-OMD (M=5)", "SN-OMD + block"]:
        for protocol in ["per-row", "per-step"]:
            lr_grid = axes_by_method[name]["lr"]
            # find best lr at M=5, then sweep M there
            best = (-np.inf, None)
            for lr in lr_grid:
                r2 = agg_r2(y, run_method(name, {"lr": lr, "M": 5.0}, X, y, wts, starts, protocol), wts)
                if np.isfinite(r2) and r2 > best[0]:
                    best = (r2, lr)
            lr_star = best[1]
            ms = [2.0, 5.0, 20.0] if args.smoke else M_SWEEP
            curve = {}
            for M in ms:
                curve[M] = agg_r2(y, run_method(name, {"lr": lr_star, "M": M}, X, y, wts, starts, protocol), wts)
            m_star = max(curve, key=curve.get)
            status = _interior(ms, m_star)
            spread = max(curve.values()) - min(curve.values())
            print(f"  {name:18s} {protocol:8s} lr*={lr_star:g}  "
                  f"M-curve " + " ".join(f"{M:g}:{curve[M]:+.3f}" for M in ms)
                  + f"   argmaxM={m_star:g}[{status}] spread={spread:.3f}")
            for M in ms:
                rows_out.append({"protocol": protocol, "method": f"{name} (M-sweep)",
                                 "axis": "M", "argmax": float(m_star), "grid_lo": float(ms[0]),
                                 "grid_hi": float(ms[-1]), "n_points": len(ms), "status": status,
                                 "window1_r2": round(float(curve[M]), 5)})

    out = RES / ("grid_adequacy_smoke.csv" if args.smoke else "grid_adequacy.csv")
    pl.DataFrame(rows_out).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")
    print("\nVERDICT:", "every tuned axis's window-1 optimum is INTERIOR --- the grid-adequacy"
          if all_interior else "SOME axis optimum is on a BOUNDARY --- widen that grid before reporting")
    print("objection the CM mis-grid raised is closed for the whole table."
          if all_interior else "(this is the next CM; fix it).")


if __name__ == "__main__":
    main()
