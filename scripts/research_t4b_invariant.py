"""T4B secondary: the P = eta_max * B invariant, on ONE stream.

Registered under T4B's ``secondary_computation_the_invariant_across_tiers``.

T4 tested the invariant only *within* the bounded scale-free family, where normalized-GD's
ceiling is right-censored at the grid top, and reported INCONCLUSIVE. That under-used the data:
across tiers the dynamic range in ``B`` is ~1000x and both endpoints are measured.

But the obvious cross-tier calculation is confounded. ``gradnorm_at_wstar.npy`` is built by
``research_findings.py`` on date[0,30) with 200k rows, while the ceilings in
``normalize_continuous.csv`` are measured on date[0,120) with 150k rows -- a different window,
a different length, and a different standardization fit. Mixing them gives a suggestive number,
not a measurement.

This recomputes the gradient norms at ``w*`` on the SAME slice the ceilings come from, using the
same loader, so ``P`` is a single-stream quantity. It changes nothing about GAP 2: there is
still no lower bound and still no separation theorem.

Usage::

    .venv/Scripts/python.exe scripts/research_t4b_invariant.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_windows_replication import _load  # noqa: E402  (the ceiling stream's own loader)

from dfsl.evaluation import best_fixed_linear  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

CEILING_STREAM = (0, 120, 150000)   # exactly normalize_continuous.csv's slice
P_STAR_C10S = 11.5                  # committed, not fitted

# Step bounds, read off the committed learner definitions (see research_normalize.make_learner)
TIER = {
    "normgd":         ("tier 3", "constant", 1.0),
    "sn_ogd":         ("tier 3", "constant", 5.0),
    "scale_adaptive": ("tier 2", "unbounded (cap 1e9)", None),
    "ogd":            ("tier 1", "sup||g||", None),
}


def eta_max(df, m):
    sub = df.filter(pl.col("method") == m).sort("learning_rate")
    stable = sub.filter(~pl.col("diverged"))
    div = sub.filter(pl.col("diverged"))
    if not stable.height:
        return None
    return {
        "last_stable": float(stable.row(stable.height - 1, named=True)["learning_rate"]),
        "first_diverged": float(div.row(0, named=True)["learning_rate"]) if div.height else None,
    }


def main() -> int:
    lo, hi, rows = CEILING_STREAM
    print("=" * 96)
    print("T4B secondary -- the invariant P = eta_max * B, recomputed on ONE stream")
    print(f"  stream: date[{lo},{hi}), rows<={rows} -- the slice normalize_continuous.csv uses")
    print("=" * 96)

    X, y, wts, _ = _load(lo, hi, rows)
    w_star = best_fixed_linear(X, y, wts)
    resid = X @ w_star - y
    gn = 2.0 * np.abs(wts * resid) * np.linalg.norm(X, axis=1)
    gn = gn[np.isfinite(gn) & (gn > 0)]
    print(f"\n  ||g|| at w* on THIS slice: n={gn.size}  median {np.median(gn):.3f}  "
          f"p99 {np.quantile(gn, 0.99):.3f}  sup {gn.max():.3f}")

    ref = np.load(RES / "gradnorm_at_wstar.npy")
    ref = ref[np.isfinite(ref) & (ref > 0)]
    print(f"  for contrast, gradnorm_at_wstar.npy (date[0,30), 200k): sup {ref.max():.3f}")
    print(f"  the two differ by {max(gn.max(), ref.max())/min(gn.max(), ref.max()):.2f}x, which "
          "is why the mixed calculation was labelled suggestive")

    nc = pl.read_csv(RES / "normalize_continuous.csv")
    sup_g = float(gn.max())

    print(f"\n  {'method':16s} {'tier':8s} {'eta_max':>16s} {'B':>12s} {'P = eta_max*B':>20s}")
    rows_out = []
    for m, (tier, blab, bconst) in TIER.items():
        e = eta_max(nc, m)
        if e is None:
            continue
        B = bconst if bconst is not None else (sup_g if m == "ogd" else None)
        if e["first_diverged"] is None:
            elab, censored = f">= {e['last_stable']:g}", True
        else:
            elab, censored = f"[{e['last_stable']:g},{e['first_diverged']:g})", False
        if B is None:
            plab = "n/a (unbounded)"
            lo_p = hi_p = None
        elif censored:
            lo_p, hi_p = e["last_stable"] * B, None
            plab = f">= {lo_p:.1f}"
        else:
            lo_p, hi_p = e["last_stable"] * B, e["first_diverged"] * B
            plab = f"[{lo_p:.1f}, {hi_p:.1f})"
        print(f"  {m:16s} {tier:8s} {elab:>16s} {blab if bconst is None else '%.1f' % B:>12s} "
              f"{plab:>20s}" + ("   CENSORED" if censored else ""))
        rows_out.append({"method": m, "tier": tier, "eta_max_last_stable": e["last_stable"],
                         "eta_max_first_diverged": e["first_diverged"], "censored": censored,
                         "B": B, "P_lo": lo_p, "P_hi": hi_p, "stream": f"date[{lo},{hi}) {rows}"})

    print("\n### does a single P* fit both measured endpoints?")
    ivs = [(r["method"], r["P_lo"], r["P_hi"]) for r in rows_out
           if r["P_lo"] is not None and not r["censored"]]
    if len(ivs) >= 2:
        lo_p = max(i[1] for i in ivs)
        hi_p = min(i[2] for i in ivs)
        for m, a, b in ivs:
            print(f"    {m:16s} P in [{a:.1f}, {b:.1f})")
        if lo_p < hi_p:
            print(f"  The intervals INTERSECT: any P* in [{lo_p:.1f}, {hi_p:.1f}) fits both, "
                  f"across a {max(r['B'] for r in rows_out if r['B'])/min(r['B'] for r in rows_out if r['B']):.0f}x "
                  "range in B.")
            print(f"  C10S's committed P* = {P_STAR_C10S} "
                  f"{'lies inside' if lo_p <= P_STAR_C10S < hi_p else 'lies OUTSIDE'} that band.")
        else:
            print(f"  The intervals are DISJOINT ([{lo_p:.1f} vs {hi_p:.1f}) -- no single P* fits "
                  "both, so the invariant is falsified on this stream.")
        print("  Caveat kept: eta_max is quantised by the sweep grid, so these are grid-resolution")
        print("  intervals, and normalized-GD stays censored and contributes nothing either way.")
    else:
        print("  Fewer than two uncensored endpoints; nothing to intersect.")

    out = RES / "t4b_invariant.csv"
    pl.DataFrame(rows_out, infer_schema_length=None).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")
    print("\nUnchanged by this: GAP 2. No lower bound, no separation theorem.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
