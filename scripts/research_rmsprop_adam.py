"""RMSProp and Adam head-to-head on the reported Jane window (audit Pass-III item 4).

Section 5 of the paper *argues* that the EMA-denominator adaptive optimizers (RMSProp,
Adam) mishandle a drifting heavy-tailed gradient scale -- numerator and denominator share
the round, so a single extreme gradient is not damped by the preconditioner -- but never
runs them. This script runs them, on the SAME window, protocols, grid discipline and
block-bootstrap error bars as ``research_baselines.py``.

Both are implemented in their standard deployed form (constant learning rate, no 1/sqrt(t)
decay, bias correction for Adam), tuned over a wide learning-rate grid, and reported
per-row and per-step next to the SN-OMD / OGD anchors. We also record the peak rolling
loss across the rate sweep -- the paper's divergence criterion -- so the claim in Section 5
is tested rather than asserted.

Usage::

    .venv/Scripts/python.exe scripts/research_rmsprop_adam.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_baselines import anchor_batched, anchor_perrow  # noqa: E402
from research_batched_check import group_boundaries  # noqa: E402
from research_table1_errorbars import N_BOOT, agg_r2, block_bootstrap  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

EPS = 1e-8
RHO = 0.9        # RMSProp second-moment decay (standard)
BETA1 = 0.9      # Adam first-moment decay (standard)
BETA2 = 0.999    # Adam second-moment decay (standard)

# Adaptive optimizers are deployed at a constant rate; sweep four orders of magnitude
# around the 1e-3 default, up to rates where a bounded-step method would still be usable.
LRS_ADAPTIVE = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 0.1, 0.3, 1.0]


# ------------------------------------------------------------------------------ RMSProp
def rmsprop_perrow(X, y, wts, lr):
    d = X.shape[1]; w = np.zeros(d); v = np.zeros(d)
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        if not np.isfinite(g).all():
            continue
        v = RHO * v + (1.0 - RHO) * (g * g)      # same round enters the denominator
        w = w - lr * g / (np.sqrt(v) + EPS)
    return preds


def rmsprop_batched(X, y, wts, starts, lr):
    d = X.shape[1]; w = np.zeros(d); v = np.zeros(d)
    ends = np.append(starts[1:], len(y)); preds = np.empty(len(y))
    for a, b in zip(starts, ends):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w; preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        if not np.isfinite(g).all():
            continue
        v = RHO * v + (1.0 - RHO) * (g * g)
        w = w - lr * g / (np.sqrt(v) + EPS)
    return preds


# --------------------------------------------------------------------------------- Adam
def adam_perrow(X, y, wts, lr):
    d = X.shape[1]; w = np.zeros(d); m = np.zeros(d); v = np.zeros(d); t = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        if not np.isfinite(g).all():
            continue
        t += 1
        m = BETA1 * m + (1.0 - BETA1) * g
        v = BETA2 * v + (1.0 - BETA2) * (g * g)
        mhat = m / (1.0 - BETA1 ** t)
        vhat = v / (1.0 - BETA2 ** t)
        w = w - lr * mhat / (np.sqrt(vhat) + EPS)
    return preds


def adam_batched(X, y, wts, starts, lr):
    d = X.shape[1]; w = np.zeros(d); m = np.zeros(d); v = np.zeros(d); t = 0
    ends = np.append(starts[1:], len(y)); preds = np.empty(len(y))
    for a, b in zip(starts, ends):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w; preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        if not np.isfinite(g).all():
            continue
        t += 1
        m = BETA1 * m + (1.0 - BETA1) * g
        v = BETA2 * v + (1.0 - BETA2) * (g * g)
        mhat = m / (1.0 - BETA1 ** t)
        vhat = v / (1.0 - BETA2 ** t)
        w = w - lr * mhat / (np.sqrt(vhat) + EPS)
    return preds


def _sched(lr, k, decaying):
    return lr / np.sqrt(k) if decaying else lr


def rmsprop_perrow_sched(X, y, wts, lr, decaying):
    d = X.shape[1]; w = np.zeros(d); v = np.zeros(d); k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred; k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        if not np.isfinite(g).all():
            continue
        v = RHO * v + (1.0 - RHO) * (g * g)
        w = w - _sched(lr, k, decaying) * g / (np.sqrt(v) + EPS)
    return preds


def adam_perrow_sched(X, y, wts, lr, decaying):
    d = X.shape[1]; w = np.zeros(d); m = np.zeros(d); v = np.zeros(d); t = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        if not np.isfinite(g).all():
            continue
        t += 1
        m = BETA1 * m + (1.0 - BETA1) * g
        v = BETA2 * v + (1.0 - BETA2) * (g * g)
        w = w - _sched(lr, t, decaying) * (m / (1.0 - BETA1 ** t)) / (
            np.sqrt(v / (1.0 - BETA2 ** t)) + EPS)
    return preds


def snomd_perrow_sched(X, y, wts, lr, decaying, cap=5.0, decay=0.99, winsor=8.0):
    """SN-OMD with the schedule as a free switch, so the comparison isolates it."""
    d = X.shape[1]; w = np.zeros(d); s = None; k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred; k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0:
            continue
        sc = max(s if s is not None else gn, 1e-8)
        s = gn if s is None else decay * s + (1.0 - decay) * min(gn, winsor * s)
        ghat = g / sc; gnn = float(np.linalg.norm(ghat))
        if gnn > cap:
            ghat = ghat * (cap / gnn)
        if np.isfinite(ghat).all():
            w = w - _sched(lr, k, decaying) * ghat
    return preds


def adagradnorm_perrow_sched(X, y, wts, lr, decaying):
    """AdaGrad-Norm; its monotone accumulator already decays, so `decaying` adds 1/sqrt(k)."""
    d = X.shape[1]; w = np.zeros(d); G = 0.0; k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred; k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        gn2 = float(g @ g)
        if not np.isfinite(gn2) or gn2 == 0:
            continue
        G += gn2
        w = w - _sched(lr, k, decaying) * g / np.sqrt(G + EPS)
    return preds


def schedule_control(X, y, wts, block_len, rng):
    """Is the adaptive optimizers' edge the PRECONDITIONER or the CONSTANT step schedule?

    Cross the two: {RMSProp, Adam, SN-OMD, AdaGrad-Norm} x {constant lr, lr/sqrt(t)}, full
    grid, per-row. If the paper's methods close the gap at a constant rate, the edge is the
    schedule (the paper handicaps itself with 1/sqrt(t)); if not, it is coordinate-wise
    preconditioning, which is a genuine baseline the paper does not have.
    """
    grid = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 0.1, 0.3, 1.0, 3.0]
    methods = [("RMSProp", rmsprop_perrow_sched), ("Adam", adam_perrow_sched),
               ("SN-OMD (M=5)", snomd_perrow_sched), ("AdaGrad-Norm", adagradnorm_perrow_sched)]
    print("\n" + "=" * 96)
    print("SCHEDULE CONTROL (per-row): preconditioner vs step-size schedule")
    print("=" * 96)
    out = []
    for decaying in (False, True):
        tag = "lr/sqrt(t)" if decaying else "constant lr"
        print(f"\n  schedule = {tag}")
        for label, fn in methods:
            cand = [({"lr": lr}, fn(X, y, wts, lr, decaying)) for lr in grid]
            setg, r2, p = best_bounded(cand, y, wts)
            if setg is None:
                print(f"    {label:16s} no bounded rate"); continue
            se, lo, hi = block_bootstrap(y, p, wts, block_len, rng)
            edge = "boundary" if setg["lr"] in (grid[0], grid[-1]) else "interior"
            print(f"    {label:16s} lr*={setg['lr']:<7g} R2={r2:+.4f} +-{se:.4f} "
                  f"[{lo:+.4f}, {hi:+.4f}] ({edge})")
            out.append({"schedule": tag, "method": label, "lr_star": setg["lr"],
                        "r2": round(r2, 4), "se": round(se, 4),
                        "ci_lo": round(lo, 4), "ci_hi": round(hi, 4), "grid": edge})
    pl.DataFrame(out).write_csv(RES / "schedule_control_jane.csv")
    print(f"\n  [saved {(RES / 'schedule_control_jane.csv').relative_to(ROOT)}]")


def best_bounded(candidates, y, wts):
    best = (None, -np.inf, None)
    for settings, p in candidates:
        r2 = agg_r2(y, p, wts)
        if np.isfinite(r2) and r2 > -1.0 and r2 > best[1]:
            best = (settings, r2, p)
    return best


def run() -> None:
    ds = JaneStreetDataset(date_range=(0, 120), max_rows=150000, standardize=True)
    X, y, wts = ds.X, ds.y, ds.weights
    starts = group_boundaries(ds.meta)
    ndays = int(np.unique(ds.meta["date_id"].to_numpy()).size)
    block_len = max(1, len(y) // ndays)
    rng = np.random.default_rng(0)

    print("=" * 96)
    print(f"RMSPROP / ADAM head-to-head on Jane  --  {len(y)} rows, {len(starts)} groups, "
          f"{ndays} days, block~{block_len}, {N_BOOT} resamples")
    print(f"RMSProp rho={RHO}; Adam beta=({BETA1},{BETA2}); eps={EPS}; constant lr")
    print("=" * 96)

    rows: list[dict] = []
    for protocol, rms, adam, anc, extra in [
        ("per-row", rmsprop_perrow, adam_perrow, anchor_perrow, ()),
        ("per-step", rmsprop_batched, adam_batched, anchor_batched, (starts,)),
    ]:
        print(f"\n{protocol.upper()}  (aggregate weighted R^2 at tuned rate; +-SE):")
        for label, fn in [("RMSProp", rms), ("Adam", adam)]:
            cand = [({"lr": lr}, fn(X, y, wts, *extra, lr)) for lr in LRS_ADAPTIVE]
            setg, r2, p = best_bounded(cand, y, wts)
            if setg is None:
                print(f"  {label:22s} no bounded rate on the grid")
                rows.append({"protocol": protocol, "method": label, "tune": "none bounded",
                             "r2": None, "se": None, "ci_lo": None, "ci_hi": None})
                continue
            se, lo, hi = block_bootstrap(y, p, wts, block_len, rng)
            edge = "boundary" if setg["lr"] in (LRS_ADAPTIVE[0], LRS_ADAPTIVE[-1]) else "interior"
            print(f"  {label:22s} lr*={setg['lr']:<7g} R2={r2:+.4f} +-{se:.4f} "
                  f"[{lo:+.4f}, {hi:+.4f}]  ({edge})")
            rows.append({"protocol": protocol, "method": label, "tune": f"lr={setg['lr']}",
                         "r2": round(r2, 4), "se": round(se, 4),
                         "ci_lo": round(lo, 4), "ci_hi": round(hi, 4), "grid": edge})

    out = RES / "rmsprop_adam_jane.csv"
    pl.DataFrame(rows).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    # ------- divergence sweep: the actual test of the Section 5 claim -------
    def rolling_max_loss(losses, window=2000):
        x = np.where(np.isfinite(losses), np.minimum(losses, 1e300), 1e300)
        w = max(1, min(window, x.size))
        return float(np.max(np.convolve(x, np.ones(w) / w, mode="valid")))

    def peak(preds):
        return rolling_max_loss(wts * (preds - y) ** 2)

    print("\n" + "-" * 96)
    print("DIVERGENCE SWEEP (per-row peak rolling loss vs learning rate)")
    print(f"  {'lr':>8} {'RMSProp':>14} {'Adam':>14} {'SN-OMD(M=5)':>14} {'plain OGD':>14}")
    srows = []
    for lr in LRS_ADAPTIVE:
        pk_r = peak(rmsprop_perrow(X, y, wts, lr))
        pk_a = peak(adam_perrow(X, y, wts, lr))
        pk_s = peak(anchor_perrow(X, y, wts, "snomd", 5.0, lr))
        pk_o = peak(anchor_perrow(X, y, wts, "ogd", 0.0, lr))
        print(f"  {lr:>8g} {pk_r:>14.4g} {pk_a:>14.4g} {pk_s:>14.4g} {pk_o:>14.4g}")
        srows.append({"lr": lr, "rmsprop_peak": float(pk_r), "adam_peak": float(pk_a),
                      "snomd_peak": float(pk_s), "ogd_peak": float(pk_o)})
    pl.DataFrame(srows).write_csv(RES / "rmsprop_adam_stability.csv")
    print(f"  [saved {(RES / 'rmsprop_adam_stability.csv').relative_to(ROOT)}]")
    print("\nREADING: report whatever this shows. If RMSProp/Adam stay bounded, Section 5's")
    print("'unbounded step' argument is too strong and must be corrected to the weaker (and")
    print("still true) statement that their preconditioner is not scale-FREE.")


if __name__ == "__main__":
    run()
