"""Does SN-OMD's across-window variance come from its tracker? (audit item 15)

The 10-window replication (``research_windows_replication.py``) found SN-OMD with the
deployed winsorized-EMA tracker to be the most *variable* bounded scale-free method
(per-row std ~0.11, dipping negative on some windows), consistent with the paper's
already-flagged 3x block-bootstrap SE inflation, which it attributes to the EMA
tracker's spike response.

This script isolates the tracker: it runs SN-OMD (M=5) across the same ten disjoint
windows with (a) the winsorized-EMA tracker (deployed default) and (b) the block-median
tracker (the paper's 'most accurate per-row' tracker), each tuned on window 1 then
FROZEN. If the block-median tracker collapses the across-window variance, the variability
is a tracker artifact, not the cap/normalizer; if not, the paper's suspicion is refuted.

Usage::

    python scripts/research_windows_tracker.py            # full (~20-40 min)
    python scripts/research_windows_tracker.py --smoke
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

from research_baselines import (  # noqa: E402
    anchor_batched,
    anchor_perrow,
    blockmed_batched,
    blockmed_perrow,
)
from research_batched_check import group_boundaries  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS  # noqa: E402  (same disjoint windows)

from dfsl import JaneStreetDataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"
LRS = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]


def run_tracker(tracker, X, y, wts, starts, protocol, lr):
    batched = protocol == "per-step"
    if tracker == "EMA":
        if batched:
            return anchor_batched(X, y, wts, starts, "snomd", 5.0, lr)
        return anchor_perrow(X, y, wts, "snomd", 5.0, lr)
    # block-median
    if batched:
        return blockmed_batched(X, y, wts, starts, lr)   # Bg=818, cap=5 defaults
    return blockmed_perrow(X, y, wts, lr)                 # B=10000, cap=5 defaults


def _load(lo, hi, rows):
    ds = JaneStreetDataset(date_range=(lo, hi), max_rows=rows, standardize=True)
    return ds.X, ds.y, ds.weights, group_boundaries(ds.meta)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    rows = 4000 if args.smoke else args.rows
    windows = WINDOWS[:3] if args.smoke else WINDOWS
    lrs = [0.2, 1.0] if args.smoke else LRS
    trackers = ["EMA", "block-median"]

    print("=" * 92)
    print(f"SN-OMD TRACKER COMPARISON across {len(windows)} windows (frozen from window 1); rows<= {rows}")
    print("=" * 92)

    rows_out: list[dict] = []
    for protocol in ["per-row", "per-step"]:
        print(f"\n########## {protocol} ##########")
        lo, hi = windows[0]
        X, y, wts, starts = _load(lo, hi, rows)
        frozen = {}
        for tr in trackers:
            best = (-np.inf, None)
            for lr in lrs:
                r2 = agg_r2(y, run_tracker(tr, X, y, wts, starts, protocol, lr), wts)
                if np.isfinite(r2) and r2 > best[0]:
                    best = (r2, lr)
            frozen[tr] = best[1]
            print(f"  [tune] SN-OMD ({tr:12s}) frozen lr={best[1]:g}  window1 R2={best[0]:+.4f}")

        for wi, (lo, hi) in enumerate(windows):
            if wi == 0:
                Xw, yw, ww, sw = X, y, wts, starts
            else:
                Xw, yw, ww, sw = _load(lo, hi, rows)
            for tr in trackers:
                p = run_tracker(tr, Xw, yw, ww, sw, protocol, frozen[tr])
                r2 = agg_r2(yw, p, ww)
                rows_out.append({"protocol": protocol, "tracker": tr, "window": f"[{lo},{hi})",
                                 "window_idx": wi + 1, "lr": frozen[tr],
                                 "weighted_r2": round(float(r2) if np.isfinite(r2) else float("nan"), 5)})

    df = pl.DataFrame(rows_out)
    out = RES / ("windows_tracker_smoke.csv" if args.smoke else "windows_tracker.csv")
    df.write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    print("\n" + "=" * 92)
    print("ACROSS-WINDOW SN-OMD by tracker (mean +/- std; lower std = more regime-robust)")
    print("=" * 92)
    for protocol in ["per-row", "per-step"]:
        print(f"\n{protocol}:")
        for tr in trackers:
            s = df.filter((pl.col("protocol") == protocol) & (pl.col("tracker") == tr))["weighted_r2"]
            print(f"  SN-OMD ({tr:12s}) mean={s.mean():+.4f}  std={s.std():.4f}  "
                  f"[{s.min():+.4f},{s.max():+.4f}]")
    print("\nREADING: if block-median's std is markedly below EMA's, SN-OMD's across-window")
    print("variability is a tracker artifact (supports the paper's SE-inflation suspicion).")


if __name__ == "__main__":
    main()
