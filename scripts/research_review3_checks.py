"""Third-round decisive checks.

CHECK A (theory fork). Is W_s ~ T^beta with beta~1 a fact about the drift, or an
artifact of a tracker that moves every round? Measure beta for a BLOCK tracker: s_t held
piecewise-constant over blocks of length B (predictable: block i uses the robust median
of block i-1), swept over B. W_s then sums over T/B block boundaries. If beta drops as B
grows we can rescue Theorem 3.3 at the tracker that achieves it (and confirm Remark 3.5);
if beta stays ~1 for every accurate-enough tracker, the total-variation parameterization
is wrong and the bound should be demoted / re-derived via the switching (N-regime) form.
We also report the lower-bracket quality vs B (the accuracy side of the frontier).

CHECK B (true stationary negative control). The 100k Jane slice is not stationary
(~30% within-day scale drift). Impose genuine stationarity in the synthetic harness
(sigma_t == const, p=2, static reachable comparator) and check whether SN-OMD's advantage
over tuned OGD vanishes. If it does, the thesis' control holds; if not, the advantage is
general step-size conditioning and the paper should say so.

Usage: python scripts/research_review3_checks.py
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


def block_tracker(g, B, c=1.0):
    """Predictable piecewise-constant scale: block i uses c*median of block i-1."""
    n = g.size
    s = np.empty(n)
    cur = float(np.median(g[:B])) * c
    for start in range(0, n, B):
        s[start:min(start + B, n)] = cur
        cur = c * float(np.median(g[start:start + B]))
    return s


def variation_curve(x, grid):
    inc = np.diff(x, prepend=x[0])
    cum = x[0] + np.cumsum(np.maximum(inc, 0.0))
    return cum[grid]


def fit_beta(T, y):
    m = (y > 0) & np.isfinite(y)
    return float(np.polyfit(np.log(T[m]), np.log(y[m]), 1)[0])


def check_a_block_beta():
    print("=" * 72)
    print("CHECK A -- block-tracker W_s growth exponent beta(B)")
    print("=" * 72)
    g = np.load(RES / "gradnorm_at_wstar.npy")
    g = g[np.isfinite(g) & (g > 0)]
    n = g.size
    # ground-truth scale for bracket quality (non-causal centered median)
    sig = pl.Series(g).rolling_median(window_size=1001, center=True, min_samples=1).to_numpy()
    grid = np.unique(np.geomspace(3000, n - 1, 40).astype(int))
    print(f"  N={n};  block B -> beta (W_s ~ T^beta), W_s(full), lower-bracket frac (s>=0.5 sigma)")
    for B in [1, 10, 30, 100, 300, 1000, 3000, 10000, 30000]:
        s = block_tracker(g, B, c=1.0)
        Ws = variation_curve(s, grid)
        beta = fit_beta(grid.astype(float), Ws)
        lb = float(np.mean(s >= 0.5 * sig))
        print(f"    B={B:6d}   beta={beta:.3f}   W_s(full)={Ws[-1]:8.0f}   lower-bracket={lb:.3f}")
    print("  (beta->0 as B grows => drift has bounded variation, jitter was the artifact;")
    print("   beta stays ~1 => total-variation is the wrong parameterization.)")


def check_b_stationary_control():
    print("\n" + "=" * 72)
    print("CHECK B -- stationary negative control (sigma const, p=2, static u*)")
    print("=" * 72)
    rng = np.random.default_rng(0)
    S, d, T = 400, 5, 20000
    u = rng.standard_normal(d); u /= np.linalg.norm(u)

    def run(kind, eta, cap=5.0, decay=0.99, winsor=8.0):
        W = np.zeros((S, d)); s = np.ones(S); acc = np.zeros(S); cnt = 0
        for t in range(T):
            x = rng.standard_normal((S, d))
            eps = rng.standard_normal(S)          # p=2, sigma=1, STATIONARY
            y = x @ u + eps
            pred = np.einsum("sd,sd->s", W, x); resid = pred - y
            g = 2.0 * resid[:, None] * x
            gn = np.linalg.norm(g, axis=1) + 1e-12
            lr = eta / np.sqrt(t + 1.0)
            if kind == "ogd":
                step = g
            else:
                v = g / s[:, None]; vn = np.linalg.norm(v, axis=1) + 1e-12
                step = v * np.minimum(1.0, cap / vn)[:, None]
                s = decay * s + (1 - decay) * np.minimum(gn, winsor * s)
            W = W - lr * step
            if t >= T // 2:
                acc += resid * resid - eps * eps; cnt += 1
        return float(np.mean(acc / cnt)), float(np.std(acc / cnt) / np.sqrt(S))

    def best(kind, grid):
        vals = [(run(kind, eta)[0], eta) for eta in grid]
        return min(vals)  # (excess_loss, eta)

    ogd = best("ogd", [0.002, 0.005, 0.01, 0.02, 0.05])
    sn = best("snomd", [0.05, 0.1, 0.2, 0.5, 1.0])
    print(f"  tuned OGD    : steady excess loss = {ogd[0]:.5f}  @eta={ogd[1]}")
    print(f"  tuned SN-OMD : steady excess loss = {sn[0]:.5f}  @eta={sn[1]}")
    print(f"  ratio SN/OGD = {sn[0]/ogd[0]:.2f}  "
          f"({'advantage VANISHES (control holds)' if sn[0] >= 0.8*ogd[0] else 'SN-OMD still better -> step-size conditioning, not drift'})")


if __name__ == "__main__":
    check_a_block_beta()
    check_b_stationary_control()
