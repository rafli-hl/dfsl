"""Second real market: does the gradient-scale mechanism replicate on crypto? (audit scope item)

The paper's central finding is established on one market (Jane). The audit's highest-value next
step is a SECOND market: if the same mechanism appears on an independent stream with the same
volatility-clustering structure, "predictable scale drift manufactures the pooled heavy tail, and
causal normalization removes it as a property of SERIAL DEPENDENCE" is not Jane-specific.

Stream: Binance BTC/USDT hourly OHLCV, 2017-08..2026-08 (~77k bars, ~9 years), spanning the 2018
bear, the 2020 COVID crash, the 2021 bull run, and the 2022 crash -- genuine regime-level scale
nonstationarity (volatility clustering), NOT a training-schedule artifact like MNIST.

Task, built to mirror Jane exactly:
  * Predict the next-hour log return from causal features (lagged returns, rolling vol, volume,
    intraday seasonality), linear predictor, weighted (here uniform) squared loss.
  * Gradient at the best fixed linear predictor w*:  g_t = 2 omega_t (x_t.w* - y_t) x_t  (as in
    research_findings.probe_intrinsic_gradients), pooled norm ||g_t||.
  * hill_alpha (top-k=2000) and the causal EMA scale tracker (decay=0.99, winsor=8) are the SAME
    estimators the Jane analysis uses.

Diagnostics (pre-committed -- report whichever way it comes out):
  1. pooled ||g|| tail alpha         -- heavy?  (Jane: ~2.4)
  2. / causal-EMA scale tracker      -- lighter?  (the removability claim; Jane: ~2.9-3.7)
  3. / non-causal rolling median     -- lighter still (ground-truth tracker)
  4. order-SHUFFLE control           -- marginal-preserving shuffle must ABOLISH the lightening
                                        (removability is serial dependence, not the marginal)
  5. within-regime drift             -- daily gradient-scale range and a rolling Hill alpha that
                                        dips (the nonstationarity that drives it)

Usage:  .venv/Scripts/python.exe scripts/research_crypto_mechanism.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dfsl.evaluation import best_fixed_linear  # noqa: E402  (same comparator as Jane)

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"
CSV = ROOT / "data" / "raw" / "crypto" / "Binance_BTCUSDT_1h.csv"

DECAY, WINSOR, HILL_K = 0.99, 8.0, 2000


def hill_alpha(x: np.ndarray, k: int = HILL_K) -> float:
    """Hill tail index of |x| from top-k order statistics (identical to research_findings)."""
    a = np.abs(np.asarray(x, dtype=np.float64))
    a = a[np.isfinite(a) & (a > 0)]
    if a.size < k + 2:
        k = max(1, a.size - 2)
    order = np.sort(a)[::-1]
    if k <= 0 or order[k] <= 0:
        return float("nan")
    denom = float(np.mean(np.log(order[:k]) - np.log(order[k])))
    return float("nan") if denom <= 0 else 1.0 / denom


def causal_ema(g: np.ndarray, decay: float = DECAY, winsor: float = WINSOR) -> np.ndarray:
    """Predictable winsorized-EMA scale tracker s_t (uses only the past), as in _step/snomd."""
    s = np.empty_like(g)
    cur = g[0]
    for i, v in enumerate(g):
        s[i] = cur
        cur = decay * cur + (1 - decay) * min(v, winsor * cur)
    return np.maximum(s, 1e-12)


def noncausal_ema(g: np.ndarray, decay: float = DECAY, winsor: float = WINSOR) -> np.ndarray:
    """Centered (non-causal) twin of the SAME winsorized-EMA estimator: geometric mean of the
    forward and backward passes. Isolates CAUSALITY (same estimator, uses the future) exactly as
    Jane's Table 1 'centered EMA (non-causal twin)' row does."""
    fwd = causal_ema(g, decay, winsor)
    bwd = causal_ema(g[::-1], decay, winsor)[::-1]
    return np.maximum(np.sqrt(fwd * bwd), 1e-12)


def _causal_z(a: np.ndarray, warmup: int = 500) -> np.ndarray:
    """Causal z-score: standardize each point by the running mean/std of the strict past."""
    a = np.asarray(a, dtype=np.float64)
    n = a.size
    cs = np.cumsum(a); cs2 = np.cumsum(a * a)
    idx = np.arange(1, n + 1)
    mean = cs / idx
    var = np.maximum(cs2 / idx - mean * mean, 1e-12)
    std = np.sqrt(var)
    # shift by one so point i is standardized by stats of [0, i-1]
    m = np.concatenate([[0.0], mean[:-1]])
    s = np.concatenate([[1.0], std[:-1]])
    z = (a - m) / np.maximum(s, 1e-8)
    z[:warmup] = 0.0
    return z


CSV_URL = "https://www.cryptodatadownload.com/cdd/Binance_BTCUSDT_1h.csv"


def _ensure_csv() -> None:
    """Download the public Binance BTC/USDT 1h OHLCV CSV if not already cached (data/raw is
    gitignored, like the Jane raw data). Source: CryptoDataDownload (documented, reproducible)."""
    if CSV.exists() and CSV.stat().st_size > 1_000_000:
        return
    import requests  # local import: only needed on first run
    CSV.parent.mkdir(parents=True, exist_ok=True)
    print(f"[downloading {CSV_URL} -> {CSV.relative_to(ROOT)}]")
    r = requests.get(CSV_URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    CSV.write_bytes(r.content)


def load_features():
    """Build (X, y, weights, day_id, dt) mirroring Jane's causal, weighted-squared-loss setup."""
    _ensure_csv()
    df = pl.read_csv(CSV, skip_rows=1)  # first line is the CryptoDataDownload URL banner
    df = df.sort("Unix")                # CSV is newest-first; make it chronological
    close = df["Close"].to_numpy().astype(np.float64)
    vol = df["Volume USDT"].to_numpy().astype(np.float64)
    tc = df["tradecount"].to_numpy().astype(np.float64)
    unix = df["Unix"].to_numpy().astype(np.float64)
    # log returns
    r = np.zeros_like(close)
    r[1:] = np.log(np.maximum(close[1:], 1e-12) / np.maximum(close[:-1], 1e-12))

    def roll(a, w):  # trailing (causal) rolling stat via pandas-free cumsum trick
        return pl.Series(a).rolling_std(window_size=w, min_samples=w).to_numpy()

    def rollmean(a, w):
        return pl.Series(a).rolling_mean(window_size=w, min_samples=w).to_numpy()

    vol24 = roll(r, 24); vol168 = roll(r, 168)
    absmean24 = rollmean(np.abs(r), 24)
    logvol = np.log(np.maximum(vol, 1.0)); logtc = np.log(np.maximum(tc, 1.0))
    hour = ((unix / 3.6e6) % 24)  # unix is in ms
    feats = {
        "r1": r, "r2": np.roll(r, 1), "r3": np.roll(r, 2), "r4": np.roll(r, 3),
        "r6": np.roll(r, 5), "vol24": vol24, "vol168": vol168, "absmean24": absmean24,
        "logvol_z": _causal_z(logvol), "logtc_z": _causal_z(logtc),
        "hour_sin": np.sin(2 * np.pi * hour / 24), "hour_cos": np.cos(2 * np.pi * hour / 24),
    }
    # standardize the return/vol features causally (features must not leak scale); seasonals kept
    for kf in ["r1", "r2", "r3", "r4", "r6", "vol24", "vol168", "absmean24"]:
        feats[kf] = _causal_z(np.nan_to_num(feats[kf], nan=0.0))
    cols = list(feats)
    X = np.column_stack([feats[c] for c in cols])
    X = np.column_stack([X, np.ones(X.shape[0])])  # intercept
    y = np.roll(r, -1)                              # target = NEXT hour's return
    dt = df["Date"].to_numpy()
    day_id = (unix // 86_400_000).astype(np.int64)   # calendar day index
    # drop warmup (rolling-168 + causal-z warmup) and the last row (no next return)
    lo, hi = 700, len(y) - 1
    keep = slice(lo, hi)
    w = np.ones(hi - lo)
    return (X[keep], y[keep], w, day_id[keep], dt[keep], cols)


def grad_norm_at(X, y, w, v):
    r = X @ v - y
    g = 2.0 * w[:, None] * r[:, None] * X
    return np.linalg.norm(g, axis=1), r


def main() -> None:
    X, y, w, day_id, dt, cols = load_features()
    n = len(y)
    print("=" * 92)
    print(f"CRYPTO SECOND MARKET  BTC/USDT 1h  n={n} bars  {str(dt[0])[:10]}..{str(dt[-1])[:10]}")
    print(f"features ({X.shape[1]}): {cols} + intercept")
    print("=" * 92)

    w_star = best_fixed_linear(X, y, w)
    # sanity: does the linear predictor explain anything? (crypto returns are near-unpredictable)
    ss_res = float(np.sum((X @ w_star - y) ** 2)); ss_tot = float(np.sum((y - y.mean()) ** 2))
    print(f"best-fixed-linear in-sample R^2 = {1 - ss_res/ss_tot:+.4f}  "
          f"(near 0 expected; the point is the gradient SCALE, not predictability)")

    gnorm, resid = grad_norm_at(X, y, w, w_star)
    gnorm0, _ = grad_norm_at(X, y, w, np.zeros(X.shape[1]))
    xnorm = np.linalg.norm(X, axis=1)

    # ---- (1)-(3) pooled vs normalized tails ----
    s_ema = causal_ema(gnorm)
    med = pl.Series(gnorm).rolling_median(window_size=201, center=True, min_samples=1).to_numpy()
    a_pool = hill_alpha(gnorm)
    a_ema = hill_alpha(gnorm[200:] / s_ema[200:])
    a_ema_nc = hill_alpha(gnorm[200:] / noncausal_ema(gnorm)[200:])  # same-estimator non-causal twin
    a_med = hill_alpha(gnorm / np.maximum(med, 1e-12))
    print("\n--- tail index (Hill alpha, k=2000; higher = lighter) ---")
    print(f"  pooled ||g|| @ w*                 alpha = {a_pool:.3f}")
    print(f"  ||g|| / causal-EMA tracker        alpha = {a_ema:.3f}   (removability claim)")
    print(f"  ||g|| / non-causal-EMA twin       alpha = {a_ema_nc:.3f}   (same-estimator; isolates causality, gap {a_ema_nc-a_ema:+.3f})")
    print(f"  ||g|| / non-causal median         alpha = {a_med:.3f}   (different estimator)")
    print(f"  [context] residual @ w* alpha={hill_alpha(resid):.2f}  feature||x|| alpha={hill_alpha(xnorm):.2f}"
          f"  pooled ||g||@0 alpha={hill_alpha(gnorm0):.2f}")

    # ---- (4) order-shuffle control (marginal-preserving) ----
    rng = np.random.default_rng(0)
    a_shuf = []
    for seed in range(5):
        perm = np.random.default_rng(seed).permutation(n)
        gp = gnorm[perm]
        sp = causal_ema(gp)
        a_shuf.append(hill_alpha(gp[200:] / sp[200:]))
    a_shuf = np.array(a_shuf)
    print("\n--- SHUFFLE control (marginal-preserving order shuffle; 5 seeds) ---")
    print(f"  shuffled ||g|| / causal-EMA       alpha = {a_shuf.mean():.3f} +- {a_shuf.std():.3f}")
    print(f"  lightening removed by shuffle?  real d(alpha)={a_ema - a_pool:+.3f}  "
          f"vs shuffled d(alpha)={a_shuf.mean() - a_pool:+.3f}")

    # ---- (5) within-regime drift ----
    days = np.unique(day_id)
    daymed = np.array([np.median(gnorm[day_id == d]) for d in days])
    daymed = daymed[np.isfinite(daymed) & (daymed > 0)]
    drift = float(np.percentile(daymed, 95) / max(np.percentile(daymed, 5), 1e-12))
    # rolling Hill alpha over ~90-day chunks
    chunk = 24 * 90
    roll_alpha = [hill_alpha(gnorm[i:i + chunk], k=500) for i in range(0, n - chunk, chunk)]
    roll_alpha = np.array([a for a in roll_alpha if np.isfinite(a)])
    print("\n--- within-regime nonstationarity ---")
    print(f"  daily gradient-scale drift (p95/p5 of daily medians) = {drift:.1f}x")
    print(f"  rolling 90-day Hill alpha: min={roll_alpha.min():.2f} median={np.median(roll_alpha):.2f} "
          f"max={roll_alpha.max():.2f}  (<2 on {int((roll_alpha<2).sum())}/{roll_alpha.size} windows)")

    # ---- (6) light-innovation surrogate: is the LEFTOVER tail (2.3) genuine or estimation cost? ----
    # Jane's tab:residual answered this with a Gaussian-innovation GARCH surrogate: a stream built
    # to have NO genuine residual tail still reads alpha~3.9-4.5 causally (pure causal-estimation
    # cost), and Jane's real 3.73 sits just BELOW that floor -> no genuine tail. We run the crypto
    # analogue: sigma_t = causal EMA of |return| is crypto's own (predictable) volatility path;
    # feed it Gaussian innovations, r~ = sigma_t*z, and push g~ = 2|r~|*||x|| through the SAME
    # pipeline. If a zero-tail process reads LIGHT causally while real crypto reads 2.26, the
    # leftover is a GENUINE innovation tail (unlike Jane); if the surrogate is also ~2.3, it is
    # estimation cost. (The exogenous ||x|| feature-norm factor is held fixed to the real data.)
    sigma = causal_ema(np.abs(y))
    a_sp, a_sc, a_snc = [], [], []
    for seed in range(5):
        z = np.random.default_rng(100 + seed).standard_normal(n)
        gtil = 2.0 * np.abs(sigma * z) * xnorm
        a_sp.append(hill_alpha(gtil))
        a_sc.append(hill_alpha(gtil[200:] / causal_ema(gtil)[200:]))
        a_snc.append(hill_alpha(gtil[200:] / noncausal_ema(gtil)[200:]))  # same-estimator twin
    a_sp, a_sc, a_snc = np.array(a_sp), np.array(a_sc), np.array(a_snc)
    print("\n--- light-innovation surrogate (Gaussian innov.; zero genuine tail) ---")
    print(f"  surrogate pooled alpha            = {a_sp.mean():.3f} +- {a_sp.std():.3f}")
    print(f"  surrogate / causal-EMA (FLOOR)    = {a_sc.mean():.3f} +- {a_sc.std():.3f}   "
          f"(estimation-cost floor: a zero-tail stream read causally)")
    print(f"  surrogate / non-causal-EMA twin   = {a_snc.mean():.3f} +- {a_snc.std():.3f}   "
          f"(SAME estimator; causal->non-causal gap {a_snc.mean()-a_sc.mean():+.3f} = causal cost is cheap)")
    print(f"  real causal-normalized = {a_ema:.3f} vs floor {a_sc.mean():.3f}: "
          f"{'real is HEAVIER than the zero-tail floor -> GENUINE residual tail' if a_ema < a_sc.mean() - a_sc.std() else 'real ~ floor -> estimation cost (as on Jane)'}")
    print(f"  same-estimator causal->non-causal gaps: surrogate {a_snc.mean()-a_sc.mean():+.3f}, "
          f"real {a_ema_nc-a_ema:+.3f}  (Jane's real gaps +0.14..+0.38, tab:residual)")

    # ---- save ----
    np.save(RES / "gradnorm_crypto_btc.npy", gnorm)
    rows = [
        {"quantity": "pooled||g||@w*", "hill_alpha": round(a_pool, 4)},
        {"quantity": "||g||/causal-EMA", "hill_alpha": round(a_ema, 4)},
        {"quantity": "||g||/noncausal-EMA-twin", "hill_alpha": round(a_ema_nc, 4)},
        {"quantity": "||g||/noncausal-median", "hill_alpha": round(a_med, 4)},
        {"quantity": "||g||/causal-EMA SHUFFLED", "hill_alpha": round(float(a_shuf.mean()), 4)},
        {"quantity": "residual@w*", "hill_alpha": round(hill_alpha(resid), 4)},
        {"quantity": "feature||x||", "hill_alpha": round(hill_alpha(xnorm), 4)},
        {"quantity": "surrogate pooled (Gaussian innov)", "hill_alpha": round(float(a_sp.mean()), 4)},
        {"quantity": "surrogate/causal-EMA (est-cost floor)", "hill_alpha": round(float(a_sc.mean()), 4)},
        {"quantity": "surrogate/noncausal-EMA-twin", "hill_alpha": round(float(a_snc.mean()), 4)},
    ]
    pl.DataFrame(rows).write_csv(RES / "crypto_mechanism.csv")
    print(f"\n[saved {(RES/'crypto_mechanism.csv').relative_to(ROOT)}, gradnorm_crypto_btc.npy]")
    print("\nVERDICT: mechanism replicates iff pooled alpha is heavy, the causal-EMA normalization")
    print("lightens it, AND the shuffle ABOLISHES that lightening (serial dependence, not marginal).")


if __name__ == "__main__":
    main()
