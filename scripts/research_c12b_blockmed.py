"""C12B -- block-median SN-OMD at matched tuning budget.

Registered in ``experiment_matrix.yaml`` (eleventh document) BEFORE execution.

C12 corrected the plain SN-OMD row of ``tab:replication`` but not its sibling,
``SN-OMD + block-median tracker`` — the same method with a different scale tracker, whose cap
is likewise pinned (``blockmed_perrow`` default ``cap=5.0``, tuned over ``lr`` alone: 9
configurations). Adopting C12 without this would place the same method at two different tuning
budgets in adjacent rows.

**The cap is the only thing that changes.** The ``lr`` grid is the tracker script's own,
unchanged, and the block length ``B`` stays pinned — it is a tracker-internal constant, the
analogue of the winsorized EMA's decay and winsorization, which are pinned for the plain row.

Usage::

    python scripts/research_c12b_blockmed.py            # full run (~5 min)
    python scripts/research_c12b_blockmed.py --smoke
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import research_windows_replication as wr  # noqa: E402
from research_baselines import blockmed_batched, blockmed_perrow  # noqa: E402
from research_divergence import diverged as rel_diverged  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research" / "c12b"

# registered design
LRS = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0]      # tracker script's own grid
M_GRID = [0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 100.0]           # reused from C10/Q6 and C12
PUBLISHED_CAP = 5.0
REPRO_TOL = 0.005


def run(X, y, wts, starts, protocol, lr, cap):
    if protocol == "per-step":
        return blockmed_batched(X, y, wts, starts, lr, cap=cap)
    return blockmed_perrow(X, y, wts, lr, cap=cap)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    rows, windows = args.rows, wr.WINDOWS
    global LRS, M_GRID
    if args.smoke:
        rows, windows = 4000, wr.WINDOWS[:3]
        LRS, M_GRID = [0.2, 1.0], [2.0, 5.0]
        print(">>> SMOKE MODE <<<")

    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    lines: list[str] = []

    def log(m=""):
        print(m)
        lines.append(m)

    log("=" * 96)
    log("C12B -- block-median SN-OMD at matched budget (cap is the ONLY change)")
    log(f"grid: lr({len(LRS)}) x M({len(M_GRID)}) = {len(LRS)*len(M_GRID)}  "
        f"vs published lr({len(LRS)}) with cap pinned at {PUBLISHED_CAP:g}")
    log("=" * 96)

    out, frozen, repro = [], {}, {}
    for protocol in ("per-row", "per-step"):
        log(f"\n########## {protocol} ##########")
        lo, hi = windows[0]
        X, y, wts, starts = wr._load(lo, hi, rows)

        # matched-budget selection
        best, best_r2 = None, -np.inf
        for lr in LRS:
            for M in M_GRID:
                r2 = agg_r2(y, run(X, y, wts, starts, protocol, lr, M), wts)
                if np.isfinite(r2) and r2 > best_r2:
                    best, best_r2 = {"lr": lr, "M": M}, float(r2)
        frozen[protocol] = best
        edge = []
        if best["lr"] in (LRS[0], LRS[-1]):
            edge.append(f"lr={best['lr']:g} at edge")
        if best["M"] in (M_GRID[0], M_GRID[-1]):
            edge.append(f"M={best['M']:g} at edge <-- collapsed toward an endpoint")
        log(f"  matched   frozen lr={best['lr']:g}, M={best['M']:g}   window1 R2={best_r2:+.4f}"
            + (f"   <-- {'; '.join(edge)}" if edge else ""))

        # published selection, for the reproduction gate
        pbest, pbest_r2 = None, -np.inf
        for lr in LRS:
            r2 = agg_r2(y, run(X, y, wts, starts, protocol, lr, PUBLISHED_CAP), wts)
            if np.isfinite(r2) and r2 > pbest_r2:
                pbest, pbest_r2 = {"lr": lr, "M": PUBLISHED_CAP}, float(r2)
        log(f"  published frozen lr={pbest['lr']:g}, M={PUBLISHED_CAP:g}   "
            f"window1 R2={pbest_r2:+.4f}")

        for arm, st in (("matched", best), ("published", pbest)):
            for wi, (lo, hi) in enumerate(windows):
                Xw, yw, ww, sw = (X, y, wts, starts) if wi == 0 else wr._load(lo, hi, rows)
                p = run(Xw, yw, ww, sw, protocol, st["lr"], st["M"])
                r2 = agg_r2(yw, p, ww)
                out.append({"protocol": protocol, "arm": arm, "window_idx": wi + 1,
                            "lr": st["lr"], "M": st["M"],
                            "weighted_r2": round(float(r2) if np.isfinite(r2) else float("nan"), 5),
                            "diverged": bool(wr._diverged(yw, p, ww)),
                            "diverged_rel": bool(rel_diverged(yw, p, ww))})
            log(f"  {arm}: 10 windows done ({time.time()-t0:.0f}s)")

    df = pl.DataFrame(out)
    df.write_csv(RES / ("c12b_blockmed_smoke.csv" if args.smoke else "c12b_blockmed.csv"))

    log("\n" + "=" * 96)
    log("BLOCK-MEDIAN: published (cap pinned) vs matched budget")
    log("=" * 96)
    summ = []
    for protocol in ("per-row", "per-step"):
        log(f"\n{protocol}:")
        log(f"  {'arm':10s} {'setting':16s} {'all-10 mean':>12s} {'std':>7s} {'min':>8s} "
            f"{'div':>6s} {'div_rel':>8s} {'held-out':>10s} {'win1':>8s}")
        for arm in ("published", "matched"):
            d = df.filter((pl.col("protocol") == protocol) & (pl.col("arm") == arm)).sort("window_idx")
            v = d["weighted_r2"].to_numpy()
            rec = {"protocol": protocol, "arm": arm, "lr": d["lr"][0], "M": d["M"][0],
                   "mean": float(np.nanmean(v)), "std": float(np.nanstd(v, ddof=1)),
                   "min": float(np.nanmin(v)), "max": float(np.nanmax(v)),
                   "n_diverged": int(d["diverged"].sum()),
                   "n_diverged_rel": int(d["diverged_rel"].sum()),
                   "heldout_mean": float(np.nanmean(v[1:])), "window1": float(v[0])}
            summ.append(rec)
            log(f"  {arm:10s} lr={rec['lr']:<5g}M={rec['M']:<6g} {rec['mean']:>+12.4f} "
                f"{rec['std']:>7.4f} {rec['min']:>+8.4f} {rec['n_diverged']:>4d}/10 "
                f"{rec['n_diverged_rel']:>6d}/10 {rec['heldout_mean']:>+10.4f} {rec['window1']:>+8.4f}")
    pl.DataFrame(summ).write_csv(
        RES / ("c12b_summary_smoke.csv" if args.smoke else "c12b_summary.csv"))

    # reproduction gate against the published table row (per-row 0.29+-.07, per-step 0.20+-.13)
    log("\n" + "=" * 96)
    log("REPRODUCTION GATE -- published arm vs the manuscript's block-median row")
    log("=" * 96)
    manuscript = {"per-row": (0.29, 0.07), "per-step": (0.20, 0.13)}
    ok_all = True
    if args.smoke:
        log("  skipped in smoke mode: the gate compares against full-run manuscript numbers")
        manuscript = {}
    for protocol, (mm, ms) in manuscript.items():
        r = [x for x in summ if x["protocol"] == protocol and x["arm"] == "published"][0]
        dv = abs(r["mean"] - mm)
        ok = dv <= 0.005 + 0.005  # manuscript is rounded to 2 d.p.
        ok_all &= ok
        repro[protocol] = {"mine": r["mean"], "manuscript": mm, "abs_diff": dv, "ok": bool(ok)}
        log(f"  {protocol:9s} mine={r['mean']:+.4f}  manuscript={mm:+.2f}  diff={dv:.4f}  "
            f"{'OK' if ok else '*** MISMATCH ***'}")

    report = {"M_GRID": M_GRID, "LRS": LRS, "frozen": frozen, "repro": repro,
              "repro_pass": bool(ok_all), "wallclock_sec": round(time.time() - t0, 1)}
    (RES / ("c12b_report_smoke.json" if args.smoke else "c12b_report.json")).write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    (RES / ("c12b_run_smoke.log" if args.smoke else "c12b_run.log")).write_text(
        "\n".join(lines), encoding="utf-8")
    log(f"\n[saved results/research/c12b/]  wallclock {report['wallclock_sec']}s")


if __name__ == "__main__":
    main()
