"""Jane Street M-sweep + endpoints, causal standardization.

Provides the numbers the reframed paper needs: SN-OMD across a range of caps M
(M->0 == normalized-GD, M->inf == uncapped scale-adaptive OGD), plus the two
endpoints as first-class baselines, on the continuous multi-regime stream. Each
config is tuned over a small learning-rate grid (best weighted R^2), because M and
the learning rate both scale the step. Uses the same ScaleNormalizedOGD as
research_normalize.py; standardization is now causal (no look-ahead).

Usage:  python scripts/research_jane_msweep.py
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_normalize import ScaleNormalizedOGD, make_learner, rolling_max_loss  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402
from dfsl.evaluation.metrics import weighted_r2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "research"


class NormalizedGD:
    """w_{t+1} = w_t - (lr/sqrt t) g_t/||g_t||  (the M->0 endpoint)."""

    def __init__(self, dim, learning_rate=0.1):
        self.weights = np.zeros(dim)
        self.lr = learning_rate
        self.t = 0

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
        if np.isfinite(gn) and gn > 0:
            self.weights -= (self.lr / np.sqrt(self.t)) * (g / gn)
        return loss

    def run(self, stream):
        preds, tgts, wts, losses = [], [], [], []
        for x, y, w in stream:
            preds.append(self.predict(x))
            tgts.append(y)
            wts.append(w)
            losses.append(self.update(x, y, w))
        return types.SimpleNamespace(
            predictions=np.asarray(preds), targets=np.asarray(tgts),
            weights=np.asarray(wts), losses=np.asarray(losses),
        )


def evaluate(make, stream_rows, lr_grid):
    """Best weighted R^2 among NON-diverged lrs, plus the largest stable lr."""
    best = {"weighted_r2": -np.inf, "lr": None, "peak": np.inf}
    stable_lr_max = 0.0
    for lr in lr_grid:
        learner = make(lr)
        r = learner.run(iter(stream_rows))
        r2 = float(weighted_r2(r.targets, r.predictions, r.weights))
        peak = rolling_max_loss(r.losses)
        diverged = (not np.isfinite(r2)) or peak > 100.0
        if not diverged:
            stable_lr_max = max(stable_lr_max, float(lr))
            if r2 > best["weighted_r2"]:
                best = {"weighted_r2": r2, "lr": float(lr), "peak": float(peak)}
    best["stable_lr_max"] = stable_lr_max
    best["diverged"] = best["lr"] is None
    return best


def main():
    print("Loading continuous stream date[0,120) with CAUSAL standardization ...")
    ds = JaneStreetDataset(date_range=(0, 120), max_rows=150000, standardize=True)
    rows = [(ds.X[i], float(ds.y[i]), float(ds.weights[i])) for i in range(len(ds.y))]
    dim = ds.X.shape[1]
    lr_grid = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
    print(f"  {len(rows)} rows, dim={dim}")

    out = []
    # baselines on the SAME slice + lr grid (for a consistent Table 1)
    print("\nBaselines:")
    for name in ("ogd", "adaptive_clip", "robust_omd[median_of_means]"):
        b = evaluate(lambda lr, n=name: make_learner(n, dim, lr), rows, lr_grid)
        print(f"  {name:30s} R2={b['weighted_r2']:.4f} @lr={b['lr']}  peak={b['peak']:.1f}  div={b['diverged']}")
        out.append({"kind": "baseline", "method": name, "M": None, **b})

    # M-sweep for SN-OMD
    print("\nM-sweep (SN-OMD, cap M):")
    for M in [0.5, 1.0, 2.0, 5.0, 10.0, 30.0]:
        b = evaluate(lambda lr, M=M: ScaleNormalizedOGD(dim=dim, learning_rate=lr, cap=M), rows, lr_grid)
        print(f"  M={M:5.1f}  R2={b['weighted_r2']:.4f} @lr={b['lr']}  peak={b['peak']:.1f}")
        out.append({"kind": "msweep", "M": M, **b})

    # endpoints
    print("\nEndpoints:")
    b = evaluate(lambda lr: NormalizedGD(dim=dim, learning_rate=lr), rows, lr_grid)
    print(f"  normalized-GD (M->0)         R2={b['weighted_r2']:.4f} @lr={b['lr']}  peak={b['peak']:.1f}")
    out.append({"kind": "normgd", "M": 0.0, **b})
    b = evaluate(lambda lr: ScaleNormalizedOGD(dim=dim, learning_rate=lr, cap=1e9), rows, lr_grid)
    print(f"  scale-adaptive OGD (M->inf)  R2={b['weighted_r2']:.4f} @lr={b['lr']}  peak={b['peak']:.1f}")
    out.append({"kind": "uncapped", "M": np.inf, **b})

    pl.DataFrame(out).write_csv(OUT / "jane_msweep.csv")
    print(f"\nwrote {OUT.relative_to(ROOT)}/jane_msweep.csv")


if __name__ == "__main__":
    main()
