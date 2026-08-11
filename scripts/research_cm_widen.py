"""Locate Cutkosky--Mehta's TRUE window-1 optimum by extending the grid past its boundary.

The round-4 CM tune put the per-row optimum at tau=300 (the max of {5,20,50,100,300}) and the
per-step optimum at lr=5 (the max of {0.02..5}) --- both on grid boundaries. Per the round-5
grid-adequacy check, a boundary optimum means the reported number may be a grid artifact. This
script extends tau up to 3000 and lr up to 20 (beta in {0,0.5}, the low-momentum regime CM
actually operates in) on WINDOW 1 only, both protocols, and reports the tuning curve so the
optimum can be confirmed interior --- or the wider optimum adopted and CM re-run.

Usage::

    .venv/Scripts/python.exe scripts/research_cm_widen.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_baselines import cm_batched, cm_perrow  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS, _load  # noqa: E402

# extended past the round-4 boundaries (tau_max was 300, lr_max was 5)
TAUS = [50.0, 100.0, 300.0, 600.0, 1000.0, 3000.0]
LRS = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
BETAS = [0.0, 0.5]


def _run(X, y, wts, starts, protocol, tau, beta, lr):
    if protocol == "per-step":
        return cm_batched(X, y, wts, starts, tau, beta, lr)
    return cm_perrow(X, y, wts, tau, beta, lr)


def main() -> None:
    lo, hi = WINDOWS[0]
    X, y, wts, starts = _load(lo, hi, 150000)
    print("=" * 92)
    print(f"CM WIDENED window-1 sweep date[{lo},{hi})  n={len(y)}  "
          f"tau<= {TAUS[-1]:g}, lr<= {LRS[-1]:g}")
    print("=" * 92)
    for protocol in ["per-row", "per-step"]:
        print(f"\n########## {protocol} ##########")
        best = (-np.inf, None)
        for beta in BETAS:
            for tau in TAUS:
                row = []
                for lr in LRS:
                    r2 = agg_r2(y, _run(X, y, wts, starts, protocol, tau, beta, lr), wts)
                    row.append(r2)
                    if np.isfinite(r2) and r2 > best[0]:
                        best = (r2, {"tau": tau, "beta": beta, "lr": lr})
                print(f"  beta={beta:<4g} tau={tau:<6g} " +
                      " ".join(f"lr{lr:g}:{r2:+.3f}" for lr, r2 in zip(LRS, row)))
        b = best[1]
        ti, li = TAUS.index(b["tau"]), LRS.index(b["lr"])
        tstat = "interior" if 0 < ti < len(TAUS) - 1 else "BOUNDARY"
        lstat = "interior" if 0 < li < len(LRS) - 1 else "BOUNDARY"
        print(f"  --> optimum R2={best[0]:+.4f} at tau={b['tau']:g}[{tstat}] "
              f"beta={b['beta']:g} lr={b['lr']:g}[{lstat}]")


if __name__ == "__main__":
    main()
