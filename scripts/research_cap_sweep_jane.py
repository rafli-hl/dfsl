"""Does the cap have an interior accuracy optimum on Jane -- under REPLICATION? (audit round-6, item 2)

The grid-adequacy appendix (D.11) reports the block tracker's per-row *window-1* R^2 rising to
0.42 at M=10, i.e. a finite cap buys accuracy. Section 4.1 / D.8 say the opposite: "on Jane the
normalized tail is indistinguishable from causal-estimation cost, so the cap sweep has no interior
optimum and the cap-family members are comparable -- the cap buys accuracy only on synthetic
heavy-tail streams, and stability unconditionally." Both cannot stand as written.

Two things the round-5 work makes essential here:
  * D.11's 0.42-at-M=10 is WINDOW-1 IN-SAMPLE, exactly the kind of optimum round-5 showed overfits
    the tuning window. The honest test is the ten-window FROZEN sweep.
  * The mechanism-test claim in 4.1/D.8 was established with the winsorized-EMA tracker (the cap
    family normalized-GD(M->0) / SN-OMD(M=5) / scale-adaptive-OGD(M->inf)). The block-median
    tracker is a DIFFERENT, more stable scale, and its normalized gradient may behave differently.
    So we sweep BOTH trackers.

This sweeps M across the ten disjoint windows at each tracker's FROZEN window-1 rate (EMA lr=2,
block lr=3 -- the Table-2 settings), per-row, and reports mean+-std R^2(M). It answers, per tracker:
does the across-window mean R^2(M) have an interior maximum that beats the M=5 setting and the
uncapped M->inf endpoint, robustly (outside +-1 std)? If yes for the block tracker, 4.1/D.8's
"no accuracy on Jane" is too strong and must be qualified; if the window-1 peak washes out across
windows, D.11's sentence is the one to caveat.

Also (airtight-clip check for section 5): confirm CM's clip is inert even WITH momentum, by running
CM(beta=0.5,lr=2) at tau=600 vs tau=inf across the ten windows -- if identical, the clip does no
work at CM's per-row optimum and the co-lead is momentum + normalization, not clip + normalization.

Usage::

    .venv/Scripts/python.exe scripts/research_cap_sweep_jane.py            # full (~25-35 min)
    .venv/Scripts/python.exe scripts/research_cap_sweep_jane.py --smoke
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

from research_baselines import anchor_perrow, blockmed_perrow, cm_perrow  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS, _load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

M_GRID = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 1e9]   # 1e9 == uncapped scale-adaptive-OGD endpoint
FROZEN_LR = {"EMA": 2.0, "block-median": 3.0}          # Table-2 window-1 rates (per-row)


def run_tracker_M(tracker, X, y, wts, lr, M):
    if tracker == "EMA":
        return anchor_perrow(X, y, wts, "snomd", M, lr)
    return blockmed_perrow(X, y, wts, lr, cap=M)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    rows = 4000 if args.smoke else args.rows
    windows = WINDOWS[:3] if args.smoke else WINDOWS
    m_grid = [2.0, 5.0, 1e9] if args.smoke else M_GRID

    print("=" * 100)
    print(f"JANE CAP SWEEP under replication: per-row R^2 vs M across {len(windows)} frozen windows; rows<= {rows}")
    print("=" * 100)

    # results[tracker][M] = list of per-window R^2
    results: dict[str, dict[float, list[float]]] = {t: {M: [] for M in m_grid} for t in FROZEN_LR}
    cm_clip = {"tau600": [], "tauinf": []}
    rows_out: list[dict] = []
    for wi, (lo, hi) in enumerate(windows):
        X, y, wts, starts = _load(lo, hi, rows)
        print(f"\n[window {wi+1}] date[{lo},{hi})  n={len(y)}")
        for tracker, lr in FROZEN_LR.items():
            line = []
            for M in m_grid:
                r2 = agg_r2(y, run_tracker_M(tracker, X, y, wts, lr, M), wts)
                results[tracker][M].append(float(r2) if np.isfinite(r2) else float("nan"))
                rows_out.append({"window_idx": wi + 1, "window": f"[{lo},{hi})", "tracker": tracker,
                                 "lr": lr, "M": M, "weighted_r2": round(float(r2), 5)})
                line.append(f"M{M:g}={r2:+.3f}")
            print(f"    {tracker:12s} (lr={lr:g})  " + " ".join(line))
        # airtight-clip check: CM(beta0.5,lr2) tau=600 vs tau=inf
        r_t600 = agg_r2(y, cm_perrow(X, y, wts, 600.0, 0.5, 2.0), wts)
        r_tinf = agg_r2(y, cm_perrow(X, y, wts, 1e18, 0.5, 2.0), wts)
        cm_clip["tau600"].append(float(r_t600)); cm_clip["tauinf"].append(float(r_tinf))
        print(f"    CM(b0.5,lr2) clip-check  tau600={r_t600:+.4f}  tauinf={r_tinf:+.4f}  |d|={abs(r_t600-r_tinf):.2e}")

    pl.DataFrame(rows_out).write_csv(RES / ("cap_sweep_jane_smoke.csv" if args.smoke else "cap_sweep_jane.csv"))

    print("\n" + "=" * 100)
    print("ACROSS-WINDOW MEAN +- STD  R^2(M)  (per-row, frozen rate)")
    print("=" * 100)
    for tracker in FROZEN_LR:
        print(f"\n{tracker} (lr={FROZEN_LR[tracker]:g}):")
        means = {}
        for M in m_grid:
            a = np.array(results[tracker][M], dtype=float)
            means[M] = np.nanmean(a)
            print(f"  M={M:<7g} mean={np.nanmean(a):+.4f}  std={np.nanstd(a):.4f}  [{np.nanmin(a):+.4f},{np.nanmax(a):+.4f}]")
        finite_M = [M for M in m_grid if M < 1e8]
        m_star = max(finite_M, key=lambda M: means[M])
        interior = finite_M[0] < m_star < finite_M[-1]
        std_star = np.nanstd(np.array(results[tracker][m_star], dtype=float))
        d_vs5 = means[m_star] - means[5.0]
        d_vs_inf = means[m_star] - means[1e9]
        print(f"  -> argmax finite-M = {m_star:g} ({'INTERIOR' if interior else 'BOUNDARY'});  "
              f"best-vs-M5 = {d_vs5:+.4f};  best-vs-uncapped = {d_vs_inf:+.4f};  std@best={std_star:.4f}")
        robust = interior and d_vs5 > std_star and d_vs_inf > std_star
        print(f"     interior cap optimum that BEATS M=5 and uncapped beyond +-1std across windows? "
              f"{'YES -> cap buys accuracy on Jane (this tracker)' if robust else 'NO -> flat/within-noise; cap mainly stability'}")

    print("\n" + "-" * 100)
    ct600 = np.array(cm_clip["tau600"]); ctinf = np.array(cm_clip["tauinf"])
    print(f"CM airtight-clip check (beta=0.5, lr=2): max|R2(tau=600) - R2(tau=inf)| = {np.nanmax(np.abs(ct600-ctinf)):.2e}  "
          f"({'clip INERT even with momentum -> co-lead is momentum+normalization' if np.nanmax(np.abs(ct600-ctinf)) < 1e-3 else 'clip DOES bind at beta=0.5'})")
    print(f"[saved {(RES / 'cap_sweep_jane.csv').relative_to(ROOT)}]")


if __name__ == "__main__":
    main()
