"""T4B: AdaptiveClip and RobustOMD on the ten-window frozen instrument.

Registered in ``experiment_matrix.yaml`` (fifteenth document) at the T4B commit, kind
``EMPIRICAL``, before this was run.

The paper's stability claims all rest on one instrument: ten disjoint 120-day windows,
hyperparameters tuned on window 1 and then FROZEN. The two scale-dependent *clippers* have
never been in it -- ``research_windows_replication.METHODS`` carries six methods and neither of
them. T4's C-23 found that on the one committed single-window run on the paper's own stream
they reach ``R^2`` 0.14-0.16 and never diverge, which puts the paper's partition on the wrong
axis: the scale-FREE uncapped endpoint diverges 7/10 while the scale-DEPENDENT bounded clipper
does not diverge at all. One single-window run is not enough to rest that correction on, and it
is not enough to rest the current framing on either.

Same windows, same tune-then-freeze protocol, same divergence criterion, same loader. Imported
from ``research_windows_replication`` rather than re-implemented, so the instrument cannot
quietly differ. A SEPARATE artifact is written: ``windows_replication.csv`` is pinned by the
paper and is not regenerated here.

Budget is matched and stated: a 1-D grid over ``lr`` on exactly ``LRS_SF``, the same ten points
the instrument gives normalized-GD, scale-adaptive OGD and SN-OMD, with the library's default
threshold parameters. Not the fixed-tau clip's 70-config 2-D budget.

The threshold statistics are reproduced from ``dfsl.algorithms`` exactly, *including* that the
current round's norm enters its own threshold -- that makes ``tau_t`` non-predictable, which is
the library's behaviour and is kept so the comparison is against the methods as measured
elsewhere rather than against an improved version of them.

Usage::

    .venv/Scripts/python.exe scripts/research_t4b_clipper_windows.py
    .venv/Scripts/python.exe scripts/research_t4b_clipper_windows.py --smoke
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

from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import (  # noqa: E402  (the instrument itself, not a copy)
    LRS_SF,
    WINDOWS,
    _diverged,
    _load,
)

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

WINDOW = 512          # every research script builds the clippers with window=512
QUANTILE = 0.9        # AdaptiveClip default
MULTIPLIER = 3.0      # RobustOMD default
MIN_HISTORY = 10      # both classes wait for 10 samples before clipping


def _mom(x: np.ndarray, n_blocks: int = 8) -> float:
    """Median of means, matching dfsl.estimators' construction closely enough for a threshold."""
    if x.size < n_blocks:
        return float(np.median(x))
    blocks = np.array_split(x, n_blocks)
    return float(np.median([b.mean() for b in blocks]))


def _tau_fn(kind: str):
    if kind == "adaptive_clip":
        return lambda h: float(np.quantile(h, QUANTILE))
    if kind == "robust_omd":
        return lambda h: MULTIPLIER * max(_mom(h), 1e-12)
    raise ValueError(kind)


class _Hist:
    """Fixed-capacity ring buffer over the trailing WINDOW gradient norms."""

    __slots__ = ("buf", "n", "cap")

    def __init__(self, cap: int) -> None:
        self.buf = np.empty(cap, dtype=np.float64)
        self.n = 0
        self.cap = cap

    def push(self, v: float) -> None:
        if self.n < self.cap:
            self.buf[self.n] = v
            self.n += 1
        else:
            self.buf[:-1] = self.buf[1:]
            self.buf[-1] = v

    def view(self) -> np.ndarray:
        return self.buf[: self.n]


def clip_perrow(X, y, wts, kind, lr):
    """One clipped OGD pass, per-row, step (lr/sqrt t) * clip(g, tau_t)."""
    tau_of = _tau_fn(kind)
    d = X.shape[1]
    w = np.zeros(d)
    hist = _Hist(WINDOW)
    k = 0
    preds = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i])
            preds[i] = pred
            k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0.0:
            continue
        hist.push(gn)
        if hist.n >= MIN_HISTORY:
            tau = tau_of(hist.view())
            if tau > 0.0 and gn > tau:
                g = g * (tau / gn)
        w = w - (lr / np.sqrt(k)) * g
    return preds


def clip_batched(X, y, wts, starts, kind, lr):
    """The same learner on the per-step protocol: one summed gradient per step."""
    tau_of = _tau_fn(kind)
    d = X.shape[1]
    w = np.zeros(d)
    hist = _Hist(WINDOW)
    ends = np.append(starts[1:], len(y))
    preds = np.empty(len(y))
    for k, (a, b) in enumerate(zip(starts, ends), start=1):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w
            preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0.0:
            continue
        hist.push(gn)
        if hist.n >= MIN_HISTORY:
            tau = tau_of(hist.view())
            if tau > 0.0 and gn > tau:
                g = g * (tau / gn)
        w = w - (lr / np.sqrt(k)) * g
    return preds


METHODS = ["AdaptiveClip", "RobustOMD"]
KIND = {"AdaptiveClip": "adaptive_clip", "RobustOMD": "robust_omd"}


def _run(name, lr, X, y, wts, starts, protocol):
    fn = clip_batched if protocol == "per-step" else clip_perrow
    extra = (starts,) if protocol == "per-step" else ()
    return fn(X, y, wts, *extra, KIND[name], lr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    rows, windows, lrs = args.rows, WINDOWS, list(LRS_SF)
    if args.smoke:
        rows, windows, lrs = 4000, WINDOWS[:3], [0.1, 0.5, 2.0]
        print(">>> SMOKE MODE <<<")

    print("=" * 96)
    print("T4B -- the clippers on the ten-window frozen instrument")
    print(f"  windows={len(windows)}  rows<={rows}  lr grid={lrs} (matched 1-D, = LRS_SF)")
    print("=" * 96)

    frozen: dict[tuple[str, str], float] = {}
    ceiling: list[dict] = []
    all_rows: list[dict] = []

    for protocol in ("per-row", "per-step"):
        print(f"\n########## PROTOCOL: {protocol} ##########")
        lo, hi = windows[0]
        X, y, wts, starts = _load(lo, hi, rows)
        print(f"\n[tune] window date[{lo},{hi})  n={len(y)}")
        for name in METHODS:
            best_lr, best_r2 = None, -np.inf
            last_stable, first_div = None, None
            for lr in lrs:
                p = _run(name, lr, X, y, wts, starts, protocol)
                r2 = agg_r2(y, p, wts)
                div = _diverged(y, p, wts)
                # C-23's open item: the committed sweep stopped at 3e-2 with these methods
                # still improving, so the ceiling was never located. Locate it here.
                if div and first_div is None:
                    first_div = lr
                if not div:
                    last_stable = lr
                if np.isfinite(r2) and r2 > best_r2 and not div:
                    best_lr, best_r2 = lr, float(r2)
                print(f"    {name:14s} lr={lr:<6g} R2={r2:+.4f}"
                      + ("   DIVERGED" if div else ""))
            frozen[(protocol, name)] = best_lr if best_lr is not None else lrs[0]
            ceiling.append({"protocol": protocol, "method": name,
                            "last_stable_lr": last_stable, "first_diverged_lr": first_div,
                            "ceiling_located": first_div is not None,
                            "frozen_lr": frozen[(protocol, name)],
                            "window1_r2": round(best_r2, 5) if np.isfinite(best_r2) else None})
            if first_div is None:
                loc = f"NOT located (stable at the top of the grid, {last_stable:g})"
            elif last_stable is None:
                loc = f"BELOW the grid: diverged at every lr tested, from {first_div:g}"
            else:
                loc = f"located in [{last_stable:g},{first_div:g})"
            r2s = f"{best_r2:+.4f}" if np.isfinite(best_r2) else "none stable"
            print(f"  {name:14s} frozen lr={frozen[(protocol, name)]:<6g} "
                  f"window1 R2={r2s}   ceiling {loc}")

        for wi, (lo, hi) in enumerate(windows):
            if wi == 0:
                Xw, yw, ww, sw = X, y, wts, starts
            else:
                Xw, yw, ww, sw = _load(lo, hi, rows)
            print(f"\n[eval] window {wi+1} date[{lo},{hi})  n={len(yw)}")
            for name in METHODS:
                lr = frozen[(protocol, name)]
                p = _run(name, lr, Xw, yw, ww, sw, protocol)
                r2 = agg_r2(yw, p, ww)
                div = _diverged(yw, p, ww)
                all_rows.append({
                    "protocol": protocol, "window": f"[{lo},{hi})", "window_idx": wi + 1,
                    "method": name, "setting": f"lr={lr:g}",
                    "weighted_r2": round(float(r2) if np.isfinite(r2) else float("nan"), 5),
                    "diverged": bool(div),
                })
                print(f"  {name:14s} R2={r2:+.4f}" + ("   <-- DIVERGED" if div else ""))

    df = pl.DataFrame(all_rows)
    tag = "_smoke" if args.smoke else ""
    df.write_csv(RES / f"t4b_clipper_windows{tag}.csv")
    pl.DataFrame(ceiling).write_csv(RES / f"t4b_clipper_ceiling{tag}.csv")

    # ------------------------------------------------------------------ summary
    print("\n" + "=" * 96)
    print("ACROSS-WINDOW SUMMARY (mean +/- std weighted R^2 at frozen settings)")
    print("=" * 96)
    sumrows = []
    for protocol in ("per-row", "per-step"):
        print(f"\n{protocol}:")
        sub = df.filter(pl.col("protocol") == protocol)
        agg = (sub.group_by("method").agg(
            pl.col("weighted_r2").mean().alias("mean"),
            pl.col("weighted_r2").std().alias("std"),
            pl.col("weighted_r2").min().alias("min"),
            pl.col("weighted_r2").max().alias("max"),
            pl.col("diverged").sum().alias("n_diverged"),
        ).sort("mean", descending=True))
        for r in agg.iter_rows(named=True):
            print(f"  {r['method']:14s} mean={r['mean']:+.4f}  std={r['std'] or 0:.4f}  "
                  f"[{r['min']:+.4f},{r['max']:+.4f}]  diverged={r['n_diverged']}/{len(windows)}")
            sumrows.append({"protocol": protocol, **r})
    pl.DataFrame(sumrows).write_csv(RES / f"t4b_clipper_windows_summary{tag}.csv")

    # ------------------------------- placed against the committed instrument's own rows
    ref = RES / "windows_replication_summary.csv"
    if ref.exists() and not args.smoke:
        print("\n" + "=" * 96)
        print("AGAINST THE COMMITTED INSTRUMENT (windows_replication_summary.csv)")
        print("=" * 96)
        r = pl.read_csv(ref)
        for protocol in ("per-row", "per-step"):
            print(f"\n{protocol}:")
            rows_ = [(x["method"], x["mean"], x["n_diverged"], "committed")
                     for x in r.filter(pl.col("protocol") == protocol).iter_rows(named=True)]
            rows_ += [(x["method"], x["mean"], x["n_diverged"], "T4B")
                      for x in (s for s in sumrows if s["protocol"] == protocol)]
            for m, mean, nd, src in sorted(rows_, key=lambda z: -(z[1] if z[1] == z[1] else -9)):
                mark = "  <== T4B" if src == "T4B" else ""
                print(f"  {m:24s} mean={mean:+.4f}  diverged={nd}/{len(windows)}{mark}")

    print("\n" + "=" * 96)
    print("WHAT THIS DOES NOT ESTABLISH")
    print("  No lower bound and no separation theorem -- T4's GAP 2 stands untouched.")
    print("  The clippers' threshold uses the current round's norm, so tau_t is NOT")
    print("    predictable; this reproduces the library, and is not a claim about ass:track.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
