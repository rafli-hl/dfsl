"""C10/Q6 -- is the constant-scale advantage a tuning-budget artifact?

Preregistered in ``experiment_matrix.yaml`` (direction C10/Q6), committed at 142a075
BEFORE this script was executed. Read that file first; this is only its execution.

The question. On the ten-window frozen-hyperparameter benchmark, fixed-tau clip (a
CONSTANT scale) beats SN-OMD (a PREDICTABLE TRACKED scale) 0.2064 to 0.1398 per-row --
the method losing to the thing it argues against. But the two are the same algorithm:

    fixed-tau clip   step magnitude = (lr/sqrt(k)) * min(||g_t||,       tau)
    SN-OMD (cap M)   step magnitude = (lr/sqrt(k)) * min(||g_t||/s_t,   M)

so SN-OMD with a constant scale s_t = s0 is fixed-tau clip with tau = M*s0 and
lr' = lr/s0. They differ in exactly one place -- whether the clip threshold is constant
or tracks a predictable scale. Yet ``research_windows_replication._grid`` tunes the
baseline over a 2-D grid (lr x tau = 70 configs) and the proposal over a 1-D grid
(lr = 10 configs, cap pinned at M=5). This script equalizes that budget and remeasures.

Three arms, identical selection rule (best window-1 weighted R2), identical evaluation:

    A1  fixed-tau clip       lr x tau  = 70   (reproduces published tuning)
    A2  SN-OMD, M pinned 5   lr        = 10   (reproduces published tuning)
    A3  SN-OMD, cap tuned    lr x M    = 70   (budget-matched -- the intervention)

Window 1 selects; windows 2-10 evaluate. The published protocol pools the selection
window into its reported mean, which this script deliberately does not do for the primary
estimand -- it reports both.

Usage::

    python scripts/research_c10_budget_match.py            # full run (~10 min)
    python scripts/research_c10_budget_match.py --smoke    # fast sanity check
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

from research_baselines import (  # noqa: E402  (validated harnesses)
    anchor_batched,
    anchor_perrow,
    fixedclip_batched,
    fixedclip_perrow,
)
from research_batched_check import group_boundaries  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS, _diverged  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research" / "c10"

# ---- preregistered grids (experiment_matrix.yaml: design.grids) -------------------
LRS_SF = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0]
TAUS = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 300.0]
M_GRID = [0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 100.0]  # len == len(TAUS): the budget match

ARMS = ["A1_fixedtau_2d", "A2_snomd_1d_published", "A3_snomd_2d_matched"]
ARM_LABEL = {
    "A1_fixedtau_2d": "fixed-tau clip (lr x tau)",
    "A2_snomd_1d_published": "SN-OMD M=5 (lr only)",
    "A3_snomd_2d_matched": "SN-OMD (lr x M)",
}
BOOT_SEED = 20260823
N_BOOT = 10000
REPRO_TOL = 0.005  # experiment_matrix.yaml: reproduction_gate


def _grid(arm):
    if arm == "A1_fixedtau_2d":
        return [{"lr": lr, "tau": t} for lr in LRS_SF for t in TAUS]
    if arm == "A2_snomd_1d_published":
        return [{"lr": lr, "M": 5.0} for lr in LRS_SF]
    if arm == "A3_snomd_2d_matched":
        return [{"lr": lr, "M": m} for lr in LRS_SF for m in M_GRID]
    raise ValueError(arm)


def _run(arm, setting, X, y, wts, starts, protocol):
    batched = protocol == "per-step"
    if arm == "A1_fixedtau_2d":
        fn = fixedclip_batched if batched else fixedclip_perrow
        extra = (starts,) if batched else ()
        return fn(X, y, wts, *extra, setting["tau"], setting["lr"])
    fn = anchor_batched if batched else anchor_perrow
    extra = (starts,) if batched else ()
    return fn(X, y, wts, *extra, "snomd", setting["M"], setting["lr"])


def _load(lo, hi, rows):
    ds = JaneStreetDataset(date_range=(lo, hi), max_rows=rows, standardize=True)
    return ds.X, ds.y, ds.weights, group_boundaries(ds.meta)


def _boundary_flags(arm, setting):
    """Report any selected hyperparameter sitting on a grid edge (prereg: grid adequacy)."""
    flags = []
    if setting["lr"] in (LRS_SF[0], LRS_SF[-1]):
        flags.append(f"lr={setting['lr']:g} at grid edge")
    if arm == "A1_fixedtau_2d" and setting["tau"] in (TAUS[0], TAUS[-1]):
        flags.append(f"tau={setting['tau']:g} at grid edge")
    if arm == "A3_snomd_2d_matched" and setting["M"] in (M_GRID[0], M_GRID[-1]):
        flags.append(f"M={setting['M']:g} at grid edge")
    return flags


def _paired_stats(diff, rng):
    """Mean paired difference over windows, SE, percentile bootstrap CI, exact sign test."""
    n = len(diff)
    mean = float(np.mean(diff))
    se = float(np.std(diff, ddof=1) / np.sqrt(n))
    idx = rng.integers(0, n, size=(N_BOOT, n))
    boot = np.mean(diff[idx], axis=1)
    lo, hi = (float(v) for v in np.percentile(boot, [2.5, 97.5]))
    # exact two-sided sign test (ties excluded), binomial(p=0.5)
    from math import comb

    pos = int(np.sum(diff > 0))
    m = int(np.sum(diff != 0))
    if m == 0:
        p = 1.0
    else:
        k = min(pos, m - pos)
        tail = sum(comb(m, i) for i in range(0, k + 1)) / (2.0 ** m)
        p = min(1.0, 2.0 * tail)
    return {"mean": mean, "se": se, "ci_lo": lo, "ci_hi": hi,
            "n_positive": pos, "n": m, "sign_p": float(p)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    rows, windows = args.rows, WINDOWS
    global LRS_SF, TAUS, M_GRID
    if args.smoke:
        rows, windows = 4000, WINDOWS[:3]
        LRS_SF = [0.1, 0.5, 2.0]
        TAUS = [5.0, 20.0]
        M_GRID = [2.0, 10.0]
        print(">>> SMOKE MODE <<<")

    RES.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    print("=" * 96)
    print("C10/Q6 -- BUDGET-MATCHED constant vs tracked scale")
    print(f"window 1 selects; windows 2-{len(windows)} evaluate; rows<={rows}")
    print("=" * 96)

    frozen: dict[tuple[str, str], dict] = {}
    tune_r2: dict[tuple[str, str], float] = {}
    rows_out: list[dict] = []

    for protocol in ["per-row", "per-step"]:
        print(f"\n########## PROTOCOL: {protocol} ##########")
        lo, hi = windows[0]
        X, y, wts, starts = _load(lo, hi, rows)
        print(f"[tune] window 1 date[{lo},{hi})  n={len(y)}")
        for arm in ARMS:
            best, best_r2 = None, -np.inf
            for setting in _grid(arm):
                r2 = agg_r2(y, _run(arm, setting, X, y, wts, starts, protocol), wts)
                if np.isfinite(r2) and r2 > best_r2:
                    best, best_r2 = setting, r2
            frozen[(protocol, arm)] = best
            tune_r2[(protocol, arm)] = float(best_r2)
            desc = ",".join(f"{k}={v:g}" for k, v in best.items())
            edge = _boundary_flags(arm, best)
            note = ("   <-- GRID BOUNDARY: " + "; ".join(edge)) if edge else ""
            print(f"  {ARM_LABEL[arm]:28s} {len(_grid(arm)):3d} cfgs  frozen: {desc:22s} "
                  f"window1 R2={best_r2:+.4f}{note}")

        for wi, (lo, hi) in enumerate(windows):
            if wi == 0:
                Xw, yw, ww, sw = X, y, wts, starts
            else:
                Xw, yw, ww, sw = _load(lo, hi, rows)
            print(f"[eval] window {wi+1} date[{lo},{hi})  n={len(yw)}")
            for arm in ARMS:
                st = frozen[(protocol, arm)]
                p = _run(arm, st, Xw, yw, ww, sw, protocol)
                r2 = agg_r2(yw, p, ww)
                div = _diverged(yw, p, ww)
                rows_out.append({
                    "protocol": protocol, "window": f"[{lo},{hi})", "window_idx": wi + 1,
                    "arm": arm, "method": ARM_LABEL[arm],
                    "setting": ",".join(f"{k}={v:g}" for k, v in st.items()),
                    "n_configs": len(_grid(arm)),
                    "weighted_r2": round(float(r2) if np.isfinite(r2) else float("nan"), 6),
                    "diverged": bool(div),
                    "is_selection_window": wi == 0,
                })
                print(f"    {ARM_LABEL[arm]:28s} R2={r2:+.4f}{'  <-- DIVERGED' if div else ''}")

    df = pl.DataFrame(rows_out)
    out_csv = RES / ("c10_budget_match_smoke.csv" if args.smoke else "c10_budget_match.csv")
    df.write_csv(out_csv)
    print(f"\n[saved {out_csv.relative_to(ROOT)}]")

    # ---------------- analysis (preregistered) ----------------
    rng = np.random.default_rng(BOOT_SEED)
    report: dict = {"grids": {"LRS_SF": LRS_SF, "TAUS": TAUS, "M_GRID": M_GRID},
                    "boot_seed": BOOT_SEED, "n_boot": N_BOOT, "protocols": {}}

    print("\n" + "=" * 96)
    print("PREREGISTERED ANALYSIS")
    print("=" * 96)

    for protocol in ["per-row", "per-step"]:
        d = df.filter(pl.col("protocol") == protocol)
        r2 = {arm: d.filter(pl.col("arm") == arm).sort("window_idx")["weighted_r2"].to_numpy()
              for arm in ARMS}
        held = {arm: v[1:] for arm, v in r2.items()}

        d_pub = held["A1_fixedtau_2d"] - held["A2_snomd_1d_published"]
        d_mat = held["A1_fixedtau_2d"] - held["A3_snomd_2d_matched"]
        delta_pub, delta_mat = float(d_pub.mean()), float(d_mat.mean())
        frac = (delta_pub - delta_mat) / delta_pub if delta_pub != 0 else float("nan")

        s_pub, s_mat = _paired_stats(d_pub, rng), _paired_stats(d_mat, rng)
        # A3 vs A2: what budget matching bought the proposal, paired
        s_gain = _paired_stats(held["A3_snomd_2d_matched"] - held["A2_snomd_1d_published"], rng)

        print(f"\n--- {protocol} ---")
        for arm in ARMS:
            print(f"  {ARM_LABEL[arm]:28s} window1={r2[arm][0]:+.4f}   "
                  f"held-out mean={held[arm].mean():+.4f}  "
                  f"std={held[arm].std(ddof=1):.4f}  "
                  f"min={held[arm].min():+.4f}  frozen={frozen[(protocol, arm)]}")
        print(f"  delta_published (A1-A2, held-out) = {delta_pub:+.4f}  "
              f"[95% CI {s_pub['ci_lo']:+.4f},{s_pub['ci_hi']:+.4f}]  "
              f"wins {s_pub['n_positive']}/{s_pub['n']}  sign p={s_pub['sign_p']:.4f}")
        print(f"  delta_matched   (A1-A3, held-out) = {delta_mat:+.4f}  "
              f"[95% CI {s_mat['ci_lo']:+.4f},{s_mat['ci_hi']:+.4f}]  "
              f"wins {s_mat['n_positive']}/{s_mat['n']}  sign p={s_mat['sign_p']:.4f}")
        print(f"  budget gain     (A3-A2, held-out) = {s_gain['mean']:+.4f}  "
              f"[95% CI {s_gain['ci_lo']:+.4f},{s_gain['ci_hi']:+.4f}]")
        print(f"  fraction_closed = {frac:+.4f}")

        if protocol == "per-row":
            if frac >= 0.50:
                verdict = "H1 SURVIVED (fraction_closed >= 0.50)"
            elif frac <= 0.25:
                verdict = "H1 FALSIFIED (fraction_closed <= 0.25)"
            else:
                verdict = "INCONCLUSIVE (0.25 < fraction_closed < 0.50)"
            print(f"  REGISTERED VERDICT (primary, per-row): {verdict}")
            report["verdict"] = verdict

        report["protocols"][protocol] = {
            "window1": {a: float(r2[a][0]) for a in ARMS},
            "heldout_mean": {a: float(held[a].mean()) for a in ARMS},
            "heldout_std": {a: float(held[a].std(ddof=1)) for a in ARMS},
            "frozen": {a: frozen[(protocol, a)] for a in ARMS},
            "boundary_flags": {a: _boundary_flags(a, frozen[(protocol, a)]) for a in ARMS},
            "delta_published": delta_pub, "delta_matched": delta_mat,
            "fraction_closed": frac,
            "paired_published": s_pub, "paired_matched": s_mat, "paired_gain": s_gain,
        }

    # ---------------- reproduction gate ----------------
    print("\n" + "=" * 96)
    print("REPRODUCTION GATE (vs results/research/windows_replication.csv)")
    print("=" * 96)
    ref_path = ROOT / "results" / "research" / "windows_replication.csv"
    repro = {}
    if ref_path.exists() and not args.smoke:
        ref = pl.read_csv(ref_path)
        pairs = [("A1_fixedtau_2d", "fixed-tau clip"), ("A2_snomd_1d_published", "SN-OMD (M=5)")]
        for protocol in ["per-row", "per-step"]:
            for arm, refname in pairs:
                mine = df.filter((pl.col("protocol") == protocol) & (pl.col("arm") == arm)) \
                         .sort("window_idx")["weighted_r2"].to_numpy()[1:].mean()
                theirs = ref.filter((pl.col("protocol") == protocol)
                                    & (pl.col("method") == refname)) \
                            .sort("window_idx")["weighted_r2"].to_numpy()[1:].mean()
                dv = abs(float(mine) - float(theirs))
                ok = dv <= REPRO_TOL
                repro[f"{protocol}/{arm}"] = {"mine": float(mine), "stored": float(theirs),
                                              "abs_diff": dv, "within_tol": bool(ok)}
                print(f"  {protocol:9s} {arm:24s} mine={mine:+.4f} stored={theirs:+.4f} "
                      f"diff={dv:.4f}  {'OK' if ok else '*** OUT OF TOLERANCE ***'}")
    report["reproduction"] = repro
    report["wallclock_sec"] = round(time.time() - t_start, 1)

    out_json = RES / ("c10_report_smoke.json" if args.smoke else "c10_report.json")
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[saved {out_json.relative_to(ROOT)}]  wallclock {report['wallclock_sec']}s")


if __name__ == "__main__":
    main()
