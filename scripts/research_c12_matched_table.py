"""C12 -- regenerate tab:replication with the tuning-budget confound removed.

Registered in ``experiment_matrix.yaml`` (ninth document) at commit 14e6652 BEFORE this
script was executed.

The published table tunes ``fixed-tau clip`` over a joint ``(lr x tau)`` grid of 70
configurations and ``SN-OMD`` over ``lr`` alone (10), with the cap pinned at ``M=5`` — a
value chosen in a separate sweep at a single fixed ``lr=0.5``. Both methods have exactly one
threshold parameter; one gets it tuned and the other does not.

**Only SN-OMD's grid changes here.** Normalized-GD and Scale-adaptive OGD are the ``M->0``
and ``M->inf`` limits of the same family and carry no free threshold, so their 1-D grids are
intrinsic to the method rather than a deficiency; OGD and AdaGrad-Norm likewise. Every other
element — windows, rows, selection protocol, lr grids, divergence criterion — is held fixed
so the difference is attributable to the one change.

Writes to ``results/research/c12/`` only. ``windows_replication*.csv`` are deliberately NOT
overwritten: the manuscript cites them and
``test_artifacts_fresh.py::test_paper_number_matches_its_csv`` pins its printed numbers to
them.

Usage::

    python scripts/research_c12_matched_table.py            # full run (~10 min)
    python scripts/research_c12_matched_table.py --smoke    # fast sanity check
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
from research_divergence import diverged as rel_diverged  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research" / "c12"

# ---- registered design (experiment_matrix.yaml doc 9) ----------------------------
M_GRID = [0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 100.0]   # len == len(wr.TAUS): the budget match
REPRO_TOL = 0.005
UNCHANGED = ["OGD", "Normalized-GD", "Scale-adaptive OGD", "fixed-tau clip", "AdaGrad-Norm"]
SNOMD = "SN-OMD (M tuned)"
METHODS = ["OGD", "Normalized-GD", "Scale-adaptive OGD", SNOMD, "fixed-tau clip",
           "AdaGrad-Norm"]


def grid(name):
    """Each method over ITS OWN free parameters. Only SN-OMD's differs from published."""
    if name == SNOMD:
        return [{"lr": lr, "M": M} for lr in wr.LRS_SF for M in M_GRID]   # 2-D: the fix
    if name == "fixed-tau clip":
        return [{"lr": lr, "tau": t} for lr in wr.LRS_SF for t in wr.TAUS]
    if name == "OGD":
        return [{"lr": lr} for lr in wr.LRS_OGD]
    if name == "AdaGrad-Norm":
        return [{"lr": lr} for lr in wr.LRS_ADAGRAD]
    return [{"lr": lr} for lr in wr.LRS_SF]


def run(name, st, X, y, wts, starts, protocol):
    if name == SNOMD:
        return wr._run_method("SN-OMD (M=5)", st, X, y, wts, starts, protocol) \
            if st.get("M") == 5.0 and False else _snomd(st, X, y, wts, starts, protocol)
    return wr._run_method(name, st, X, y, wts, starts, protocol)


def _snomd(st, X, y, wts, starts, protocol):
    from research_baselines import anchor_batched, anchor_perrow
    if protocol == "per-step":
        return anchor_batched(X, y, wts, starts, "snomd", st["M"], st["lr"])
    return anchor_perrow(X, y, wts, "snomd", st["M"], st["lr"])


def boundary(name, st):
    flags = []
    lrs = sorted({g["lr"] for g in grid(name)})
    if st["lr"] in (lrs[0], lrs[-1]):
        flags.append(f"lr={st['lr']:g} at edge")
    if name == SNOMD and st["M"] in (M_GRID[0], M_GRID[-1]):
        flags.append(f"M={st['M']:g} at edge  <-- collapsed toward an endpoint method")
    if name == "fixed-tau clip" and st["tau"] in (wr.TAUS[0], wr.TAUS[-1]):
        flags.append(f"tau={st['tau']:g} at edge")
    return flags


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    rows, windows = args.rows, wr.WINDOWS
    global M_GRID
    if args.smoke:
        rows, windows = 4000, wr.WINDOWS[:3]
        wr.LRS_SF = [0.1, 0.5, 2.0]
        wr.LRS_OGD = [2e-3, 1e-2]
        wr.LRS_ADAGRAD = [0.03, 0.3]
        wr.TAUS = [5.0, 20.0]
        M_GRID = [2.0, 10.0]
        print(">>> SMOKE MODE <<<")

    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    lines: list[str] = []

    def log(m=""):
        print(m)
        lines.append(m)

    log("=" * 100)
    log("C12 -- tab:replication at MATCHED tuning budget (only SN-OMD's grid changes)")
    log(f"{len(windows)} windows, rows<={rows}; SN-OMD gets lr x M = "
        f"{len(wr.LRS_SF)}x{len(M_GRID)}={len(wr.LRS_SF)*len(M_GRID)}, "
        f"fixed-tau gets lr x tau = {len(wr.LRS_SF)}x{len(wr.TAUS)}={len(wr.LRS_SF)*len(wr.TAUS)}")
    log("=" * 100)

    frozen, tune_r2, out = {}, {}, []
    for protocol in ("per-row", "per-step"):
        log(f"\n########## {protocol} ##########")
        lo, hi = windows[0]
        X, y, wts, starts = wr._load(lo, hi, rows)
        log(f"[tune] window 1 date[{lo},{hi})  n={len(y)}")
        for name in METHODS:
            best, best_r2 = None, -np.inf
            for st in grid(name):
                r2 = agg_r2(y, run(name, st, X, y, wts, starts, protocol), wts)
                if np.isfinite(r2) and r2 > best_r2:
                    best, best_r2 = st, float(r2)
            frozen[(protocol, name)] = best
            tune_r2[(protocol, name)] = best_r2
            fl = boundary(name, best)
            log(f"  {name:24s} {len(grid(name)):3d} cfg  "
                f"{','.join(f'{k}={v:g}' for k, v in best.items()):22s} "
                f"win1 R2={best_r2:+.4f}" + (f"   <-- {'; '.join(fl)}" if fl else ""))

        for wi, (lo, hi) in enumerate(windows):
            Xw, yw, ww, sw = (X, y, wts, starts) if wi == 0 else wr._load(lo, hi, rows)
            for name in METHODS:
                st = frozen[(protocol, name)]
                p = run(name, st, Xw, yw, ww, sw, protocol)
                r2 = agg_r2(yw, p, ww)
                out.append({
                    "protocol": protocol, "window": f"[{lo},{hi})", "window_idx": wi + 1,
                    "method": name,
                    "setting": ",".join(f"{k}={v:g}" for k, v in st.items()),
                    "n_configs": len(grid(name)),
                    "weighted_r2": round(float(r2) if np.isfinite(r2) else float("nan"), 5),
                    "diverged": bool(wr._diverged(yw, p, ww)),
                    "diverged_rel": bool(rel_diverged(yw, p, ww)),
                })
            log(f"[eval] window {wi+1} done ({time.time()-t0:.0f}s)")

    df = pl.DataFrame(out)
    df.write_csv(RES / ("c12_matched_smoke.csv" if args.smoke else "c12_matched.csv"))

    # ---------------- summary in the published format + held-out ----------------
    rowsum = []
    for protocol in ("per-row", "per-step"):
        for name in METHODS:
            d = df.filter((pl.col("protocol") == protocol) & (pl.col("method") == name)) \
                  .sort("window_idx")
            v = d["weighted_r2"].to_numpy()
            rowsum.append({
                "protocol": protocol, "method": name,
                "setting": d["setting"][0], "n_configs": int(d["n_configs"][0]),
                "mean": float(np.nanmean(v)), "std": float(np.nanstd(v, ddof=1)),
                "min": float(np.nanmin(v)), "max": float(np.nanmax(v)),
                "n_diverged": int(d["diverged"].sum()),
                "n_diverged_rel": int(d["diverged_rel"].sum()),
                "heldout_mean": float(np.nanmean(v[1:])),
                "heldout_std": float(np.nanstd(v[1:], ddof=1)),
                "window1": float(v[0]),
            })
    sm = pl.DataFrame(rowsum)
    sm.write_csv(RES / ("c12_matched_summary_smoke.csv" if args.smoke
                        else "c12_matched_summary.csv"))

    log("\n" + "=" * 100)
    log("MATCHED-BUDGET TABLE   (all ten windows, published format | held-out 2-10)")
    log("=" * 100)
    for protocol in ("per-row", "per-step"):
        log(f"\n{protocol}:")
        sub = sm.filter(pl.col("protocol") == protocol).sort("mean", descending=True)
        log(f"  {'method':24s} {'cfg':>4s} {'all-10 mean':>12s} {'std':>7s} "
            f"{'div':>5s} {'div_rel':>8s} {'held-out':>10s} {'win1':>8s}")
        for r in sub.iter_rows(named=True):
            log(f"  {r['method']:24s} {r['n_configs']:>4d} {r['mean']:>+12.4f} "
                f"{r['std']:>7.4f} {r['n_diverged']:>3d}/10 {r['n_diverged_rel']:>6d}/10 "
                f"{r['heldout_mean']:>+10.4f} {r['window1']:>+8.4f}")

    # ---------------- reproduction gate on the untouched methods ----------------
    log("\n" + "=" * 100)
    log("REPRODUCTION GATE -- the five untouched methods must match the published CSV")
    log("=" * 100)
    ref_path = ROOT / "results" / "research" / "windows_replication.csv"
    gate = {}
    ok_all = True
    if ref_path.exists() and not args.smoke:
        ref = pl.read_csv(ref_path)
        for protocol in ("per-row", "per-step"):
            for name in UNCHANGED:
                mine = df.filter((pl.col("protocol") == protocol) & (pl.col("method") == name)) \
                         .sort("window_idx")["weighted_r2"].to_numpy()
                theirs = ref.filter((pl.col("protocol") == protocol) & (pl.col("method") == name)) \
                            .sort("window_idx")["weighted_r2"].to_numpy()
                if theirs.size == 0:
                    continue
                dv = float(np.nanmax(np.abs(mine - theirs)))
                ok = dv <= REPRO_TOL
                ok_all &= ok
                gate[f"{protocol}/{name}"] = {"max_abs_diff": dv, "ok": bool(ok)}
                log(f"  {protocol:9s} {name:22s} max|diff|={dv:.6f}  "
                    f"{'OK' if ok else '*** OUT OF TOLERANCE ***'}")
        if not ok_all:
            log("\n  GATE FAILED -- methods whose grids were not touched did not reproduce.")
            log("  Registered surprise (c): this indicates a harness problem, not a result.")

    report = {"M_GRID": M_GRID, "frozen": {f"{k[0]}/{k[1]}": v for k, v in frozen.items()},
              "boundary_flags": {f"{k[0]}/{k[1]}": boundary(k[1], v) for k, v in frozen.items()},
              "repro_gate": gate, "repro_gate_pass": bool(ok_all),
              "wallclock_sec": round(time.time() - t0, 1)}
    (RES / ("c12_report_smoke.json" if args.smoke else "c12_report.json")).write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    (RES / ("c12_run_smoke.log" if args.smoke else "c12_run.log")).write_text(
        "\n".join(lines), encoding="utf-8")
    log(f"\n[saved results/research/c12/]  wallclock {report['wallclock_sec']}s")


if __name__ == "__main__":
    main()
