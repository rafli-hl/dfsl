"""Two baselines the review says are conspicuously missing from Table 1, run on the
SAME real stream and protocols with the SAME block-bootstrap error bars.

fixed-tau clip  clip(g, tau) = g * min(1, tau/||g||), a CONSTANT scale-free threshold
                (the paper's synthetic 'fixedclip', TAU=20). It satisfies Theorem 3.1
                (||ghat|| <= tau), so it should NOT diverge -- the honest question is
                whether a single global tau can fit a ~6x-drifting gradient scale as well
                as SN-OMD's tracked s_t. Tuned over (lr, tau).

AdaGrad-Norm    scalar AdaGrad: G_t += ||g_t||^2, step = eta * g_t / sqrt(G_t + eps). The
                Adam-family baseline Sec 5 argues fails because the same round enters
                numerator and denominator; here we actually run it. Tuned over eta.

Both are reported per-row and per-step at their tuned settings, with a circular
moving-block bootstrap (block ~ 1 day), alongside the Table 1 anchors normalized-GD and
SN-OMD (recomputed here for an apples-to-apples band).

Usage: python scripts/research_baselines.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_batched_check import _step, group_boundaries  # noqa: E402  (validated harness)
from research_table1_errorbars import N_BOOT, agg_r2, block_bootstrap  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

LRS = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
TAUS = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 300.0]  # tau ~ intrinsic ||g|| (median~9, p99~126)
LRS_ADAGRAD = [0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0]
EPS = 1e-8


# --------------------------------------------------------------------- fixed-tau clip
def fixedclip_perrow(X, y, wts, tau, lr):
    d = X.shape[1]; w = np.zeros(d); k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred; k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0:
            continue
        step = g * min(1.0, tau / gn)               # clip(g, tau): scale-free threshold
        w = w - (lr / np.sqrt(k)) * step
    return preds


def fixedclip_batched(X, y, wts, starts, tau, lr):
    d = X.shape[1]; w = np.zeros(d)
    ends = np.append(starts[1:], len(y)); preds = np.empty(len(y))
    for k, (a, b) in enumerate(zip(starts, ends), start=1):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w; preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0:
            continue
        step = g * min(1.0, tau / gn)
        w = w - (lr / np.sqrt(k)) * step
    return preds


# ------------------------------------------------------------------------ AdaGrad-Norm
def adagrad_perrow(X, y, wts, lr):
    d = X.shape[1]; w = np.zeros(d); G = 0.0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        gn2 = float(g @ g)
        if not np.isfinite(gn2) or gn2 == 0:
            continue
        G += gn2                                     # same round enters the denominator
        w = w - lr * g / np.sqrt(G + EPS)            # no extra 1/sqrt(t): sqrt(G) decays
    return preds


def adagrad_batched(X, y, wts, starts, lr):
    d = X.shape[1]; w = np.zeros(d); G = 0.0
    ends = np.append(starts[1:], len(y)); preds = np.empty(len(y))
    for k, (a, b) in enumerate(zip(starts, ends), start=1):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w; preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        gn2 = float(g @ g)
        if not np.isfinite(gn2) or gn2 == 0:
            continue
        G += gn2
        w = w - lr * g / np.sqrt(G + EPS)
    return preds


# ------------------------------------------------------- Table 1 anchors (via _step)
def anchor_perrow(X, y, wts, mode, cap, lr):
    d = X.shape[1]; w = np.zeros(d); s = None; k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred; k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        w, s = _step(mode, cap, w, g, s, k, lr)
    return preds


def anchor_batched(X, y, wts, starts, mode, cap, lr):
    d = X.shape[1]; w = np.zeros(d); s = None
    ends = np.append(starts[1:], len(y)); preds = np.empty(len(y))
    for k, (a, b) in enumerate(zip(starts, ends), start=1):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w; preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        w, s = _step(mode, cap, w, g, s, k, lr)
    return preds


def blockmed_perrow(X, y, wts, lr, B=10000, cap=5.0):
    """SN-OMD with a predictable per-block median scale (the paper's 'most accurate' tracker)."""
    d = X.shape[1]; w = np.zeros(d); blk = None; buf = []; k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred; k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0:
            continue
        sc = blk if blk is not None else max(gn, 1e-8)
        buf.append(gn)
        if len(buf) >= B:
            blk = max(float(np.median(buf)), 1e-8); buf = []
        sc = max(sc, 1e-8)
        ghat = g / sc; gnn = float(np.linalg.norm(ghat))
        if gnn > cap:
            ghat = ghat * (cap / gnn)
        if np.isfinite(ghat).all():
            w = w - (lr / np.sqrt(k)) * ghat
    return preds


def blockmed_batched(X, y, wts, starts, lr, Bg=818, cap=5.0):
    d = X.shape[1]; w = np.zeros(d); blk = None; buf = []
    ends = np.append(starts[1:], len(y)); preds = np.empty(len(y))
    for k, (a, b) in enumerate(zip(starts, ends), start=1):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w; preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0:
            continue
        sc = blk if blk is not None else max(gn, 1e-8)
        buf.append(gn)
        if len(buf) >= Bg:
            blk = max(float(np.median(buf)), 1e-8); buf = []
        sc = max(sc, 1e-8)
        ghat = g / sc; gnn = float(np.linalg.norm(ghat))
        if gnn > cap:
            ghat = ghat * (cap / gnn)
        if np.isfinite(ghat).all():
            w = w - (lr / np.sqrt(k)) * ghat
    return preds


# --------------------------------------------------- Cutkosky & Mehta (2021), live baseline
# Normalized SGD with momentum on CLIPPED gradients (their high-probability method under
# E||g||^p < inf): clip each raw gradient at a fixed tau, EMA it into a momentum, and step
# in the *normalized* momentum direction. Differs from SN-OMD, which divides by a *predictable
# tracked scale* (not a fixed clip) and caps the normalized gradient rather than fully
# normalizing the step. Tuned over (lr, tau, beta).
def cm_perrow(X, y, wts, tau, beta, lr):
    d = X.shape[1]; w = np.zeros(d); m = np.zeros(d); k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i]); preds[i] = pred; k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn):
            continue
        ghat = g * min(1.0, tau / gn) if gn > 0 else g          # clip raw g at tau
        m = beta * m + (1.0 - beta) * ghat                      # momentum on clipped grad
        mn = float(np.linalg.norm(m))
        if mn > 0 and np.isfinite(mn):
            w = w - (lr / np.sqrt(k)) * (m / mn)                # normalized step
    return preds


def cm_batched(X, y, wts, starts, tau, beta, lr):
    d = X.shape[1]; w = np.zeros(d); m = np.zeros(d)
    ends = np.append(starts[1:], len(y)); preds = np.empty(len(y))
    for k, (a, b) in enumerate(zip(starts, ends), start=1):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w; preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn):
            continue
        ghat = g * min(1.0, tau / gn) if gn > 0 else g
        m = beta * m + (1.0 - beta) * ghat
        mn = float(np.linalg.norm(m))
        if mn > 0 and np.isfinite(mn):
            w = w - (lr / np.sqrt(k)) * (m / mn)
    return preds


def best_over(candidates, y, wts):
    """candidates: list of (settings_dict, preds). Return best bounded by aggregate R2."""
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
    print(f"MISSING BASELINES on Jane  --  {len(y)} rows, {len(starts)} groups, {ndays} days, "
          f"block~{block_len}, {N_BOOT} resamples")
    print("=" * 96)

    rows: list[dict] = []
    for protocol, fc, ag, anc, extra in [
        ("per-row", fixedclip_perrow, adagrad_perrow, anchor_perrow, ()),
        ("per-step", fixedclip_batched, adagrad_batched, anchor_batched, (starts,)),
    ]:
        print(f"\n{protocol.upper()}  (aggregate weighted R^2 at tuned setting; +-SE):")

        # fixed-tau clip: tune (lr, tau)
        cand = [({"lr": lr, "tau": tau}, fc(X, y, wts, *extra, tau, lr))
                for lr in LRS for tau in TAUS]
        setg, r2, p = best_over(cand, y, wts)
        se, lo, hi = block_bootstrap(y, p, wts, block_len, rng)
        print(f"  {'fixed-tau clip':26s} tau*={setg['tau']:<5g} lr*={setg['lr']:<5g} "
              f"R2={r2:+.4f} +-{se:.4f}  [{lo:+.4f}, {hi:+.4f}]")
        rows.append({"protocol": protocol, "method": "fixed-tau clip", "tune": f"tau={setg['tau']},lr={setg['lr']}",
                     "r2": round(r2, 4), "se": round(se, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4)})

        # AdaGrad-Norm: tune eta
        cand = [({"lr": lr}, ag(X, y, wts, *extra, lr)) for lr in LRS_ADAGRAD]
        setg, r2, p = best_over(cand, y, wts)
        se, lo, hi = block_bootstrap(y, p, wts, block_len, rng)
        print(f"  {'AdaGrad-Norm':26s} eta*={setg['lr']:<5g}         "
              f"R2={r2:+.4f} +-{se:.4f}  [{lo:+.4f}, {hi:+.4f}]")
        rows.append({"protocol": protocol, "method": "AdaGrad-Norm", "tune": f"eta={setg['lr']}",
                     "r2": round(r2, 4), "se": round(se, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4)})

        # anchors: normalized-GD and SN-OMD (same band, apples-to-apples)
        for label, mode, cap in [("normalized-GD (anchor)", "normgd", 0.0),
                                 ("SN-OMD M=5 (anchor)", "snomd", 5.0)]:
            cand = [({"lr": lr}, anc(X, y, wts, *extra, mode, cap, lr)) for lr in LRS]
            setg, r2, p = best_over(cand, y, wts)
            se, lo, hi = block_bootstrap(y, p, wts, block_len, rng)
            print(f"  {label:26s} lr*={setg['lr']:<5g}         "
                  f"R2={r2:+.4f} +-{se:.4f}  [{lo:+.4f}, {hi:+.4f}]")
            rows.append({"protocol": protocol, "method": label, "tune": f"lr={setg['lr']}",
                         "r2": round(r2, 4), "se": round(se, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4)})

    out = RES / "baselines_jane.csv"
    pl.DataFrame(rows).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    # ---- stability sweep: are these baselines fragile, or bounded like SN-OMD? ----
    def rolling_max_loss(losses, window=2000):
        x = np.where(np.isfinite(losses), np.minimum(losses, 1e300), 1e300)
        w = max(1, min(window, x.size))
        return float(np.max(np.convolve(x, np.ones(w) / w, mode="valid")))

    def peak(preds):
        return rolling_max_loss(wts * (preds - y) ** 2)

    print("\n" + "-" * 96)
    print("STABILITY SWEEP (per-row peak rolling loss; does the method blow up at high lr?)")
    print(f"  {'lr':>6} {'fixed-tau(20)':>14} {'AdaGrad-Norm':>13} {'SN-OMD(M=5)':>12} {'plain OGD':>11}")
    srows = []
    for lr in [0.05, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]:
        pk_fc = peak(fixedclip_perrow(X, y, wts, 20.0, lr))
        pk_ag = peak(adagrad_perrow(X, y, wts, lr))
        pk_sn = peak(anchor_perrow(X, y, wts, "snomd", 5.0, lr))
        pk_ogd = peak(anchor_perrow(X, y, wts, "ogd", 0.0, lr))
        print(f"  {lr:>6} {pk_fc:>14.1f} {pk_ag:>13.1f} {pk_sn:>12.1f} {pk_ogd:>11.3g}")
        srows.append({"lr": lr, "fixedtau_peak": round(pk_fc, 2), "adagrad_peak": round(pk_ag, 2),
                      "snomd_peak": round(pk_sn, 2), "ogd_peak": float(pk_ogd)})
    pl.DataFrame(srows).write_csv(RES / "baselines_stability.csv")
    print(f"  [saved {(RES / 'baselines_stability.csv').relative_to(ROOT)}]")
    print("\nHONEST READING: fixed-tau clip and AdaGrad-Norm are BOUNDED-step methods, so they do")
    print("NOT diverge like OGD/scale-dependent clipping -- they belong in Table 1's stable group,")
    print("and are accuracy-competitive with (fixed-tau per-step: better than) SN-OMD. SN-OMD is")
    print("thus one of SEVERAL scale-free bounded methods here; its edge is the predictable tracker")
    print("+ dynamic-regret analysis, not a Jane accuracy win. This supports the review's C2.")


if __name__ == "__main__":
    run()
