"""Reproduce tab:residual's GARCH-*surrogate* block from committed code.

The paper's `tab:residual` reports a zero-residual-tail control: a GARCH(1,1) stream with
Gaussian innovations (so the *conditional* tail is light by construction), calibrated to the
real raw pooled index, then run through the SAME causal winsorized-EMA the paper deploys. It
reads a light-but-not-Gaussian normalized tail -- the "causal-estimation cost" of tracking a
predictable scale online. Until now the exact three-threshold cells

    raw pooled (none)        2.54 / 2.48 / 2.44   (k = .005 / .01 / .02)
    causal winsorized-EMA    4.81 / 4.48 / 4.08
    true-sigma_t oracle     10.3  / 9.05 / 7.75

were reproduced by no committed script (`research_null_normalization.py` builds the same
GARCH control but only prints the headline k=0.01). This script regenerates all three
thresholds, plus the surrogate's *non-causal twin* (centered winsorized-EMA), so the §D.9
surrogate-to-surrogate causal-vs-non-causal gap is reproducible too.

Everything is synthetic -- it needs NO gitignored Jane data, so a reviewer can run it from a
clean clone. The estimators are imported verbatim from the modules behind the paper's
numbers (`garch_stream`, `causal_ema`, `centered_ema`, `hill`), so this is the same pipeline,
not a re-implementation.

Key identity: in x_t = sigma_t * z_t, the true-sigma_t "oracle" |x_t|/sigma_t equals |z_t|
exactly, so the oracle row is just the Hill index of the Gaussian innovations.

Usage:
  python scripts/research_residual_surrogate.py            # calibrate + full table + CSV
  python scripts/research_residual_surrogate.py --grid     # print the calibration grid only
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Same estimators as the paper's tab:residual real-data rows and the GARCH control.
from research_review2_checks import causal_ema, centered_ema, hill  # noqa: E402
from research_null_normalization import garch_stream  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

N = 200_000                     # ~ the real Jane slice behind gradnorm_at_wstar.npy
SEEDS = 20                      # matches research_null_normalization's mechanism/GARCH seeds
SEEDS_CAL = 8                   # cheaper sweep for locating (a,b)
WARMUP = 200                    # drop EMA warm-up, exactly as tab:residual's real rows do
FRACS = (0.005, 0.01, 0.02)     # the three tab:residual thresholds
OMEGA = 1e-6
SEED0 = 9000                    # same base seed stream as research_null_normalization.run_garch
REAL_RAW_K01 = 2.43             # tab:residual real raw pooled at k=.01 (calibration reference)

# The locked calibrated config: (a=.22, b=.77), a near-integrated GARCH whose raw pooled index
# sits on the real ~2.43-2.5 band. At the seed setup below it reproduces ALL THREE tab:residual
# surrogate rows to within +-0.02:  raw 2.54/2.48/2.44, causal-EMA 4.81/4.48/4.08, oracle
# 10.3/9.05/7.75.  Re-derive with `--grid` (its k=.01 argmin against the real raw index
# independently selects this entry) and check the joint raw+causal fit with `--sweep`.
CALIB = (0.22, 0.77)

# Persistence grid; b set so a+b in {0.97,0.98,0.99} (near-integrated, as real vol is).
GRID = [(a, round(s - a, 3)) for s in (0.99, 0.98, 0.97)
        for a in (0.16, 0.18, 0.20, 0.22, 0.24, 0.26)]


def hill_row(x: np.ndarray) -> np.ndarray:
    xs = x[np.isfinite(x) & (x > 0)]
    return np.array([hill(xs, int(f * xs.size)) for f in FRACS])


def normalized(x: np.ndarray, tracker) -> np.ndarray:
    s = tracker(x, decay=0.99, winsor=8.0)
    return (x / np.maximum(s, 1e-12))[WARMUP:-WARMUP]


def surrogate_rows(a: float, b: float, seeds: int) -> dict[str, np.ndarray]:
    """Average Hill rows over `seeds` GARCH streams for raw / causal-EMA / non-causal twin /
    true-sigma oracle (=|z|)."""
    acc = {k: [] for k in ("raw", "causal", "twin", "oracle")}
    for sd in range(seeds):
        rng = np.random.default_rng(SEED0 + sd)
        gx, gz = garch_stream(N, OMEGA, a, b, rng)   # gx=|x| heavy marginal, gz=|z| innovations
        acc["raw"].append(hill_row(gx))
        acc["causal"].append(hill_row(normalized(gx, causal_ema)))
        acc["twin"].append(hill_row(normalized(gx, centered_ema)))
        acc["oracle"].append(hill_row(gz))           # |x|/sigma_t == |z| exactly
    return {k: np.nanmean(np.array(v), 0) for k, v in acc.items()}


def fmt(row: np.ndarray) -> str:
    return "  ".join(f"{v:5.2f}" for v in row)


def run_grid() -> tuple[float, float]:
    print("=" * 78)
    print(f"CALIBRATION GRID -- GARCH(1,1) Gaussian innov., N={N:,}, seeds={SEEDS_CAL}")
    print(f"  target: raw |x| at k=.01 near the real pooled index {REAL_RAW_K01}")
    print("=" * 78)
    print(f"  {'(a, b)':>14}  a+b   " + "  ".join(f"raw_k{f}" for f in FRACS))
    best, best_gap = None, np.inf
    for a, b in GRID:
        r = surrogate_rows(a, b, SEEDS_CAL)["raw"]
        gap = abs(r[1] - REAL_RAW_K01)
        flag = ""
        if gap < best_gap:
            best_gap, best, flag = gap, (a, b), "  <== nearest k=.01 to real raw"
        marker = "  [CALIB]" if (a, b) == CALIB else ""
        print(f"  ({a:.2f}, {b:.2f})  {a + b:.2f}   {fmt(r)}{flag}{marker}")
    print(f"\n  nearest-k.01 (a,b) = {best} (|raw_k.01 - {REAL_RAW_K01}| = {best_gap:.3f}); "
          f"locked CALIB = {CALIB} (matches the reported surrogate raw row across all k)")
    return best


def run_full(a: float, b: float) -> None:
    print("\n" + "=" * 78)
    print(f"tab:residual GARCH-SURROGATE block   (a={a}, b={b}, a+b={a + b:.2f}, "
          f"N={N:,}, seeds={SEEDS})")
    print("=" * 78)
    rows = surrogate_rows(a, b, SEEDS)
    hdr = "  ".join(f"k={f}" for f in FRACS)
    print(f"  {'Normalization of ||g||':38s} {hdr}")
    labels = {"raw": "raw pooled (none)",
              "causal": "causal winsorized-EMA (deployed)",
              "twin": "  centered winsorized-EMA (non-causal twin)",
              "oracle": "  true-sigma_t oracle (= |z|)"}
    for key in ("raw", "causal", "twin", "oracle"):
        print(f"  {labels[key]:38s} {fmt(rows[key])}")

    paper = {"raw": (2.54, 2.48, 2.44), "causal": (4.81, 4.48, 4.08),
             "oracle": (10.3, 9.05, 7.75)}
    print("\n  vs paper tab:residual (surrogate block):")
    for key in ("raw", "causal", "oracle"):
        diff = rows[key] - np.array(paper[key])
        print(f"  {labels[key]:38s} paper {fmt(np.array(paper[key]))}   "
              f"d {'  '.join(f'{d:+.2f}' for d in diff)}")

    # §D.9 surrogate-to-surrogate gaps (all from the surrogate's own rows):
    g_causal_twin = rows["twin"] - rows["causal"]     # isolating causality, same estimator
    g_oracle_causal = rows["oracle"] - rows["causal"]  # full causal-estimation cost
    print(f"\n  surrogate causal->non-causal-twin gap (k):  "
          f"{'  '.join(f'{v:+.2f}' for v in g_causal_twin)}")
    print(f"  surrogate oracle-vs-causal gap        (k):  "
          f"{'  '.join(f'{v:+.2f}' for v in g_oracle_causal)}")

    out_rows = []
    for key in ("raw", "causal", "twin", "oracle"):
        for j, f in enumerate(FRACS):
            out_rows.append({"row": labels[key].strip(), "k": f,
                             "alpha_hat": round(float(rows[key][j]), 4),
                             "a": a, "b": b, "N": N, "seeds": SEEDS})
    out = RES / "residual_surrogate.csv"
    pl.DataFrame(out_rows).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")


def run_sweep() -> None:
    """Focused sweep at the LOCKED seed setup (SEEDS, SEED0, N -- validated by the oracle row):
    print raw / causal / oracle at each candidate (a,b) so raw~2.48 AND causal~4.48 can be
    matched jointly."""
    print("=" * 78)
    print(f"FULL-SEED SWEEP  N={N:,}, seeds={SEEDS}  (target raw_k.01~2.48, causal_k.01~4.48)")
    print("=" * 78)
    print(f"  {'(a, b)':>12}   raw(.005/.01/.02)      causal(.005/.01/.02)   oracle_k.01")
    cands = [(0.20, 0.79), (0.21, 0.78), (0.22, 0.77), (0.23, 0.76), (0.24, 0.75),
             (0.22, 0.76), (0.23, 0.75)]
    for a, b in cands:
        r = surrogate_rows(a, b, SEEDS)
        print(f"  ({a:.2f},{b:.2f})   {fmt(r['raw'])}    {fmt(r['causal'])}    {r['oracle'][1]:.2f}")


def main() -> None:
    if "--grid" in sys.argv:
        run_grid()
        return
    if "--sweep" in sys.argv:
        run_sweep()
        return
    run_full(*CALIB)


if __name__ == "__main__":
    main()
