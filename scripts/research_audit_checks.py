"""Audit verification runs (A3 reproduction, A7 block-tracker stability).

A3  Reproduce Table 3 / Sec 4.3: W_s vs block length B on the real gradient-scale
    process. Reports the ACTUAL round count, W_s(full), the per-update ratio W_s/(N/B),
    the linear-fit slope of W_s-vs-update-count (+R^2), and beta restricted to horizons
    with >=50 blocks. (The npy is 200k rounds, not 357k -- fixes the text.)

A7  Run SN-OMD with a B=1e4 block-median scale tracker through the learning-rate sweep on
    the continuous Jane stream and confirm it does not destabilize (peak rolling loss),
    versus the default winsorized-EMA tracker. Reports R^2, peak loss, and lower bracket.

Usage: python scripts/research_audit_checks.py [--a7]
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"


def block_scale(g, B, c=1.0):
    n = g.size
    s = np.empty(n); cur = float(np.median(g[:B])) * c
    for st in range(0, n, B):
        s[st:min(st + B, n)] = cur; cur = c * float(np.median(g[st:st + B]))
    return s


def a3():
    g = np.load(RES / "gradnorm_at_wstar.npy"); g = g[np.isfinite(g) & (g > 0)]; n = g.size
    print("=" * 74)
    print(f"A3 -- W_s vs block length B.  ACTUAL round count N = {n:,}  (paper says 357k!)")
    print("=" * 74)
    grid = np.unique(np.geomspace(3000, n - 1, 60).astype(int))
    print(f"  {'B':>6} {'W_s(full)':>10} {'k=N/B':>8} {'W_s/k':>7} {'fit slope':>9} {'fitR2':>6} {'beta(>=50blk)':>13}")
    for B in [1, 100, 1000, 3000, 10000]:
        s = block_scale(g, B); inc = np.diff(s, prepend=s[0]); Wsfull = float(s[0] + np.maximum(inc, 0).sum())
        bnds = list(range(B, n, B)); prev = float(np.median(g[:B])); acc = prev; ws = []
        for st in bnds:
            m = float(np.median(g[st - B:st])); acc += max(m - prev, 0.0); prev = m; ws.append(acc)
        k = np.arange(1, len(ws) + 1)
        sl, r2 = (np.polyfit(k, ws, 1)[0], np.corrcoef(k, ws)[0, 1] ** 2) if len(ws) >= 2 else (np.nan, np.nan)
        # beta from log-log W_s(T) restricted to horizons with >=50 blocks
        Wc = s[0] + np.cumsum(np.maximum(inc, 0.0)); WT = Wc[grid]
        mask = (grid / B >= 50) & (WT > 0)
        beta = np.polyfit(np.log(grid[mask].astype(float)), np.log(WT[mask]), 1)[0] if mask.sum() >= 4 else np.nan
        print(f"  {B:>6} {Wsfull:>10.0f} {n/B:>8.1f} {Wsfull/(n/B):>7.2f} {sl:>9.3f} {r2:>6.3f} "
              f"{beta:>13.2f}".replace("nan", "  n/a"))
    print("  => B=1 is a per-round-jitter outlier (~5.7x); for B>=100 W_s is linear in the")
    print("     update count (slope ~1.7, R^2~0.98-0.99); beta(>=50blk) ~ 1.0-1.25, no trend.")


def a7():
    from research_normalize import ScaleNormalizedOGD, rolling_max_loss
    from dfsl import JaneStreetDataset
    from dfsl.evaluation.metrics import weighted_r2

    class BlockSNOGD(ScaleNormalizedOGD):
        """SN-OMD whose scale is a predictable per-block median of ||g|| (block length B)."""
        def __init__(self, dim, learning_rate=0.1, cap=5.0, B=10000):
            super().__init__(dim=dim, learning_rate=learning_rate, cap=cap)
            self.B = B; self._buf = []; self._block_scale = None

        def update(self, x, y, weight=1.0):
            self.t += 1
            pred = self.predict(x)
            with np.errstate(over="ignore", invalid="ignore"):
                err = np.float64(pred) - np.float64(y); loss = float(np.float64(weight) * err * err)
                g = 2.0 * weight * err * x
            gn = float(np.linalg.norm(g))
            if not np.isfinite(gn):
                return loss
            s = self._block_scale if self._block_scale is not None else max(gn, 1e-8)
            self._buf.append(gn)
            if len(self._buf) >= self.B:
                self._block_scale = max(float(np.median(self._buf)), 1e-8); self._buf = []
            s = max(s, 1e-8); ghat = g / s; gnn = float(np.linalg.norm(ghat))
            if gnn > self.cap:
                ghat = ghat * (self.cap / gnn)
            if np.isfinite(ghat).all():
                self.weights -= (self.lr / np.sqrt(self.t)) * ghat
            return loss

    def run(learner, rows):
        preds, tg, wt, ls = [], [], [], []
        for x, y, w in rows:
            preds.append(learner.predict(x)); tg.append(y); wt.append(w); ls.append(learner.update(x, y, w))
        return types.SimpleNamespace(predictions=np.asarray(preds), targets=np.asarray(tg),
                                     weights=np.asarray(wt), losses=np.asarray(ls))

    def fold_r2(t, p, w, K=10):
        """Paired per-fold weighted R^2 (contiguous folds) -> a band on deterministic data."""
        idx = np.array_split(np.arange(t.size), K)
        return np.array([weighted_r2(t[i], p[i], w[i]) for i in idx])

    print("\n" + "=" * 78)
    print("A7 -- block-tracker SN-OMD across the FULL lr sweep (extended to 5, 10).")
    print("      Stress-test: is lr=2 the sweep edge? does block>EMA hold off-boundary?")
    print("=" * 78)
    ds = JaneStreetDataset(date_range=(0, 120), max_rows=150000, standardize=True)
    rows = [(ds.X[i], float(ds.y[i]), float(ds.weights[i])) for i in range(len(ds.y))]
    dim = ds.X.shape[1]
    print(f"  {len(rows)} rows, dim={dim} (DETERMINISTIC real data: no seed -> band is over folds)")
    print(f"  {'lr':>6} {'block R2':>9} {'block peak':>11} {'EMA R2':>8} {'EMA peak':>9} {'blk-EMA':>8}")
    lrs = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
    store = {}
    for lr in lrs:
        rb = run(BlockSNOGD(dim=dim, learning_rate=lr, cap=5.0, B=10000), iter(rows))
        re = run(ScaleNormalizedOGD(dim=dim, learning_rate=lr, cap=5.0), iter(rows))
        r2b = weighted_r2(rb.targets, rb.predictions, rb.weights)
        r2e = weighted_r2(re.targets, re.predictions, re.weights)
        store[lr] = (rb, re, r2b, r2e)
        print(f"  {lr:>6} {r2b:>9.4f} {rolling_max_loss(rb.losses):>11.1f} "
              f"{r2e:>8.4f} {rolling_max_loss(re.losses):>9.1f} {r2b - r2e:>8.4f}")
    lr_b = max(lrs, key=lambda k: store[k][2]); lr_e = max(lrs, key=lambda k: store[k][3])
    print(f"  => block argmax lr = {lr_b} (peak {'INTERIOR' if lr_b not in (lrs[0], lrs[-1]) else 'ON BOUNDARY'}); "
          f"EMA argmax lr = {lr_e}")
    print(f"     max peak-rolling-loss over the whole sweep: "
          f"block={max(rolling_max_loss(store[k][0].losses) for k in lrs):.1f}, "
          f"EMA={max(rolling_max_loss(store[k][1].losses) for k in lrs):.1f}")

    # Paired fold band: is block>EMA a robust sign, or one lucky aggregate?
    print("  paired 10-fold weighted-R2 band (block - EMA), at lr=2 and at each method's best lr:")
    for tag, lr in [("lr=2.0", 2.0), (f"block@{lr_b}/EMA@{lr_e}", None)]:
        if lr is None:
            fb = fold_r2(store[lr_b][0].targets, store[lr_b][0].predictions, store[lr_b][0].weights)
            fe = fold_r2(store[lr_e][1].targets, store[lr_e][1].predictions, store[lr_e][1].weights)
        else:
            fb = fold_r2(store[lr][0].targets, store[lr][0].predictions, store[lr][0].weights)
            fe = fold_r2(store[lr][1].targets, store[lr][1].predictions, store[lr][1].weights)
        d = fb - fe
        print(f"    {tag:20s} mean gap={d.mean():+.4f}  std={d.std():.4f}  "
              f"folds block>EMA: {int((d > 0).sum())}/{len(d)}")


if __name__ == "__main__":
    a3()
    if "--a7" in sys.argv:
        a7()
