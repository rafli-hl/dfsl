"""Second-round reviewer checks (run off saved artifacts).

Item 2  Does W_s / V_sigma^+ grow with the horizon? Theorem 3.3's simplification
        W_s = O(sup sigma) -> "drift enters as a constant, not a rate" is only true if
        the upward scale variation does not accumulate with T. Fit the growth exponent.

Item 4  Self-normalization control on the alpha 2.4 -> 3.7 headline. ||g||/s_t is a
        self-normalized statistic; check the tail lightening survives (a) a non-causal
        centered-median scale (cleaner sigma_t) and (b) an EXOGENOUS scale (feature norm
        ||x||, which does not see the residual/weight factors of ||g||).

Item 1b Bootstrap the dynamic-budget growth exponent over sampled days, and report what
        happens if the per-regime tail index is p_r ~ 2 (the normalized-gradient regime).

Usage: python scripts/research_review2_checks.py
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
    if k <= 0 or a[k] <= 0:
        return float("nan")
    return 1.0 / float(np.mean(np.log(a[:k]) - np.log(a[k])))


def causal_ema(g, decay=0.99, winsor=8.0):
    s = np.empty_like(g)
    cur = g[0]
    for i, v in enumerate(g):
        s[i] = cur
        cur = decay * cur + (1 - decay) * min(v, winsor * cur)
    return s


def centered_ema(g, decay=0.99, winsor=8.0):
    """Non-causal counterpart of causal_ema: same winsorized-EMA estimator run
    forward AND backward, combined by geometric mean. Isolates the *causality*
    axis (it sees the future) while holding the estimator, decay, and
    winsorization fixed."""
    fwd = causal_ema(g, decay, winsor)
    bwd = causal_ema(g[::-1], decay, winsor)[::-1]
    return np.sqrt(fwd * bwd)


def upward_variation_curve(x, grid):
    """Cumulative upward variation W(T) = x[0] + sum_{t<=T} (x_t - x_{t-1})_+ at horizons."""
    inc = np.diff(x, prepend=x[0])
    up = np.maximum(inc, 0.0)
    cum = x[0] + np.cumsum(up)
    return cum[grid]


def fit_slope(T, y):
    m = (y > 0) & np.isfinite(y) & (T > 0)
    return float(np.polyfit(np.log(T[m]), np.log(y[m]), 1)[0])


def item2_variation_growth():
    print("=" * 70)
    print("ITEM 2 -- does W_s / V_sigma^+ grow with horizon T?")
    print("=" * 70)
    g = np.load(RES / "gradnorm_at_wstar.npy")
    g = g[np.isfinite(g) & (g > 0)]
    N = g.size
    # ground-truth scale: centered (non-causal) rolling median, window 1001
    W = 1001
    s_true = pl.Series(g).rolling_median(window_size=W, center=True, min_samples=1).to_numpy()
    s_ema = causal_ema(g)
    grid = np.unique(np.geomspace(2000, N - 1, 40).astype(int))
    V_true = upward_variation_curve(s_true, grid)
    W_ema = upward_variation_curve(s_ema, grid)
    b_true = fit_slope(grid.astype(float), V_true)
    b_ema = fit_slope(grid.astype(float), W_ema)
    print(f"  N={N},  V_sigma^+ (non-causal median) growth exponent  beta = {b_true:.3f}")
    print(f"           W_s (causal EMA tracker)      growth exponent  beta = {b_ema:.3f}")
    print(f"  (beta=0 => bounded/constant; beta=1 => linear accumulation)")
    print(f"  V_sigma^+ at T={grid[0]}: {V_true[0]:.0f}   at T={grid[-1]}: {V_true[-1]:.0f}"
          f"   ratio {V_true[-1]/V_true[0]:.1f}x for {grid[-1]/grid[0]:.0f}x horizon")
    print(f"  => with sqrt(W_s) in the bound, p=2 effective rate ~ T^{{{(1+b_ema)/2:.2f}}} "
          f"(sqrt-T iff beta=0)")


def item4_selfnorm_control():
    print("\n" + "=" * 70)
    print("ITEM 4 -- self-normalization control on alpha 2.4 -> 3.7")
    print("=" * 70)
    g = np.load(RES / "gradnorm_at_wstar.npy")
    xn = np.load(RES / "featurenorm.npy")
    m = np.isfinite(g) & (g > 0) & np.isfinite(xn) & (xn > 0)
    g, xn = g[m], xn[m]
    fracs = [0.005, 0.01, 0.02]

    def rep(name, x):
        xs = x[np.isfinite(x) & (x > 0)]
        print(f"  {name:42s} " + "  ".join(f"k={f}:{hill(xs,int(f*xs.size)):.2f}" for f in fracs))

    rep("raw ||g|| (pooled)", g)
    # --- deployed causal tracker vs its non-causal twin (isolates causality) ---
    rep("||g|| / causal winsorized-EMA (deployed)", (g / np.maximum(causal_ema(g), 1e-12))[200:-200])
    rep("||g|| / centered winsorized-EMA (non-causal twin)", (g / np.maximum(centered_ema(g), 1e-12))[200:-200])
    # --- trailing vs centered median (same estimator, isolates causality) ---
    s_tmed = pl.Series(g).rolling_median(window_size=1001, center=False, min_samples=1).to_numpy()
    s_med = pl.Series(g).rolling_median(window_size=1001, center=True, min_samples=1).to_numpy()
    rep("||g|| / trailing median (causal)", (g / np.maximum(s_tmed, 1e-12))[200:-200])
    rep("||g|| / centered median (non-causal)", (g / np.maximum(s_med, 1e-12))[200:-200])
    # exogenous: divide by feature-norm scale (EMA of ||x||), which does not see residual/weight
    rep("||g|| / EMA(||x||)  (exogenous scale)", (g / np.maximum(causal_ema(xn), 1e-12))[200:])
    rep("feature norm ||x|| (reference)", xn)


def item1_budget_bootstrap():
    print("\n" + "=" * 70)
    print("ITEM 1b -- bootstrap the dynamic-budget growth exponent")
    print("=" * 70)
    d = pl.read_csv(RES / "heavybudget_daily.csv").filter(pl.col("hill_alpha").is_finite()).sort("date_id")
    n = d["n"].to_numpy().astype(float)
    a = d["hill_alpha"].to_numpy()
    stride = 13

    def budget_exponent(alpha):
        heavy = alpha < 2.0
        per = np.where(heavy, n ** (1.0 / np.maximum(alpha, 1e-6)), 0.0)
        cb = stride * np.cumsum(per)
        ct = stride * np.cumsum(n)
        mask = cb > 0
        if mask.sum() < 5:
            return np.nan
        return float(np.polyfit(np.log(ct[mask]), np.log(cb[mask]), 1)[0])

    base = budget_exponent(a)
    # Hill SE ~ alpha/sqrt(k); k ~ min(500, n/10). Perturb per-day alpha and refit.
    k = np.minimum(500, n / 10)
    se = a / np.sqrt(np.maximum(k, 1))
    rng = np.random.default_rng(0)
    exps = [budget_exponent(a + rng.normal(0, se)) for _ in range(500)]
    exps = np.array([e for e in exps if np.isfinite(e)])
    print(f"  pooled-gradient budget exponent = {base:.3f}  "
          f"(bootstrap {exps.mean():.3f} +/- {exps.std():.3f})")
    frac_sub2 = float(np.mean(a < 2.0))
    print(f"  fraction of days with pooled alpha<2: {100*frac_sub2:.0f}%")
    # normalized-gradient regime: p_r ~ 2 everywhere -> no heavy days -> budget ~ 0 heavy mass
    print("  If per-regime p_r ~ 2 (normalized gradients, alpha~3.7): no alpha<2 regimes,")
    print("  so the heavy budget collapses to the light-tailed sqrt(N T) inflation")
    print("  (exponent 0.5) -- i.e. the super-sqrt-T growth is entirely a pooled-tail effect.")


if __name__ == "__main__":
    item2_variation_growth()
    item4_selfnorm_control()
    item1_budget_bootstrap()
