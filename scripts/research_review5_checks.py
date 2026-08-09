"""Fifth-round check -- the estimator null the earlier passes never ran.

Every tail control so far (review..review4) normalizes REAL Jane gradients, which
already contain scale drift. So none can separate the two explanations for the
alpha 2.4 -> ~3 lightening:

  (H1, thesis)   the pooled tail is MANUFACTURED by slow scale drift, and dividing
                 by a tracked scale removes it;
  (H0, artifact) dividing any series by a lagged robust scale mechanically lightens
                 its ESTIMATED Hill tail, drift or not.

The decisive test is a synthetic null: feed the SAME causal pipeline (winsorized-EMA
tracker, decay=0.99 winsor=8; and trailing-median) two streams with the SAME heavy
pooled marginal (Hill alpha ~ 2.4), differing only in WHY they are heavy:

  STATIONARY-HEAVY (null)   : iid |Student-t(nu=2.4)|.  Genuinely heavy, NO drift.
                              Current draw is independent of the predictable (lag-only)
                              scale, so a faithful normalizer must leave alpha ~ 2.4.
  DRIFT-MANUFACTURED (pos.)  : g_t = sigma_t * |N(0,1)|, sigma_t piecewise-constant over
                              regimes with regime scale ~ Pareto(2.4).  Light within a
                              regime; the pooled tail is PURE drift.  A tracker that can
                              follow sigma_t should lighten it toward alpha -> large.

Reading:
  H1 holds  <=>  null alpha stays ~2.4  AND  drift alpha rises.
  H0 (the review's worry) would show up as the NULL alpha also rising to ~3.

We also sweep regime length L: the lightening of the drift stream must switch OFF when
regimes are shorter than the tracker can follow (fast drift), which is the signature of
a faithful tracker rather than a mechanical artifact.

Runs standalone (no raw data). Usage: python scripts/research_review5_checks.py
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
sys.path.insert(0, str(ROOT / "src"))

from dfsl.preprocessing import OnlineScaleTracker  # noqa: E402

N = 200_000  # match the ~200k gradients at w* used in the paper
WARMUP = 500  # drop tracker warm-up before estimating the tail
FRACS = (0.005, 0.01, 0.02, 0.05, 0.10)  # Hill-threshold fractions (as in check2)
SEEDS = tuple(range(12))
TARGET_ALPHA = 2.4


def hill_alpha(a: np.ndarray, k: int) -> float:
    """Hill tail-index estimate from the top-k order statistics (as in check2)."""
    a = np.sort(a[np.isfinite(a) & (a > 0)])[::-1]
    k = min(k, a.size - 2)
    if k <= 0 or a[k] <= 0:
        return float("nan")
    return 1.0 / float(np.mean(np.log(a[:k]) - np.log(a[k])))


def hill_curve(x: np.ndarray) -> np.ndarray:
    xs = x[np.isfinite(x) & (x > 0)]
    return np.array([hill_alpha(xs, int(f * xs.size)) for f in FRACS])


# ----------------------------------------------------------------------------- streams
def gen_stationary_heavy(n: int, rng: np.random.Generator) -> np.ndarray:
    """iid |Student-t(nu=TARGET_ALPHA)|: genuinely heavy (tail index = nu), no drift."""
    return np.abs(rng.standard_t(df=TARGET_ALPHA, size=n))


def gen_drift_manufactured(n: int, regime_len: int, rng: np.random.Generator) -> np.ndarray:
    """g_t = sigma_t * |N(0,1)| with sigma_t piecewise-constant, regime scale ~ Pareto(a).

    |N(0,1)| is light (all moments finite); the pooled heaviness comes ENTIRELY from the
    Pareto-distributed regime scale, so the tail index of g is set by sigma (~TARGET_ALPHA).
    """
    n_regimes = int(np.ceil(n / regime_len))
    # Pareto(a) with unit lower bound has tail index a; np.random.pareto returns (X-1).
    regime_scale = 1.0 + rng.pareto(TARGET_ALPHA, size=n_regimes)
    sigma = np.repeat(regime_scale, regime_len)[:n]
    return sigma * np.abs(rng.standard_normal(n))


# ------------------------------------------------------------------------- normalizers
def normalize_ema(g: np.ndarray) -> np.ndarray:
    """||g||/s_t with the causal winsorized-EMA tracker SN-OMD actually uses."""
    tr = OnlineScaleTracker(decay=0.99, winsor=8.0)
    s = np.empty(g.size)
    for i, v in enumerate(g):
        s[i] = tr.scale
        tr.step(float(v))
    return (g / np.maximum(s, 1e-12))[WARMUP:]


def normalize_median(g: np.ndarray, window: int = 1000) -> np.ndarray:
    """||g||/median_W with a causal (shift-by-1) trailing median, as in check2."""
    med = pl.Series(g).rolling_median(window_size=window, min_samples=1).shift(1).to_numpy()
    med[0] = g[0]
    return (g / np.maximum(med, 1e-12))[window:]


# ------------------------------------------------------------------------------- driver
def _mean_std(curves: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    arr = np.vstack(curves)
    return np.nanmean(arr, axis=0), np.nanstd(arr, axis=0)


def _fmt(mu: np.ndarray, sd: np.ndarray) -> str:
    return "  ".join(f"k={f:.3f}:{m:4.2f}+-{s:.2f}" for f, m, s in zip(FRACS, mu, sd))


def run() -> None:
    print("=" * 78)
    print("ESTIMATOR NULL: does causal scale-normalization lighten a tail with NO drift?")
    print(f"  N={N:,}  seeds={len(SEEDS)}  target raw alpha~{TARGET_ALPHA}")
    print("  (mean +- std over seeds; higher alpha = LIGHTER tail)")
    print("=" * 78)

    rows: list[dict] = []

    def record(stream: str, regime_len, normalizer: str, mu: np.ndarray, sd: np.ndarray) -> None:
        for f, m, s in zip(FRACS, mu, sd):
            rows.append(
                {"stream": stream, "regime_len": regime_len, "normalizer": normalizer,
                 "k_frac": f, "alpha_mean": round(float(m), 4), "alpha_std": round(float(s), 4)}
            )

    # ---- the null: iid genuinely-heavy, no drift ----
    raw, ema, med = [], [], []
    for sd in SEEDS:
        rng = np.random.default_rng(1000 + sd)
        g = gen_stationary_heavy(N, rng)
        raw.append(hill_curve(g[WARMUP:]))
        ema.append(hill_curve(normalize_ema(g)))
        med.append(hill_curve(normalize_median(g)))
    print("\nSTATIONARY-HEAVY  |Student-t(2.4)|, no drift  -- H1 predicts NO change:")
    print(f"  raw                {_fmt(*_mean_std(raw))}")
    print(f"  / EMA tracker      {_fmt(*_mean_std(ema))}")
    print(f"  / trailing median  {_fmt(*_mean_std(med))}")
    null_raw = _mean_std(raw)[0]
    null_ema = _mean_std(ema)[0]
    record("stationary_heavy", None, "raw", *_mean_std(raw))
    record("stationary_heavy", None, "ema", *_mean_std(ema))
    record("stationary_heavy", None, "median", *_mean_std(med))

    # ---- the positive control: tail is pure drift, swept by regime length ----
    print("\nDRIFT-MANUFACTURED  sigma_t*|N(0,1)|, regime scale~Pareto(2.4)"
          "  -- H1 predicts tracker LIGHTENS when it can follow sigma_t:")
    for L in (50, 250, 1000, 5000):
        raw, ema = [], []
        for sd in SEEDS:
            rng = np.random.default_rng(2000 + sd)
            g = gen_drift_manufactured(N, L, rng)
            raw.append(hill_curve(g[WARMUP:]))
            ema.append(hill_curve(normalize_ema(g)))
        tag = "(faster than tracker)" if L <= 100 else "(trackable)"
        print(f"  regime L={L:<5d} {tag}")
        print(f"    raw            {_fmt(*_mean_std(raw))}")
        print(f"    / EMA tracker  {_fmt(*_mean_std(ema))}")
        record("drift_manufactured", L, "raw", *_mean_std(raw))
        record("drift_manufactured", L, "ema", *_mean_std(ema))

    out = RES / "normalization_null.csv"
    pl.DataFrame(rows).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    # ---- verdict at the paper's headline threshold k=0.01 ----
    j = FRACS.index(0.01)
    print("\n" + "-" * 78)
    print(f"VERDICT at k=0.01 (the paper's headline threshold):")
    print(f"  NULL (no drift):  raw alpha={null_raw[j]:.2f}  ->  / EMA alpha={null_ema[j]:.2f}")
    delta = null_ema[j] - null_raw[j]
    if abs(delta) < 0.4:
        print(f"  => normalizer leaves a genuinely-heavy iid tail essentially unchanged "
              f"(delta={delta:+.2f}). The Jane lightening is NOT a mechanical artifact: H1.")
    else:
        print(f"  => normalizer moves the tail by delta={delta:+.2f} with ZERO drift. "
              f"H0 (artifact) cannot be ruled out; the headline needs a caveat.")


if __name__ == "__main__":
    run()
