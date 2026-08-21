"""Two load-bearing checks for the causal Jane results.

(1) Contemporaneous (cross-sectional) leakage. If we update after every row, then
    predicting symbol 39 at (date,time) t has already trained on symbols 1..38 at the
    SAME timestep -- strictly past in row index, but contemporaneous in time. The
    honest protocol predicts the whole (date_id, time_id) batch, THEN applies one
    aggregated update. We compare per-row vs batched R^2; if it drops, there is a
    second, finer leakage of the same class as the standardizer.

(2) Does uncapped scale-adaptive OGD (M->inf) ever diverge in the lr sweep? This is
    load-bearing for the cap's empirical value on real data.

Self-contained; causal standardization. Usage: python scripts/research_batched_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dfsl import JaneStreetDataset
from dfsl.evaluation.metrics import weighted_r2

ROOT = Path(__file__).resolve().parents[1]


def group_boundaries(meta):
    """Return start indices of each (date_id, time_id) group (rows are pre-sorted)."""
    d = meta["date_id"].to_numpy()
    t = meta["time_id"].to_numpy()
    key = d.astype(np.int64) * (t.max() + 1) + t.astype(np.int64)
    change = np.ones(len(key), dtype=bool)
    change[1:] = key[1:] != key[:-1]
    return np.flatnonzero(change)


def _step(mode, cap, w, g, s, k, lr, decay=0.99, winsor=8.0):
    """One update; returns (w, s). k is the step count (row or group index)."""
    gn = float(np.linalg.norm(g))
    if not np.isfinite(gn) or gn == 0:
        return w, s
    if mode == "ogd":
        return w - (lr / np.sqrt(k)) * g, s
    if mode == "normgd":
        return w - (lr / np.sqrt(k)) * (g / gn), s
    # snomd / scale-adaptive (cap=inf recovers uncapped). Algorithm 1 normalizes by the
    # PREDICTABLE scale s_{t-1} -- F_{t-1}-measurable, i.e. built only from g_1..g_{t-1} --
    # and folds ||g_t|| in only afterwards. The high-probability analysis needs exactly that
    # measurability (Freedman), so the pre-update capture below is part of the algorithm,
    # not an implementation detail. Matches OnlineScaleTracker.step in dfsl.preprocessing.
    sc = max(s if s is not None else gn, 1e-8)
    s = gn if s is None else decay * s + (1 - decay) * min(gn, winsor * s)
    ghat = g / sc
    gnn = float(np.linalg.norm(ghat))
    if gnn > cap:
        ghat = ghat * (cap / gnn)
    return w - (lr / np.sqrt(k)) * ghat, s


def run_perrow(X, y, wts, mode, cap, lr):
    d = X.shape[1]
    w = np.zeros(d); s = None; k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred
            k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        w, s = _step(mode, cap, w, g, s, k, lr)
    return float(weighted_r2(y, preds, wts))


def run_batched(X, y, wts, starts, mode, cap, lr):
    d = X.shape[1]
    w = np.zeros(d); s = None
    preds = np.empty(len(y))
    ends = np.append(starts[1:], len(y))
    for k, (a, b) in enumerate(zip(starts, ends), start=1):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w; preds[a:b] = p
            resid = p - y[a:b]
            g = 2.0 * (X[a:b] * (wts[a:b] * resid)[:, None]).sum(axis=0)  # group gradient
        w, s = _step(mode, cap, w, g, s, k, lr)
    return float(weighted_r2(y, preds, wts))


def main():
    ds = JaneStreetDataset(date_range=(0, 120), max_rows=150000, standardize=True)
    X, y, wts = ds.X, ds.y, ds.weights
    starts = group_boundaries(ds.meta)
    print(f"{len(y)} rows in {len(starts)} (date,time) groups "
          f"(mean {len(y)/len(starts):.1f} symbols/timestep)")

    lrs = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
    methods = [("OGD", "ogd", 0.0), ("normalized-GD", "normgd", 0.0),
               ("SN-OMD (M=5)", "snomd", 5.0), ("uncapped scale-adaptive OGD", "snomd", 1e9)]

    def summarize(runner, *extra):
        rows_out = []
        for label, mode, cap in methods:
            best, stable = -np.inf, 0.0
            for lr in lrs:
                r2 = runner(X, y, wts, *extra, mode, cap, lr)
                bounded = np.isfinite(r2) and r2 > -1.0
                if bounded:
                    stable = max(stable, lr)
                    best = max(best, r2)
            rows_out.append((label, best, stable))
        return rows_out

    print("\n=== CHECK 1: batched-by-timestep, full lr sweep (does OGD still diverge?) ===")
    for label, best, stable in summarize(run_batched, starts):
        print(f"  {label:30s} best R2={best:+.4f}   stable lr <= {stable}")

    print("\n=== per-row, same sweep (for contrast) ===")
    for label, best, stable in summarize(run_perrow):
        print(f"  {label:30s} best R2={best:+.4f}   stable lr <= {stable}")

    print("\n=== CHECK 2: cap buys non-divergence? SN-OMD(M=5) vs uncapped at high lr (per-row) ===")
    for lr in [0.5, 1.0, 2.0, 5.0]:
        r2c = run_perrow(X, y, wts, "snomd", 5.0, lr)
        r2u = run_perrow(X, y, wts, "snomd", 1e9, lr)
        print(f"  lr={lr:4.1f}:  SN-OMD(M=5) R2={r2c:+.4f} ({'bounded' if r2c>-1 else 'DIVERGED'})   "
              f"uncapped R2={r2u:+.4f} ({'bounded' if r2u>-1 else 'DIVERGED'})")


if __name__ == "__main__":
    main()
