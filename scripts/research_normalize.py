"""Achievability test: does a SCALE-NORMALIZED step attain the worst-tail rate?

THEORY.md section 4 predicts the fix for the drifting-scale divergence (FINDINGS
Finding 7) is to decouple the step from the tail scale: divide the gradient by a
tracked robust scale s_t (scale-invariant step) instead of clipping to a
scale-dependent threshold tau_t = c*s_t. The two differ by a factor 1/s_t:

    clip-to-tau step   ~  min(||g||, M*s) . g/||g||        (scales WITH s -> transmits drift)
    normalize+cap step ~  min(||g||/s, M) . g/||g||        (scale-INVARIANT -> immune to drift)

We implement Scale-Normalized OGD (SN-OGD): a robustified EMA scale tracker s_t plus
a *constant, scale-free* cap M on the normalized gradient, and test it exactly where
clipping failed (per-window restarts, FINDINGS Finding 7) and on the continuous
multi-regime stream (Finding 8). Success = bounded across all regimes without
per-regime lr tuning, at R^2 comparable to the best clipper.

Usage::  python scripts/research_normalize.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dfsl import AdaptiveClip, JaneStreetDataset, OnlineGradientDescent, RobustOMD
from dfsl.evaluation import best_fixed_linear, linear_losses, regret_curve
from dfsl.evaluation.metrics import weighted_r2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "research"

plt.rcParams.update(
    {
        "font.family": "serif", "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "cm", "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
        "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "axes.linewidth": 0.6, "lines.linewidth": 1.2, "legend.frameon": False,
        "axes.spines.top": False, "axes.spines.right": False,
        "savefig.dpi": 300, "savefig.bbox": "tight",
    }
)


class ScaleNormalizedOGD:
    """OGD with a scale-invariant step: g_t / s_t, capped at a scale-free M.

    s_t is a robustified EMA of ||g_t|| (a single spike contributes at most
    winsor*s_{t-1}), so the *typical* normalized gradient is O(1) regardless of the
    regime's scale; the constant cap M bounds the worst-case step without depending
    on s_t.
    """

    def __init__(self, dim, learning_rate=0.1, beta=0.99, cap=10.0, winsor=8.0):
        self.dim = dim
        self.lr = learning_rate
        self.beta = beta
        self.cap = cap
        self.winsor = winsor
        self.weights = np.zeros(dim)
        self.t = 0
        self.s = None

    def predict(self, x):
        return float(self.weights @ x)

    def update(self, x, y, weight=1.0):
        self.t += 1
        pred = self.predict(x)
        with np.errstate(over="ignore", invalid="ignore"):
            err = np.float64(pred) - np.float64(y)
            loss = float(np.float64(weight) * err * err)
            g = 2.0 * weight * err * x
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn):
            return loss
        if self.s is None:
            self.s = max(gn, 1e-8)
        else:
            self.s = self.beta * self.s + (1.0 - self.beta) * min(gn, self.winsor * self.s)
        s = max(self.s, 1e-8)
        ghat = g / s
        gnn = float(np.linalg.norm(ghat))
        if gnn > self.cap:
            ghat = ghat * (self.cap / gnn)
        if np.isfinite(ghat).all():
            self.weights -= (self.lr / np.sqrt(self.t)) * ghat
        return loss

    def run(self, stream):
        preds, tgts, wts, losses = [], [], [], []
        for x, y, w in stream:
            preds.append(self.predict(x))
            tgts.append(y)
            wts.append(w)
            losses.append(self.update(x, y, w))
        import types
        return types.SimpleNamespace(
            predictions=np.asarray(preds), targets=np.asarray(tgts),
            weights=np.asarray(wts), losses=np.asarray(losses),
        )


def make_learner(name, dim, lr):
    if name == "ogd":
        return OnlineGradientDescent(dim=dim, learning_rate=lr)
    if name == "adaptive_clip":
        return AdaptiveClip(dim=dim, learning_rate=lr, window=512)
    if name == "sn_ogd":
        return ScaleNormalizedOGD(dim=dim, learning_rate=lr)
    est = name.split("[")[1].rstrip("]")
    return RobustOMD(dim=dim, learning_rate=lr, estimator=est, window=512, clip_multiplier=3.0)


def rolling_max_loss(losses, window=2000):
    x = np.where(np.isfinite(losses), losses, np.inf)
    w = max(1, min(window, x.size))
    roll = np.convolve(np.minimum(x, 1e300), np.ones(w) / w, mode="valid")
    return float(np.max(roll))


def eval_run(learner, stream, comp):
    r = learner.run(stream)
    r2 = float(weighted_r2(r.targets, r.predictions, r.weights))
    reg = float(regret_curve(r.losses, comp)[-1])
    peak = rolling_max_loss(r.losses)
    return r2, reg, peak


# --------------------------------------------------------------------------- #
def test_continuous():
    print("\n=== TEST A: continuous multi-regime stream date[0,120) ===")
    ds = JaneStreetDataset(date_range=(0, 120), max_rows=150000, standardize=True)
    X, y, w = ds.X, ds.y, ds.weights
    dim = X.shape[1]
    comp = linear_losses(X, y, best_fixed_linear(X, y, w), w)
    stream = list(zip(X, y, w))
    lrs = [2e-3, 5e-3, 1e-2, 2e-2, 3e-2, 5e-2, 1e-1, 2e-1, 3.5e-1, 5e-1]
    methods = ["ogd", "adaptive_clip", "robust_omd[median_of_means]", "sn_ogd"]
    rows = []
    for name in methods:
        for lr in lrs:
            r2, reg, peak = eval_run(make_learner(name, dim, lr), stream, comp)
            diverged = (not np.isfinite(r2)) or r2 < -1.0 or peak > 50.0
            rows.append({"method": name, "learning_rate": lr, "weighted_r2": r2,
                         "peak_rolling_loss": peak, "diverged": diverged})
            print(f"  {name:28s} lr={lr:.0e}  R2={r2:+.5f}  peak={peak:9.2f}"
                  + ("  DIVERGED" if diverged else ""))
    df = pl.DataFrame(rows)
    df.write_csv(OUT / "normalize_continuous.csv")
    return df


def test_windows():
    print("\n=== TEST B: per-window restart (where clipping failed, Finding 7) ===")
    windows = [(0, 20), (30, 50), (100, 120), (400, 420), (900, 920)]
    methods = ["ogd", "adaptive_clip", "sn_ogd"]
    rows = []
    for lr in (5e-3, 1e-2):
        for lo, hi in windows:
            ds = JaneStreetDataset(date_range=(lo, hi), max_rows=60000, standardize=True)
            X, y, w = ds.X, ds.y, ds.weights
            dim = X.shape[1]
            comp = linear_losses(X, y, best_fixed_linear(X, y, w), w)
            stream = list(zip(X, y, w))
            for name in methods:
                r2, reg, peak = eval_run(make_learner(name, dim, lr), stream, comp)
                diverged = (not np.isfinite(r2)) or r2 < -1.0 or peak > 50.0
                rows.append({"lr": lr, "window": f"[{lo},{hi})", "method": name,
                             "weighted_r2": r2, "peak": peak, "diverged": diverged})
            print(f"  lr={lr:.0e} window[{lo},{hi}): "
                  + "  ".join(f"{m.split('[')[0]}={rows[-len(methods)+i]['weighted_r2']:+.4f}"
                                + ("!" if rows[-len(methods)+i]['diverged'] else "")
                                for i, m in enumerate(methods)))
    df = pl.DataFrame(rows)
    df.write_csv(OUT / "normalize_windows.csv")
    # survival summary
    print("\n  survival (fraction of 10 window-runs that stayed bounded):")
    for name in methods:
        sub = df.filter(pl.col("method") == name)
        surv = 1.0 - float(sub["diverged"].mean())
        meanr2 = float(sub.filter(~pl.col("diverged"))["weighted_r2"].mean() or 0.0)
        print(f"    {name:16s} survived {surv*100:.0f}%   mean R2 (when bounded)={meanr2:+.4f}")
    return df


def figure(cont):
    fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.6))
    order = ["ogd", "adaptive_clip", "robust_omd[median_of_means]", "sn_ogd"]
    colors = {"ogd": "#d62728", "adaptive_clip": "#7f7f7f",
              "robust_omd[median_of_means]": "#2ca02c", "sn_ogd": "#1f77b4"}
    labels = {"ogd": "OGD", "adaptive_clip": "AdaptiveClip",
              "robust_omd[median_of_means]": "RobustOMD (MoM)", "sn_ogd": "SN-OGD (ours)"}
    markers = {"ogd": "o", "adaptive_clip": "s", "robust_omd[median_of_means]": "D", "sn_ogd": "^"}
    ax = axes[0]
    for name in order:
        sub = cont.filter(pl.col("method") == name).sort("learning_rate")
        ax.plot(sub["learning_rate"], sub["weighted_r2"], color=colors[name],
                marker=markers[name], ms=3.5, label=labels[name])
    ax.set_xscale("log"); ax.set_ylim(-0.10, 0.20)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("learning rate"); ax.set_ylabel(r"weighted $R^2$")
    ax.set_title("(a) Accuracy vs. learning rate")
    ax.legend(loc="lower center", fontsize=6)
    ax = axes[1]
    for name in order:
        sub = cont.filter(pl.col("method") == name).sort("learning_rate")
        ax.plot(sub["learning_rate"], sub["peak_rolling_loss"], color=colors[name],
                marker=markers[name], ms=3.5, label=labels[name])
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.axhspan(0, 6, color="#2ca02c", alpha=0.08)
    ax.set_xlabel("learning rate"); ax.set_ylabel("peak rolling loss")
    ax.set_title("(b) Stability vs. learning rate")
    fig.savefig(OUT / "fig_normalize.png"); plt.close(fig)
    print("\n  wrote results/research/fig_normalize.png")


def main():
    cont = test_continuous()
    test_windows()
    figure(cont)
    print(f"\nFindings written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
