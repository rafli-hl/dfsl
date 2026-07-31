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


def cmp_normgd():
    """CMP -- does the block-median tracker beat *normalized-GD* (the M->0 baseline the
    paper concedes it "ties"), per-row AND per-step, judged on a paired 10-fold band?

    Table 1 concedes SN-OMD(EMA) ~= normalized-GD on real data. But the block tracker
    reaches R^2~0.38 per-row. If block>normGD with a supporting band, the "ties" framing
    understates the method against the very baseline that motivated the repositioning. If
    it is inside the fold noise, "comparable" stands and we say so explicitly. Per-step
    (where normGD is strongest, 0.316) is the protective check.
    """
    from research_normalize import ScaleNormalizedOGD  # noqa: F401  (import parity)
    from dfsl import JaneStreetDataset
    from dfsl.evaluation.metrics import weighted_r2

    def norm(v):
        return float(np.linalg.norm(v))

    def perrow_preds(X, y, wts, method, lr, B=10000, cap=5.0):
        d = X.shape[1]; w = np.zeros(d); s = None; buf = []; blk = None; k = 0
        preds = np.empty(len(y))
        for i in range(len(y)):
            with np.errstate(over="ignore", invalid="ignore"):
                pred = float(w @ X[i]); preds[i] = pred; k += 1
                g = 2.0 * wts[i] * (pred - y[i]) * X[i]
            gn = norm(g)
            if not np.isfinite(gn) or gn == 0:
                continue
            if method == "normgd":
                w -= (lr / np.sqrt(k)) * (g / gn); continue
            if method == "ema":
                s = gn if s is None else 0.99 * s + 0.01 * min(gn, 8.0 * s)
                sc = max(s, 1e-8)
            else:  # block
                sc = blk if blk is not None else max(gn, 1e-8)
                buf.append(gn)
                if len(buf) >= B:
                    blk = max(float(np.median(buf)), 1e-8); buf = []
                sc = max(sc, 1e-8)
            ghat = g / sc; gnn = norm(ghat)
            if gnn > cap:
                ghat = ghat * (cap / gnn)
            if np.isfinite(ghat).all():
                w -= (lr / np.sqrt(k)) * ghat
        return preds

    def batched_preds(X, y, wts, starts, method, lr, Bg=None, cap=5.0):
        d = X.shape[1]; w = np.zeros(d); s = None; buf = []; blk = None
        ends = np.append(starts[1:], len(y)); preds = np.empty(len(y))
        for k, (a, b) in enumerate(zip(starts, ends), start=1):
            with np.errstate(over="ignore", invalid="ignore"):
                p = X[a:b] @ w; preds[a:b] = p
                g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
            gn = norm(g)
            if not np.isfinite(gn) or gn == 0:
                continue
            if method == "normgd":
                w -= (lr / np.sqrt(k)) * (g / gn); continue
            if method == "ema":
                s = gn if s is None else 0.99 * s + 0.01 * min(gn, 8.0 * s)
                sc = max(s, 1e-8)
            else:
                sc = blk if blk is not None else max(gn, 1e-8)
                buf.append(gn)
                if len(buf) >= Bg:
                    blk = max(float(np.median(buf)), 1e-8); buf = []
                sc = max(sc, 1e-8)
            ghat = g / sc; gnn = norm(ghat)
            if gnn > cap:
                ghat = ghat * (cap / gnn)
            if np.isfinite(ghat).all():
                w -= (lr / np.sqrt(k)) * ghat
        return preds

    def fold_band(y, preds, wts, K=10):
        idx = np.array_split(np.arange(y.size), K)
        return np.array([weighted_r2(y[i], preds[i], wts[i]) for i in idx])

    def tuned(runner, methods, lrs, *extra):
        best = {}
        for m in methods:
            r2s = {lr: weighted_r2(y, runner(X, y, wts, *extra, m, lr), wts) for lr in lrs}
            lr_star = max(r2s, key=r2s.get)
            best[m] = (lr_star, r2s[lr_star])
        return best

    def report_pair(tag, y, pa, pb, wts, name_a, name_b):
        """Paired fold band a-b with SE, t and a two-sided sign test."""
        fa = fold_band(y, pa, wts); fb = fold_band(y, pb, wts); dgap = fa - fb
        K = len(dgap); mean = dgap.mean(); sd = dgap.std(ddof=1)
        se = sd / np.sqrt(K); t = mean / se if se > 0 else np.nan
        wins = int((dgap > 0).sum())
        # exact two-sided sign test p-value (binomial, p=0.5)
        from math import comb
        k = max(wins, K - wins)
        p = min(1.0, 2.0 * sum(comb(K, j) for j in range(k, K + 1)) / 2 ** K)
        print(f"    {tag:16s} {name_a}-{name_b}: mean={mean:+.4f} sd={sd:.4f} "
              f"se={se:.4f} t={t:+.2f}  {name_a}>{name_b}: {wins}/{K} (sign p={p:.3f})")

    print("\n" + "=" * 82)
    print("CMP -- block-median tracker vs normalized-GD (and EMA), per-row AND per-step,")
    print("       each at its own tuned lr, judged on a PAIRED 10-fold band.")
    print("=" * 82)
    ds = JaneStreetDataset(date_range=(0, 120), max_rows=150000, standardize=True)
    X, y, wts = ds.X, ds.y, ds.weights
    d = ds.meta["date_id"].to_numpy().astype(np.int64)
    tk = ds.meta["time_id"].to_numpy().astype(np.int64)
    key = d * (tk.max() + 1) + tk
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    rows_per_group = len(y) / len(starts)
    ndays = int(np.unique(d).size)
    groups_per_day = max(1, int(round(len(starts) / max(ndays, 1))))
    print(f"  {len(y)} rows, {len(starts)} (date,time) groups, {rows_per_group:.1f} rows/group, "
          f"{ndays} days, ~{groups_per_day} groups/day (batched block size)")

    lrs = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
    methods = ["normgd", "ema", "block"]

    print("\n  PER-ROW, each method at its tuned lr:")
    br = tuned(perrow_preds, methods, lrs)
    for m in methods:
        print(f"    {m:8s} lr*={br[m][0]:<4}  R2={br[m][1]:+.4f}")
    pr = {m: perrow_preds(X, y, wts, m, br[m][0]) for m in methods}
    report_pair("per-row", y, pr["block"], pr["normgd"], wts, "block", "normgd")
    report_pair("per-row", y, pr["block"], pr["ema"], wts, "block", "ema")
    report_pair("per-row", y, pr["ema"], pr["normgd"], wts, "ema", "normgd")

    print("\n  PER-STEP (batched by (date,time)), each method at its tuned lr:")
    bb = tuned(batched_preds, ["normgd", "ema"], lrs, starts)  # block needs Bg -> separate
    r2s = {lr: weighted_r2(y, batched_preds(X, y, wts, starts, "block", lr, Bg=groups_per_day), wts)
           for lr in lrs}
    bb["block"] = (max(r2s, key=r2s.get), max(r2s.values()))
    for m in methods:
        print(f"    {m:8s} lr*={bb[m][0]:<4}  R2={bb[m][1]:+.4f}")
    pb = {"normgd": batched_preds(X, y, wts, starts, "normgd", bb["normgd"][0]),
          "ema": batched_preds(X, y, wts, starts, "ema", bb["ema"][0]),
          "block": batched_preds(X, y, wts, starts, "block", bb["block"][0], Bg=groups_per_day)}
    report_pair("per-step", y, pb["block"], pb["normgd"], wts, "block", "normgd")
    report_pair("per-step", y, pb["block"], pb["ema"], wts, "block", "ema")
    report_pair("per-step", y, pb["ema"], pb["normgd"], wts, "ema", "normgd")


def divthresh():
    """5a -- divisor-vs-threshold, MEASURED (A.8 currently asserts it).

    A.8 claims a lagging scale $s_t$ hurts a THRESHOLD use (clip $\\|g\\|$ at
    $s_t$) but is tolerable for a DIVISOR use ($\\hat g=g/s_t$, cancels
    first-order). We test it directly: use the *same* tracked scale (a
    block-median of $\\|g\\|$ whose block length $B$ IS the window/lag knob --
    long $B$ = more lag at regime onsets) and sweep $B$, comparing downstream
    weighted $R^2$ under the two uses, each at its own tuned lr (the two uses
    live on different step scales, so a shared lr would be unfair). Prediction
    to confirm/refute: divisor $R^2$ ~flat in $B$; threshold $R^2$ falls as $B$
    grows. Real Jane stream, deterministic (no RNG), same load as --cmp.
    """
    from dfsl import JaneStreetDataset
    from dfsl.evaluation.metrics import weighted_r2

    def norm(v):
        return float(np.linalg.norm(v))

    def run(X, y, wts, use, B, lr, cap=5.0):
        d = X.shape[1]; w = np.zeros(d); buf = []; blk = None; k = 0
        preds = np.empty(len(y))
        for i in range(len(y)):
            with np.errstate(over="ignore", invalid="ignore"):
                pred = float(w @ X[i]); preds[i] = pred; k += 1
                g = 2.0 * wts[i] * (pred - y[i]) * X[i]
            gn = norm(g)
            if not np.isfinite(gn) or gn == 0:
                continue
            sc = blk if blk is not None else max(gn, 1e-8)  # predictable: prior block only
            buf.append(gn)
            if len(buf) >= B:
                blk = max(float(np.median(buf)), 1e-8); buf = []
            sc = max(sc, 1e-8)
            if use == "divisor":            # g / s, capped at M -- direction preserved
                step = g / sc; sn = norm(step)
                if sn > cap:
                    step = step * (cap / sn)
            else:                            # threshold: clip ||g|| at s -- lag clips onsets
                step = g if gn <= sc else g * (sc / gn)
            if np.isfinite(step).all():
                w -= (lr / np.sqrt(k)) * step
        return preds

    print("\n" + "=" * 82)
    print("5a -- divisor vs threshold under a window (block timescale B) sweep.")
    print("      Same tracked scale, two uses; each tuned over lr. A.8's claim, measured.")
    print("=" * 82)
    ds = JaneStreetDataset(date_range=(0, 120), max_rows=150000, standardize=True)
    X, y, wts = ds.X, ds.y, ds.weights
    print(f"  {len(y)} rows, dim={X.shape[1]} (DETERMINISTIC real data)")
    Bs = [50, 200, 1000, 5000, 20000]
    # Per-use lr grids: the divisor+cap step is scale-free (best lr ~O(1)); the threshold
    # step is the raw clipped gradient, i.e. scale-DEPENDENT OGD, stable only at small lr
    # (the paper's own clip experiments run at 5e-3..1e-2). Tuning each on its own grid
    # isolates the window-lag SHAPE from that first-order divergence difference.
    lrs = {"divisor": [0.1, 0.2, 0.5, 1.0, 2.0],
           "threshold": [3e-4, 1e-3, 3e-3, 1e-2, 3e-2]}
    print(f"  {'B (window)':>11} {'divisor R2':>11} {'div lr*':>8} {'threshold R2':>13} {'thr lr*':>8}")
    best = {"divisor": [], "threshold": []}
    for B in Bs:
        row = {}
        for use in ("divisor", "threshold"):
            r2s = {lr: weighted_r2(y, run(X, y, wts, use, B, lr), wts) for lr in lrs[use]}
            lr_star = max(r2s, key=r2s.get); row[use] = (r2s[lr_star], lr_star)
            best[use].append(r2s[lr_star])
        print(f"  {B:>11} {row['divisor'][0]:>11.4f} {row['divisor'][1]:>8} "
              f"{row['threshold'][0]:>13.4f} {row['threshold'][1]:>8}")
    dv = np.array(best["divisor"]); th = np.array(best["threshold"])
    print(f"  => divisor  R2 range over B: [{dv.min():.4f}, {dv.max():.4f}]  "
          f"spread {dv.max() - dv.min():.4f}  (short->long: {dv[0]:.3f}->{dv[-1]:.3f})")
    print(f"     threshold R2 range over B: [{th.min():.4f}, {th.max():.4f}]  "
          f"spread {th.max() - th.min():.4f}  (short->long: {th[0]:.3f}->{th[-1]:.3f})")
    print("     A.8 confirmed if threshold degrades with B while divisor stays ~flat.")


if __name__ == "__main__":
    a3()
    if "--a7" in sys.argv:
        a7()
    if "--cmp" in sys.argv:
        cmp_normgd()
    if "--divthresh" in sys.argv:
        divthresh()
