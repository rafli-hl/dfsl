"""Stress-tests of the two favorable numbers from the previous round (applying the same
discipline that caught the leakage).

CHECK A  Is the block-tracker's beta<1 real, or a finite-horizon artifact? Refit
         W_s ~ T^beta restricted to horizons with enough blocks (T/B >= 50), and plot
         W_s against UPDATE COUNT (T/B). RESULT: beta ~ 1 wherever measurable, and W_s is
         linear in the update count with a B-independent slope (~1.7) -> the drift is a
         genuine T^{1/2} rate; B only moves the CONSTANT (1/B). The rescue fails.

CHECK B  Is the MNIST pooled heavy tail genuine within-phase drift, or the training
         transient? Redo pooled-vs-normalized alpha inside a constant-lr window. RESULT:
         in a nearly-flat-scale window the pooled tail is ALREADY light (alpha~6-9) -> the
         heaviness is schedule-driven (decay + lr drops), a weaker effect than on markets.

Usage: python scripts/research_review4_checks.py
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


def hill(a, k):
    a = np.sort(a[np.isfinite(a) & (a > 0)])[::-1]
    k = min(k, a.size - 2)
    return 1.0 / np.mean(np.log(a[:k]) - np.log(a[k])) if k > 0 and a[k] > 0 else float("nan")


def ema(g, d=0.99, w=8.0):
    s = np.empty_like(g); cur = g[0]
    for i, v in enumerate(g):
        s[i] = cur; cur = d * cur + (1 - d) * min(v, w * cur)
    return s


def check_a():
    print("=" * 70)
    print("CHECK A -- is block-tracker beta<1 real, or finite-horizon?")
    print("=" * 70)
    g = np.load(RES / "gradnorm_at_wstar.npy"); g = g[np.isfinite(g) & (g > 0)]; n = g.size

    def block(B, c=1.0):
        s = np.empty(n); cur = float(np.median(g[:B])) * c
        for st in range(0, n, B):
            s[st:min(st + B, n)] = cur; cur = c * float(np.median(g[st:st + B]))
        return s

    grid = np.unique(np.geomspace(3000, n - 1, 60).astype(int))
    print(f"  {'B':>7} {'beta(all)':>9} {'beta(T/B>=50)':>13} {'Ws(full)':>10} {'#blocks':>8}")
    for B in [1, 100, 1000, 3000, 10000, 30000]:
        s = block(B); inc = np.diff(s, prepend=s[0]); Ws = s[0] + np.cumsum(np.maximum(inc, 0.0))
        W = Ws[grid]
        def fit(mask):
            m = mask & (W > 0)
            return np.polyfit(np.log(grid[m].astype(float)), np.log(W[m]), 1)[0] if m.sum() >= 4 else float("nan")
        print(f"  {B:>7} {fit(np.ones_like(grid, bool)):>9.3f} {fit(grid / B >= 50):>13.3f} "
              f"{W[-1]:>10.0f} {n / B:>8.1f}".replace("nan", "  n/a"))
    print("  W_s vs update count k=T/B (slope should be B-independent if W_s ~ T):")
    for B in [100, 1000, 10000]:
        s = block(B); bnds = list(range(B, n, B)); prev = float(np.median(g[:B])); acc = prev; ws = []
        for st in bnds:
            m = float(np.median(g[st - B:st])); acc += max(m - prev, 0.0); prev = m; ws.append(acc)
        k = np.arange(1, len(ws) + 1)
        print(f"    B={B:6d}: slope={np.polyfit(k, ws, 1)[0]:.3f} per update  (R^2={np.corrcoef(k, ws)[0,1]**2:.3f})")


def check_b():
    print("\n" + "=" * 70)
    print("CHECK B -- MNIST: genuine within-phase drift or training transient?")
    print("=" * 70)
    p = RES / "gradnorm_mnist.npy"
    if not p.exists():
        print("  gradnorm_mnist.npy missing; run scripts/research_second_domain.py first.")
        return
    g = np.load(p); g = g[np.isfinite(g) & (g > 0)]
    fr = [0.02, 0.05, 0.10]

    def rep(tag, x):
        x = x[np.isfinite(x) & (x > 0)]
        print(f"  {tag:32s} " + "  ".join(f"k={f}:{hill(x,int(f*x.size)):.2f}" for f in fr))

    rep("FULL pooled ||g||", g)
    rep("FULL ||g||/EMA", (g / np.maximum(ema(g), 1e-12))[50:])
    w = g[938:1876]  # constant-lr window between the two lr drops
    mm = [float(np.median(w[i:i + 100])) for i in range(0, len(w) - 100, 100)]
    print(f"  mid-training constant-lr window: scale range {max(mm)/min(mm):.2f}x (nearly flat)")
    rep("MID pooled ||g||", w)
    rep("MID ||g||/EMA", (w / np.maximum(ema(w), 1e-12))[50:])


if __name__ == "__main__":
    check_a()
    check_b()
