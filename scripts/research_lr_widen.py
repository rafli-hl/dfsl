"""Extend the lr grid past its ceiling for every method (window 1) --- climbing or plateaued?

The round-5 grid-adequacy check found most scale-free methods put their window-1 lr optimum at
the TOP of their grid (lr=2 for LRS_SF, 3 for AdaGrad, 5 for CM). A boundary argmax is only a
problem if R^2 is still *climbing* there; if the curve has plateaued, the ceiling is benign.
This sweeps lr high at each method's known-good second axis and prints the tuning curve so the
shape is visible: a still-rising curve means the grid cut off the optimum and Table 2 must be
re-tuned on a wider grid; a flat/declining curve past lr=2 means the reported number stands.

Window 1 == date[0,120), 150k rows. CM is handled by research_cm_widen.py.

Usage::

    .venv/Scripts/python.exe scripts/research_lr_widen.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_grid_adequacy import run_method  # noqa: E402  (shared runner)
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS, _load  # noqa: E402

LRS = [0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0]
# method -> fixed second-axis params (besides lr)
EXTRA = {
    "Normalized-GD": {},
    "SN-OMD (M=5)": {},                 # M=5 default in run_method
    "SN-OMD + block": {},               # M=5 default
    "AdaGrad-Norm": {},
    "fixed-tau clip": {"tau": 20.0},    # its interior tau optimum
}


def main() -> None:
    lo, hi = WINDOWS[0]
    X, y, wts, starts = _load(lo, hi, 150000)
    print("=" * 92)
    print(f"lr-WIDENED window-1 sweep date[{lo},{hi})  n={len(y)}  lr up to {LRS[-1]:g}")
    print("(is the boundary-at-lr=2 optimum still climbing, or plateaued?)")
    print("=" * 92)
    for protocol in ["per-row", "per-step"]:
        print(f"\n########## {protocol} ##########")
        for name, extra in EXTRA.items():
            curve = []
            for lr in LRS:
                p = run_method(name, {"lr": lr, **extra}, X, y, wts, starts, protocol)
                curve.append(agg_r2(y, p, wts))
            i = int(np.nanargmax([c if np.isfinite(c) else -np.inf for c in curve]))
            stat = "interior" if 0 < i < len(LRS) - 1 else "BOUNDARY"
            print(f"  {name:16s} " + " ".join(f"{lr:g}:{c:+.3f}" for lr, c in zip(LRS, curve))
                  + f"   argmax lr={LRS[i]:g} R2={curve[i]:+.3f} [{stat}]")


if __name__ == "__main__":
    main()
