"""Paired across-window bootstrap: is the block-median tracker actually better? (audit round-3)

The ten-window replication (``research_windows_replication.py`` +
``research_windows_tracker.py``) reports mean+-std per method, but the accuracy question
--- does SN-OMD with the block-median scale beat the deployed winsorized-EMA default, and
the bounded baselines? --- needs a *paired* test that varies regime, not the single-window
block-bootstrap CI of Table 4 (which said "not significant").

This script pairs the two runs by window: block-median per-window weighted R^2 comes from
``windows_tracker.csv``; the EMA default (== "SN-OMD (M=5)") and every baseline come from
``windows_replication.csv``. For each protocol and each comparison it forms the ten paired
differences (block - other), then reports (a) the paired mean +- SE with a t_9 95% CI,
(b) a paired percentile bootstrap over the ten windows (resample windows w/ replacement),
and (c) wins/10. R^2 is floored at -1 before differencing so a divergent/severely-negative
window (e.g. scale-adaptive OGD per-row) contributes a bounded, interpretable gap rather
than a 1e6 outlier; the floor is stated in the output.

Usage::

    .venv/Scripts/python.exe scripts/research_tracker_bootstrap.py
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
FLOOR = -1.0        # R^2 floor: worse than predicting zero-mean is capped here for the gap
B = 10000           # bootstrap resamples over the 10 windows
T_BY_N = {10: 2.262, 9: 2.306}   # Student-t 0.975 quantile keyed by n paired diffs (n-1 dof)

# comparisons: block-median vs each of these (names as in the two CSVs)
BASELINES = [
    ("EMA (SN-OMD default)", "SN-OMD (M=5)"),
    ("Normalized-GD", "Normalized-GD"),
    ("Fixed-tau clip", "fixed-tau clip"),
    ("AdaGrad-Norm", "AdaGrad-Norm"),
    ("Cutkosky-Mehta", "Cutkosky-Mehta"),   # from windows_cm.csv, not windows_replication.csv
    ("OGD", "OGD"),
    ("Scale-adaptive OGD", "Scale-adaptive OGD"),
]


def _by_window(df: pl.DataFrame, protocol: str, key_col: str, key_val: str) -> dict[int, float]:
    sub = df.filter((pl.col("protocol") == protocol) & (pl.col(key_col) == key_val))
    return {int(w): float(r) for w, r in zip(sub["window_idx"], sub["weighted_r2"])}


def main() -> None:
    rep = pl.read_csv(RES / "windows_replication.csv")
    trk = pl.read_csv(RES / "windows_tracker.csv")
    cm = pl.read_csv(RES / "windows_cm.csv")   # Cutkosky-Mehta, same schema as rep

    rows_out: list[dict] = []
    rng = np.random.default_rng(0)

    print("=" * 92)
    print("PAIRED ACROSS-WINDOW BOOTSTRAP: block-median tracker vs EMA default and baselines")
    print(f"(ten frozen windows; R^2 floored at {FLOOR}; t_9 and {B}-resample percentile CIs)")
    print("=" * 92)

    for protocol in ["per-row", "per-step"]:
        block = _by_window(trk, protocol, "tracker", "block-median")
        # Also drop window 1 (the block median was selected on it) to close the selection
        # objection: an edge that survives on the nine untouched windows is selection-free.
        for wset_label, drop in [("all 10 windows", None),
                                 ("drop window 1 (selection-free)", 1)]:
            windows = sorted(w for w in block if w != drop)
            n = len(windows); tq = T_BY_N[n]
            print(f"\n########## {protocol} -- {wset_label}  (block mean = "
                  f"{np.mean([block[w] for w in windows]):+.4f}) ##########")
            print(f"  {'comparison (block - X)':28s} {'mean':>8s} {'SE':>7s} "
                  f"{'t95% CI':>18s} {'boot95% CI':>18s}  wins")
            for label, name in BASELINES:
                src = cm if name == "Cutkosky-Mehta" else rep
                other = _by_window(src, protocol, "method", name)
                diffs = np.array([max(block[w], FLOOR) - max(other[w], FLOOR) for w in windows])
                mean = float(diffs.mean())
                se = float(diffs.std(ddof=1) / np.sqrt(n))
                t_lo, t_hi = mean - tq * se, mean + tq * se
                boot = np.array([rng.choice(diffs, size=n, replace=True).mean()
                                 for _ in range(B)])
                b_lo, b_hi = np.percentile(boot, [2.5, 97.5])
                wins = int((diffs > 0).sum())
                sig = "*" if (t_lo > 0 or t_hi < 0) else " "
                print(f"  {label:28s} {mean:+8.4f} {se:7.4f} "
                      f"[{t_lo:+.3f},{t_hi:+.3f}] [{b_lo:+.3f},{b_hi:+.3f}] {sig} {wins:2d}/{n}")
                rows_out.append({"protocol": protocol, "window_set": wset_label,
                                 "comparison": f"block - {label}",
                                 "mean_diff": round(mean, 5), "se": round(se, 5),
                                 "t95_lo": round(t_lo, 5), "t95_hi": round(t_hi, 5),
                                 "boot95_lo": round(float(b_lo), 5), "boot95_hi": round(float(b_hi), 5),
                                 "n_windows": n, "wins": wins,
                                 "significant_t95": bool(t_lo > 0 or t_hi < 0)})

    out = RES / "tracker_bootstrap.csv"
    pl.DataFrame(rows_out).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")
    print("\nREADING: a t95/boot CI excluding 0 (marked *) is a paired significant gap across")
    print("regimes --- the instrument that varies the hypothesized variable. This supersedes")
    print("the single-window block-bootstrap CI of Table 4 for the block-vs-EMA question.")


if __name__ == "__main__":
    main()
