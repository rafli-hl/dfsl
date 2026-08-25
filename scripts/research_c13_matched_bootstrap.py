"""C13: re-run the paired across-window bootstrap on the MATCHED-BUDGET rows.

``research_tracker_bootstrap.py`` pairs the block-median tracker against the EMA default
and each baseline, and its intervals are what Appendix F.3 and Section B.2 quote. Those
intervals were computed from ``windows_tracker.csv`` and ``windows_replication.csv`` --
runs in which SN-OMD's cap was PINNED at M=5 while fixed-tau swept tau. C12/C12B replaced
that with a matched two-parameter budget and Table 1 adopted the new rows, but the paired
bootstrap was never re-run, so the appendix still asserts a +0.15 block-over-EMA gap
against a table whose own cells differ by +0.05.

This recomputes the same statistic on the adopted rows, using the identical methodology
(R^2 floored at -1 before differencing, paired by window, Student-t 95% interval, and a
percentile bootstrap resampling windows with replacement), so the only thing that changes
is the input.

One asymmetry this surfaces and does not fix. Cutkosky-Mehta is NOT part of the matched
run: it is tuned over (lr, tau, beta) = 9 x 6 x 4 = 216 configurations on window 1, where
SN-OMD and fixed-tau get 70 each. The extra budget favors CM, so a tie against CM is
conservative rather than inflated -- but it is a budget asymmetry of exactly the kind C12
was run to remove, and the comparison should be read with it in mind.

Usage::

    .venv/Scripts/python.exe scripts/research_c13_matched_bootstrap.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

FLOOR = -1.0        # identical to research_tracker_bootstrap.py
B = 10000
T_BY_N = {10: 2.262, 9: 2.306}
SEED = 0

# Comparisons, as (label, source, selector). "block" is always the left side.
BASELINES = [
    ("EMA (SN-OMD, M tuned)", "c12", "SN-OMD (M tuned)"),
    ("Normalized-GD", "c12", "Normalized-GD"),
    ("Fixed-tau clip", "c12", "fixed-tau clip"),
    ("AdaGrad-Norm", "c12", "AdaGrad-Norm"),
    ("Cutkosky-Mehta", "cm", "Cutkosky-Mehta"),
    ("OGD", "c12", "OGD"),
    ("Scale-adaptive OGD", "c12", "Scale-adaptive OGD"),
]


def _load():
    c12 = pl.read_csv(RES / "c12" / "c12_matched.csv")
    c12b = pl.read_csv(RES / "c12b" / "c12b_blockmed.csv")
    cm = pl.read_csv(RES / "windows_cm.csv")
    return c12, c12b, cm


def _series(df, protocol, col, value, key="window_idx"):
    sub = df.filter((pl.col("protocol") == protocol) & (pl.col(col) == value))
    return {int(r[key]): float(r["weighted_r2"]) for r in sub.iter_rows(named=True)}


def run() -> int:
    c12, c12b, cm = _load()
    rng = np.random.default_rng(SEED)

    print("=" * 96)
    print("C13 -- paired across-window bootstrap, recomputed on the MATCHED-BUDGET rows")
    print("  left side  : block-median tracker, cap tuned alongside rate (c12b, arm=matched)")
    print("  right side : the adopted Table 1 rows (c12), plus CM from windows_cm.csv")
    print("  NOTE       : CM is tuned over 216 configs (lr,tau,beta) vs 70 for SN-OMD and")
    print("               fixed-tau. The extra budget favors CM, so a tie is conservative.")
    print("=" * 96)

    rows_out: list[dict] = []
    for protocol in ("per-row", "per-step"):
        block = _series(c12b.filter(pl.col("arm") == "matched"), protocol, "arm", "matched")
        for drop, label in ((None, "all 10 windows"), (1, "drop window 1")):
            wins_set = sorted(w for w in block if drop is None or w != drop)
            n = len(wins_set)
            tcrit = T_BY_N[n]
            print(f"\n########## {protocol} -- {label}  (block mean = "
                  f"{np.mean([block[w] for w in wins_set]):+.4f}) ##########")
            print(f"  {'comparison (block - X)':30s} {'mean':>8s} {'SE':>7s} "
                  f"{'t95 CI':>20s} {'boot95 CI':>20s}  wins")
            for lab, src, sel in BASELINES:
                if src == "c12":
                    other = _series(c12, protocol, "method", sel)
                else:
                    other = _series(cm, protocol, "method", sel)
                missing = [w for w in wins_set if w not in other]
                if missing:
                    print(f"  {lab:30s}  MISSING windows {missing}")
                    continue
                diffs = np.array([max(block[w], FLOOR) - max(other[w], FLOOR)
                                  for w in wins_set])
                mean = float(diffs.mean())
                se = float(diffs.std(ddof=1) / np.sqrt(n))
                lo, hi = mean - tcrit * se, mean + tcrit * se
                reps = np.array([diffs[rng.integers(0, n, n)].mean() for _ in range(B)])
                blo, bhi = np.percentile(reps, [2.5, 97.5])
                w = int((diffs > 0).sum())
                sig = "*" if lo > 0 or hi < 0 else " "
                print(f"  {lab:30s} {mean:+8.4f} {se:7.4f} "
                      f"[{lo:+7.4f},{hi:+7.4f}] [{blo:+7.4f},{bhi:+7.4f}]  {w}/{n}{sig}")
                rows_out.append({
                    "protocol": protocol, "window_set": label,
                    "comparison": f"block - {lab}", "mean_diff": round(mean, 5),
                    "se": round(se, 5), "t95_lo": round(lo, 5), "t95_hi": round(hi, 5),
                    "boot95_lo": round(float(blo), 5), "boot95_hi": round(float(bhi), 5),
                    "n_windows": n, "wins": w,
                    "significant_t95": bool(lo > 0 or hi < 0),
                })

    out = RES / "c13_matched_bootstrap.csv"
    pl.DataFrame(rows_out).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    # ------------------------------------------------- Bonferroni, as the appendix reports it
    # 14 paired tests: seven baselines x two protocols. The drop-window-1 set re-analyses the
    # same comparisons rather than adding new ones, so it does not enter the count.
    T_BONF = 3.91          # t_9 at alpha/14, as already stated in the manuscript
    print("\n" + "-" * 96)
    print(f"BONFERRONI at alpha/14 (t_9 = {T_BONF} instead of {T_BY_N[10]}), all 10 windows")
    print(f"  {'comparison':34s} {'uncorrected':>22s} {'corrected':>22s}  verdict change")
    for r in rows_out:
        if r["window_set"] != "all 10 windows":
            continue
        lo = r["mean_diff"] - T_BONF * r["se"]
        hi = r["mean_diff"] + T_BONF * r["se"]
        was, now = r["significant_t95"], (lo > 0 or hi < 0)
        flag = "" if was == now else ("   <-- LOSES significance" if was else
                                      "   <-- GAINS significance")
        print(f"  {r['protocol']:8s} {r['comparison'].replace('block - ',''):25s} "
              f"{r['mean_diff']:+.4f} [{r['t95_lo']:+.3f},{r['t95_hi']:+.3f}]".rjust(22)
              + f"  {r['mean_diff']:+.4f} [{lo:+.3f},{hi:+.3f}]".rjust(22) + flag)
        r["bonf_lo"] = round(lo, 5)
        r["bonf_hi"] = round(hi, 5)
        r["significant_bonf"] = bool(now)
    pl.DataFrame(rows_out).write_csv(out)

    # ---------------------------------------------------- what changed versus the old run
    old = pl.read_csv(RES / "tracker_bootstrap.csv")
    print("\n" + "-" * 96)
    print("WHAT THE RE-RUN CHANGES (per-row, all 10 windows)")
    print(f"  {'comparison':30s} {'old (pinned M=5)':>26s} {'new (matched budget)':>26s}")
    pairs = [("block - EMA (SN-OMD default)", "block - EMA (SN-OMD, M tuned)"),
             ("block - Cutkosky-Mehta", "block - Cutkosky-Mehta"),
             ("block - Normalized-GD", "block - Normalized-GD"),
             ("block - Fixed-tau clip", "block - Fixed-tau clip"),
             ("block - AdaGrad-Norm", "block - AdaGrad-Norm")]
    for o, nw in pairs:
        ro = old.filter((pl.col("protocol") == "per-row")
                        & (pl.col("window_set") == "all 10 windows")
                        & (pl.col("comparison") == o))
        rn = [r for r in rows_out if r["protocol"] == "per-row"
              and r["window_set"] == "all 10 windows" and r["comparison"] == nw]
        if ro.height and rn:
            a, b_ = ro.row(0, named=True), rn[0]
            print(f"  {nw.replace('block - ',''):30s} "
                  f"{a['mean_diff']:+.4f} [{a['t95_lo']:+.3f},{a['t95_hi']:+.3f}]".rjust(26)
                  + f"   {b_['mean_diff']:+.4f} [{b_['t95_lo']:+.3f},{b_['t95_hi']:+.3f}]".rjust(26))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
