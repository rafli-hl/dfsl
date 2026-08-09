"""Diagnostic: the window-1 tuning curve for Cutkosky-Mehta, both protocols (audit round-4).

The round-4 audit flags CM's per-step cell (0.01) as a likely misconfiguration signature,
since normalize-only (normalized-GD, 0.29) and clip-only (fixed-tau, 0.20) each score >=0.20
per-step. This sweeps CM's full (lr, tau, beta) grid on window 1 and prints the best R^2 per
(tau, beta) so the tuning curve is visible --- in particular whether small/zero momentum
(beta->0, i.e. clip+normalize) recovers the per-step pack, which would show the earlier
beta in {0.9, 0.99} grid simply missed CM's operating regime under batched gradients.

Usage::  .venv/Scripts/python.exe scripts/research_cm_diag.py
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
from research_windows_replication import _load  # noqa: E402

LRS = [0.02, 0.1, 0.5, 1.0, 2.0, 5.0]
TAUS = [5.0, 20.0, 50.0, 100.0, 300.0]
BETAS = [0.0, 0.5, 0.9, 0.99]


def run(protocol, X, y, wts, starts):
    print(f"\n########## {protocol}: best R^2 over lr per (tau, beta) ##########")
    header = "tau \\ beta  " + "  ".join(f"{b:>7g}" for b in BETAS)
    print(header)
    overall = (-np.inf, None)
    for tau in TAUS:
        cells = []
        for beta in BETAS:
            best = -np.inf
            for lr in LRS:
                p = (cm_batched(X, y, wts, starts, tau, beta, lr) if protocol == "per-step"
                     else cm_perrow(X, y, wts, tau, beta, lr))
                r2 = agg_r2(y, p, wts)
                if np.isfinite(r2) and r2 > best:
                    best = r2
                if np.isfinite(r2) and r2 > overall[0]:
                    overall = (r2, {"tau": tau, "beta": beta, "lr": lr})
            cells.append(best)
        print(f"  {tau:>7g}   " + "  ".join(f"{c:>7.3f}" for c in cells))
    print(f"  --> best {protocol}: R^2={overall[0]:+.4f} at {overall[1]}")
    return overall


def main() -> None:
    X, y, wts, starts = _load(0, 120, 150000)
    print("=" * 80)
    print(f"CM WINDOW-1 TUNING CURVE  (n={len(y)}, {len(starts)} timesteps)")
    print("=" * 80)
    run("per-row", X, y, wts, starts)
    run("per-step", X, y, wts, starts)


if __name__ == "__main__":
    main()
