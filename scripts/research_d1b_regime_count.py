"""D1B step 0: does the regime count N grow sublinearly in T on the real scale process?

Remark D.3 leaves open a switching bound in the regime count. D1 derived its target rate,
``R_T = Otilde(N^(1-1/p) * T^(1/p))``, and verified both limits. That rate is an improvement
on the current ``T^(1/p+1/2)`` only when N is SUBLINEAR in T: if regimes arrive at a constant
rate then ``N ~ T`` and ``N^(1-1/p) T^(1/p) = Theta(T)``, which is the vacuous bound the whole
direction exists to escape.

The paper measures the tracker's upward variation ``W_s`` to be ``Theta(T)`` (Table 6). This
script asks the corresponding question for N, using the paper's OWN definition of a regime --
a horizon over which the tracker's upward variation is ``O(1)``.

Construction. Walk the tracker path and accumulate upward variation ``sum (s_t - s_{t-1})_+``.
When adding step t would push a segment past the budget c, close the segment BEFORE t and open
a new one at t. Each segment then has upward variation <= c, except a single step larger than c
which forms its own segment -- which is exactly the drift model Appendix E.8 assumes,
"piecewise-slow variation plus arbitrary jumps at N change points". N is the segment count.

The answer is a function of c and of the tracker, so both are swept and the sensitivity IS the
result rather than a robustness afterthought. c is expressed in units of the median scale so it
is comparable across trackers.

Usage::

    .venv/Scripts/python.exe scripts/research_d1b_regime_count.py
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

# Horizons at which N is evaluated, log-spaced so the exponent fit is not dominated by the tail.
FRACTIONS = [0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0]
# Segment budgets, in units of the median scale.
C_GRID = [0.5, 1.0, 2.0, 5.0, 10.0]


# --------------------------------------------------------------------- trackers
def winsorized_ema(g, decay=0.99, winsor=8.0):
    """The deployed default, matching research_batched_check._step."""
    s = np.empty(len(g))
    cur = None
    for i, gn in enumerate(g):
        cur = gn if cur is None else decay * cur + (1 - decay) * min(gn, winsor * cur)
        s[i] = cur
    return s


def two_timescale(g, Wf=64, rho=0.0008, C=1.0):
    """The envelope of research_tracker.two_timescale -- the one with a proven W_s bound."""
    n = len(g)
    fast = np.empty(n)
    for t in range(n):
        lo = max(0, t - Wf)
        fast[t] = C * (np.median(g[lo:t]) if t > lo else g[t])
    s = np.empty(n)
    s[0] = fast[0]
    for t in range(1, n):
        s[t] = max(fast[t], (1.0 - rho) * s[t - 1])
    return s


def block_median(g, B=10000):
    """Predictable per-block median: block k uses block k-1's median."""
    n = len(g)
    s = np.empty(n)
    prev = float(np.median(g[:min(B, n)]))
    for k in range(0, n, B):
        s[k:k + B] = prev
        prev = float(np.median(g[k:k + B]))
    return s


TRACKERS = {
    "winsorized EMA (deployed)": winsorized_ema,
    "two-timescale envelope (proven)": two_timescale,
    "block median (most accurate)": block_median,
}


# ------------------------------------------------------------------ the measurement
def regime_count(s, c):
    """Segments needed so each carries upward variation <= c (jumps may exceed alone)."""
    n = len(s)
    if n == 0:
        return 0
    segments = 1
    acc = 0.0
    for t in range(1, n):
        up = s[t] - s[t - 1]
        if up <= 0:
            continue
        if acc + up > c:
            segments += 1        # close before t, reopen at t
            acc = 0.0
        else:
            acc += up
    return segments


def upward_variation(s):
    d = np.diff(s)
    return float(d[d > 0].sum())


# A growth exponent cannot be fitted from a handful of segments. Table 6 already imposes
# exactly this rule on the corresponding W_s ~ T^beta fit -- it restricts to horizons with
# >~50 blocks and calls the decline at large B "a finite-horizon artifact -- B=10^4 has only
# ~20 blocks". The same rule is applied here, and note which way it cuts: it DISQUALIFIES the
# only tracker whose exponent looks sublinear, so it makes proceeding to a derivation harder,
# not easier.
MIN_SEGMENTS = 50


def fit_exponent(Ts, Ns):
    """Slope of log N against log T; 1.0 means N grows in proportion to T."""
    m = (np.array(Ns) > 0)
    if m.sum() < 3:
        return float("nan")
    return float(np.polyfit(np.log(np.array(Ts)[m]), np.log(np.array(Ns)[m]), 1)[0])


def measurable(Ns):
    """Is there enough resolution for the exponent to mean anything?"""
    return max(Ns) >= MIN_SEGMENTS


def run() -> int:
    g = np.load(RES / "gradnorm_at_wstar.npy")
    g = g[np.isfinite(g) & (g > 0)]
    n = len(g)
    print("=" * 96)
    print(f"D1B STEP 0 -- does the regime count N grow sublinearly in T?")
    print(f"  scale process: {n} gradient norms at w*, median {np.median(g):.4g}")
    print("  regime = a horizon over which the tracker's upward variation is <= c")
    print("  the switching bound helps only if the exponent of N(T) is materially below 1")
    print("=" * 96)

    rows = []
    for tname, tfn in TRACKERS.items():
        s_full = tfn(g)
        med = float(np.median(s_full))
        print(f"\n########## {tname} ##########")
        print(f"  W_s over the full record = {upward_variation(s_full):.4g} "
              f"({upward_variation(s_full)/med:.4g} in units of the median scale {med:.4g})")
        print(f"  {'c (x median)':>12s} " + " ".join(f"{int(f*n):>8d}" for f in FRACTIONS)
              + "   exponent")
        for c_units in C_GRID:
            c = c_units * med
            Ts, Ns = [], []
            for f in FRACTIONS:
                T = int(f * n)
                N = regime_count(s_full[:T], c)
                Ts.append(T)
                Ns.append(N)
            beta = fit_exponent(Ts, Ns)
            ok = measurable(Ns)
            if not ok:
                flag = f"  <-- only {max(Ns)} segments; exponent NOT MEASURABLE"
            elif beta >= 0.95:
                flag = "  <-- LINEAR"
            elif beta < 0.9:
                flag = "  <-- sublinear"
            else:
                flag = ""
            print(f"  {c_units:12g} " + " ".join(f"{N:8d}" for N in Ns)
                  + f"   {beta:.3f}{flag}")
            for T, N in zip(Ts, Ns):
                rows.append({"tracker": tname, "c_units_of_median": c_units,
                             "T": T, "N": N, "exponent": round(beta, 4),
                             "measurable": ok, "max_segments": int(max(Ns))})

    out = RES / "d1b_regime_count.csv"
    pl.DataFrame(rows).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    # ------------------------------------------------------------------ the verdict
    combos = {(r["tracker"], r["c_units_of_median"], r["exponent"], r["measurable"])
              for r in rows}
    good = sorted([c for c in combos if c[3]], key=lambda x: x[2])
    dropped = sorted([c for c in combos if not c[3]], key=lambda x: x[2])
    print("-" * 96)
    print(f"{len(dropped)} of {len(combos)} combinations have fewer than {MIN_SEGMENTS} "
          f"segments and are not measurable:")
    for t, c, b, _ in dropped:
        print(f"    {t:34s} c={c:<5g} exponent {b:.3f} -- discarded")
    if not good:
        print("\nVERDICT: NOTHING IS MEASURABLE at this horizon. No claim follows.")
        return 0
    lo, hi = good[0][2], good[-1][2]
    print(f"\nexponent of N(T) over the {len(good)} measurable combinations: "
          f"{lo:.3f} to {hi:.3f}")
    if lo >= 0.95:
        print("\nVERDICT: LINEAR everywhere tested.")
        print("  N grows in proportion to T, so N^(1-1/p) T^(1/p) = Theta(T) at every p and the")
        print("  switching bound of Remark D.3 is vacuous at the measured drift rate. This is")
        print("  not a gap in the proof -- no proof of that form can help on this process.")
    elif hi < 0.9:
        print("\nVERDICT: SUBLINEAR everywhere tested -- proceed to the derivation.")
    else:
        print("\nVERDICT: MIXED. The exponent depends on c or on the tracker, so it is not a")
        print("  property of the data alone and no clean claim follows. Report the sweep.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
