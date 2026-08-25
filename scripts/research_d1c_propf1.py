"""D1C: is Prop F.1's discharge of Assumption D.1 empty at the measured regime count?

Prop F.1 discharges the lower bracket for the two-timescale envelope, and pays for it with one
added term ``O(D N W sup_t sigma_t)``, "dominated whenever ``NW << T^(1/p)`` (macroscopic
regimes)". D1B measured ``N`` to be at least linear in ``T`` for that same envelope. This
evaluates the domination condition rather than assuming it.

Two readings, reported separately because they can disagree:

  (a) asymptotic -- how ``NW/T^(1/p)`` scales. Evaluated at ``beta = 1`` EXACTLY, not at D1B's
      fitted 1.16-1.21: ``N <= T`` by construction so a fitted exponent above 1 is a
      finite-horizon artifact, and the argument must not lean on it.

  (b) at the measured horizon -- the numeric ratio at ``T = 200,000`` with the measured ``N``.
      A term can scale badly and still be small at the horizon in hand; if it is, the
      proposition is fine as applied and only its asymptotic reading needs qualifying.

``W`` is not free. The blocking argument needs the window split into ``~W/l`` near-independent
blocks of length ``l >= the mixing time``, so ``W`` is reported at the tracker's own window
(``W=64``, which ignores that requirement and is therefore the most favourable value available)
and at the blocking-required window, with the mixing time estimated from the process itself.

Also closes two seams. S1: a tracker-free segmentation, so the claim is about the process and
not only about our adaptive filters. S3: the coarsening defence, costed through the
exceptional-set accounting rather than asserted as a binary.

Usage::

    .venv/Scripts/python.exe scripts/research_d1c_propf1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_d1b_regime_count import (  # noqa: E402
    C_GRID,
    MIN_SEGMENTS,
    regime_count,
    two_timescale,
)

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

P_GRID = [1.3, 1.5, 2.0]
W_TRACKER = 64            # the envelope's own fast window, research_tracker.two_timescale
BLOCKS_NEEDED = 10        # "~W/l near-independent blocks"; 10 is generous to the proposition


def rank_acf(x, lags):
    """Rank (Spearman) autocorrelation, matching how the paper reports serial dependence."""
    r = np.argsort(np.argsort(x)).astype(float)
    r -= r.mean()
    denom = float(r @ r)
    return {L: float(r[:-L] @ r[L:]) / denom for L in lags}


def mixing_time(x, thresh=0.05):
    """Smallest lag at which rank autocorrelation falls below `thresh` and stays there."""
    lags = [1, 5, 10, 25, 50, 100, 150, 200, 250, 300, 400, 500, 750, 1000, 1500, 2000]
    acf = rank_acf(x, [L for L in lags if L < len(x) // 4])
    for L in sorted(acf):
        if acf[L] < thresh:
            return L, acf
    return None, acf


def blockwise_regime_count(g, b, c_units):
    """S1: tracker-free segmentation. Non-causal block medians, no adaptive filter in the loop.

    Still an estimator -- a block median is a smoother -- but it has no feedback, no decay rate
    and no asymmetry between rising and falling, which is what "tracker-derived" was a worry
    about.
    """
    n = len(g) // b
    if n < 3:
        return None
    med = np.array([np.median(g[k * b:(k + 1) * b]) for k in range(n)])
    return regime_count(med, c_units * float(np.median(med)))


def run() -> int:
    g = np.load(RES / "gradnorm_at_wstar.npy")
    g = g[np.isfinite(g) & (g > 0)]
    T = len(g)
    s_env = two_timescale(g)

    print("=" * 98)
    print("D1C -- is Prop F.1's added term O(D N W sup sigma) dominated at the measured N?")
    print(f"  domination condition: N*W << T^(1/p);  T = {T}")
    print("=" * 98)

    # ------------------------------------------------------------------ the mixing time
    ell, acf = mixing_time(g)
    print("\n### the window W the blocking argument requires")
    print("  rank autocorrelation of the scale process:")
    for L in sorted(acf):
        if L in (1, 50, 100, 250, 500, 1000, 2000):
            print(f"    lag {L:5d}: {acf[L]:+.4f}")
    if ell is None:
        ell = max(acf)
        print(f"  never falls below 0.05 within the lags tested -> l >= {ell}")
    else:
        print(f"  falls below 0.05 at lag {ell} -> mixing time l ~ {ell}")
    W_block = BLOCKS_NEEDED * ell
    print(f"  blocking needs ~{BLOCKS_NEEDED} blocks of length >= l, so W >= {W_block}")
    print(f"  reporting both W = {W_TRACKER} (the tracker's own window, which IGNORES this and")
    print(f"  is therefore the most favourable value available) and W = {W_block}")

    # ---------------------------------------------------------------- (a) the asymptotics
    print("\n### (a) asymptotic:  N*W / T^(1/p) ~ W * T^(beta - 1/p),  evaluated at beta = 1")
    print(f"  {'p':>5s} {'1/p':>7s} {'beta - 1/p':>12s}   verdict")
    for p in P_GRID:
        e = 1.0 - 1.0 / p
        verdict = ("DIVERGES -- term is never dominated" if e > 0 else
                   "bounded" if e == 0 else "vanishes -- term is dominated")
        print(f"  {p:5.1f} {1/p:7.3f} {e:12.3f}   {verdict}")
    print("  (at the fitted beta = 1.16-1.21 the exponent is only larger; beta = 1 is the")
    print("   conservative reading and the conclusion does not depend on the fit)")

    # -------------------------------------------------- (b) the ratio at the real horizon
    print(f"\n### (b) at the measured horizon T = {T}, envelope tracker")
    rows = []
    print(f"  {'c':>5s} {'N':>7s} {'measurable':>11s} " +
          " ".join(f"{'NW/T^1/'+str(p):>14s}" for p in P_GRID) + "   W")
    for W, wlab in ((W_TRACKER, "tracker"), (W_block, "blocking")):
        for c_units in C_GRID:
            N = regime_count(s_env, c_units * float(np.median(s_env)))
            ok = N >= MIN_SEGMENTS
            cells = []
            for p in P_GRID:
                ratio = N * W / (T ** (1.0 / p))
                cells.append(f"{ratio:14.1f}")
                rows.append({"tracker": "two-timescale envelope", "c_units": c_units,
                             "N": N, "W": W, "W_source": wlab, "p": p,
                             "T": T, "ratio_NW_over_Tinvp": round(ratio, 4),
                             "dominated": bool(ratio < 1.0), "measurable": bool(ok)})
            print(f"  {c_units:5g} {N:7d} {str(ok):>11s} " + " ".join(cells) + f"   {wlab}")

    # ------------------------------------------------------------------- S1, tracker-free
    print("\n### S1 -- tracker-free segmentation (non-causal block medians, no filter in loop)")
    print(f"  {'block b':>9s} {'#blocks':>8s} " +
          " ".join(f"{'N(c='+str(c)+')':>12s}" for c in (0.5, 1.0, 2.0)))
    s1 = []
    for b in (50, 100, 250, 500, 1000):
        counts = [blockwise_regime_count(g, b, c) for c in (0.5, 1.0, 2.0)]
        print(f"  {b:9d} {len(g)//b:8d} " +
              " ".join(f"{('-' if n is None else n):>12}" for n in counts))
        for c, n in zip((0.5, 1.0, 2.0), counts):
            if n is not None:
                s1.append({"block": b, "n_blocks": len(g) // b, "c_units": c, "N": n})
    if s1:
        print("  N per unit time (N / n_blocks) is the scale-free reading:")
        for c in (0.5, 1.0, 2.0):
            fr = [(r["block"], r["N"] / r["n_blocks"]) for r in s1 if r["c_units"] == c]
            print(f"    c={c}: " + "  ".join(f"b={b}:{v:.3f}" for b, v in fr))
        print("  a roughly constant fraction across b means boundaries arrive at a constant")
        print("  RATE, i.e. N grows in proportion to T with no tracker in the loop.")

    # ------------------------------------------------------- S3 -- cost the coarsening defence
    print("\n### S3 -- the coarsening defence, costed rather than asserted")
    print("  tab:beta: the B=10^4 block tracker holds the lower bracket at 0.93, not 0.")
    for bracket in (0.93, 0.97, 0.99):
        viol = 1.0 - bracket
        print(f"    bracket {bracket:.2f} -> {viol*100:.0f}% of rounds violate; charged trivially")
        print(f"      at O(D sup sigma) per round that is {viol:.2f}*T = "
              f"{viol*T:,.0f} rounds at T={T:,} -- Theta(T), the same wall.")
    print("  So coarsening does not escape: it trades the O(NW) lapse set for an O(T) violation")
    print("  set. The binary claim 'a coarse tracker fails the bracket' was overstated; the")
    print("  accounting reaches the same conclusion and is checkable.")

    out = RES / "d1c_propf1.csv"
    pl.DataFrame(rows).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    # --------------------------------------------------------------------------- verdict
    meas = [r for r in rows if r["measurable"]]
    dom_any = [r for r in meas if r["dominated"]]
    print("-" * 98)
    if not dom_any:
        print("H_D1C SURVIVES. The added term is dominated at NO (c, W, p) combination tested,")
        print("  asymptotically or at the measured horizon. Prop F.1's discharge is empirically")
        print("  vacuous on this data: it buys the bracket at a cost this process does not pay.")
    else:
        print(f"H_D1C FALSIFIED IN PART -- dominated in {len(dom_any)} of {len(meas)} measurable")
        print("  combinations. The favourable outcome; report which and do not generalise:")
        for r in dom_any:
            print(f"    c={r['c_units']} W={r['W']} ({r['W_source']}) p={r['p']}: "
                  f"ratio {r['ratio_NW_over_Tinvp']:.3f}")
    print("\nWhat this does NOT establish: anything about Prop F.1's correctness, about")
    print("  Prop 3.1 (unconditional, no drift model), or about the divergence partition.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
