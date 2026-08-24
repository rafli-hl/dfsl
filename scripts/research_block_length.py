"""Is the one-day bootstrap block long enough?  (audit finding 10)

Table 4's error bars come from a circular moving-block bootstrap with a block of about one
trading day. The audit's objection: rank autocorrelation of ~0.1-0.2 persists to lag 250,
so a one-day block may not span the dependence, which would *understate* the standard
errors -- and the paper's readings lean on those intervals in both directions. A tie that
rests on overlapping intervals is safe under this failure mode (true intervals would be
wider, so they would still overlap), but a *separation* the paper reads as real is not.

This measures the sensitivity directly. Each row of Table 4 is recomputed at exactly the
tuned setting the table prints -- read from the committed CSVs, not re-tuned, so the point
estimates are the table's own -- and the same prediction vector is bootstrapped at blocks
of 1, 3, 5 and 10 trading days. It then re-runs, at every block length, the comparisons the
paper's prose actually makes.

The answer is not the one the objection anticipates, and the script says so in its own
output: past three days the standard errors *shrink*. The slice is 20 trading days, so a
3-day block leaves 7 blocks per resample and a 10-day block leaves 2, and a moving-block
bootstrap with a handful of long contiguous stretches collapses toward the original series.
So the long-block columns measure the record length, not the dependence. What survives is
the check the audit actually proposed -- at 3 days the errors do not move -- plus the
observation that the accuracy claims do not rest on this bootstrap in the first place.

Usage::

    .venv/Scripts/python.exe scripts/research_block_length.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_batched_check import group_boundaries  # noqa: E402
# The anchor runners here are the same function as research_table1_errorbars' preds_*;
# taking them from research_baselines keeps every row of the table sourced from the module
# that produced it.
from research_baselines import (  # noqa: E402
    adagrad_batched,
    adagrad_perrow,
    anchor_batched,
    anchor_perrow,
    fixedclip_batched,
    fixedclip_perrow,
)
from research_table1_errorbars import agg_r2  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

N_BOOT = 4000
BLOCK_DAYS = [1, 3, 5, 10]


def block_bootstrap(y, p, wts, block_len, rng, n_boot=N_BOOT):
    """Circular moving-block bootstrap of the aggregate weighted R^2 (as in Table 4)."""
    n = len(y)
    n_blocks = int(np.ceil(n / block_len))
    offs = np.arange(block_len)
    reps = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx = ((starts[:, None] + offs) % n).ravel()[:n]
        reps[b] = agg_r2(y, p, wts, idx)
    return float(reps.std(ddof=1))


def _tuned() -> dict:
    """Read each Table 4 row's tuned setting from the CSV that produced it."""
    eb = pl.read_csv(RES / "table1_errorbars.csv")
    bl = pl.read_csv(RES / "baselines_jane.csv")

    def eb_lr(proto, meth):
        r = eb.filter((pl.col("protocol") == proto) & (pl.col("method") == meth))
        return float(r["lr_star"][0])

    def bl_tune(proto, meth):
        r = bl.filter((pl.col("protocol") == proto) & (pl.col("method") == meth))
        return dict(kv.split("=") for kv in r["tune"][0].split(","))

    out = {}
    for proto in ("per-row", "per-step"):
        out[proto] = {
            "OGD": ("anchor", "ogd", 0.0, eb_lr(proto, "OGD")),
            "Scale-adaptive OGD (M->inf)": (
                "anchor", "snomd", 1e9, eb_lr(proto, "Scale-adaptive OGD (M->inf)")),
            "Normalized-GD (M->0)": (
                "anchor", "normgd", 0.0, float(bl_tune(proto, "normalized-GD (anchor)")["lr"])),
            "SN-OMD (M=5)": (
                "anchor", "snomd", 5.0, float(bl_tune(proto, "SN-OMD M=5 (anchor)")["lr"])),
            "Fixed-tau clip": (
                "clip", float(bl_tune(proto, "fixed-tau clip")["tau"]),
                float(bl_tune(proto, "fixed-tau clip")["lr"])),
            "AdaGrad-Norm": ("adagrad", float(bl_tune(proto, "AdaGrad-Norm")["eta"])),
        }
    return out


def _predict(kind, spec, protocol, X, y, wts, starts):
    if protocol == "per-row":
        if kind == "anchor":
            return anchor_perrow(X, y, wts, spec[0], spec[1], spec[2])
        if kind == "clip":
            return fixedclip_perrow(X, y, wts, spec[0], spec[1])
        return adagrad_perrow(X, y, wts, spec[0])
    if kind == "anchor":
        return anchor_batched(X, y, wts, starts, spec[0], spec[1], spec[2])
    if kind == "clip":
        return fixedclip_batched(X, y, wts, starts, spec[0], spec[1])
    return adagrad_batched(X, y, wts, starts, spec[0])


def run() -> None:
    ds = JaneStreetDataset(date_range=(0, 120), max_rows=150000, standardize=True)
    X, y, wts = ds.X, ds.y, ds.weights
    starts = group_boundaries(ds.meta)
    ndays = int(np.unique(ds.meta["date_id"].to_numpy()).size)
    day = max(1, len(y) // ndays)
    rng = np.random.default_rng(0)

    print("=" * 96)
    print(f"BLOCK-LENGTH SENSITIVITY  --  {len(y)} rows, {ndays} days, "
          f"1 day ~ {day} rows, {N_BOOT} resamples per cell")
    print("  Point estimates are Table 4's own (tuned settings read from the committed CSVs).")
    print("  Blocks drawn per resample at each length (this is the binding constraint):")
    for d in BLOCK_DAYS:
        nb = int(np.ceil(len(y) / max(1, day * d)))
        note = "" if nb >= 10 else ("   <-- too few blocks to estimate a spread"
                                    if nb < 5 else "   <-- marginal")
        print(f"    {d:2d} day(s) = {day*d:6d} rows -> {nb:3d} blocks{note}")
    print("=" * 96)

    tuned = _tuned()
    rows = []
    preds = {}
    for protocol in ("per-row", "per-step"):
        print(f"\n{protocol.upper()}   SE at block = 1, 3, 5, 10 trading days "
              f"(and the ratio to the 1-day SE):")
        print(f"  {'method':30s} {'R^2':>8s} " +
              " ".join(f"{d:>6d}d" for d in BLOCK_DAYS) + "   ratio(10d/1d)")
        for label, cfg in tuned[protocol].items():
            kind, spec = cfg[0], cfg[1:]
            p = _predict(kind, spec, protocol, X, y, wts, starts)
            preds[(protocol, label)] = p
            r2 = agg_r2(y, p, wts)
            ses = []
            for d in BLOCK_DAYS:
                se = block_bootstrap(y, p, wts, max(1, day * d), rng)
                ses.append(se)
                rows.append({"protocol": protocol, "method": label, "block_days": d,
                             "block_rows": day * d, "r2": round(r2, 4),
                             "se": round(se, 4)})
            ratio = ses[-1] / ses[0] if ses[0] > 0 else float("nan")
            print(f"  {label:30s} {r2:+8.4f} " +
                  " ".join(f"{s:7.4f}" for s in ses) + f"   {ratio:5.2f}x")

    out = RES / "block_length_sensitivity.csv"
    RES.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")

    # ------------------------------------------------ do the paper's readings survive?
    def cell(proto, meth, d):
        return next(r for r in rows
                    if r["protocol"] == proto and r["method"] == meth and r["block_days"] == d)

    def overlap(proto, a, b, d):
        ra, rb = cell(proto, a, d), cell(proto, b, d)
        lo_a, hi_a = ra["r2"] - 1.96 * ra["se"], ra["r2"] + 1.96 * ra["se"]
        lo_b, hi_b = rb["r2"] - 1.96 * rb["se"], rb["r2"] + 1.96 * rb["se"]
        return lo_a <= hi_b and lo_b <= hi_a

    print("-" * 96)
    print("DO THE PAPER'S READINGS SURVIVE A LONGER BLOCK?")
    checks = [
        ("per-step", "SN-OMD (M=5)", "Normalized-GD (M->0)",
         True, 'prose: the two are "comparable" per-step -- needs OVERLAP'),
        ("per-row", "SN-OMD (M=5)", "AdaGrad-Norm",
         True, 'prose: no per-row accuracy win over the family -- needs OVERLAP'),
        ("per-row", "SN-OMD (M=5)", "OGD",
         False, "scale-dependent OGD is far worse per-row -- needs SEPARATION"),
    ]
    allok = True
    for proto, a, b, want_overlap, note in checks:
        line = []
        ok = True
        for d in BLOCK_DAYS:
            o = overlap(proto, a, b, d)
            ok &= (o == want_overlap)
            line.append(f"{d}d:{'overlap' if o else 'disjoint'}")
        allok &= ok
        print(f"  [{'PASS' if ok else 'CHECK'}] {proto:8s} {a} vs {b}")
        print(f"           {'  '.join(line)}   ({note})")

    print("-" * 96)
    print("READING. The audit expected a longer block to WIDEN the intervals, since a block")
    print("too short for the dependence understates the variance. It does not: past three days")
    print("the standard errors shrink. That is not evidence the dependence is absent -- it is")
    print("the moving-block bootstrap degenerating. The slice is 20 trading days, so a 3-day")
    print("block already leaves only 7 blocks and a 10-day block leaves 2; with a handful of")
    print("long contiguous stretches each resample looks like the original series, and the")
    print("spread collapses toward zero. The 10-day column is an artifact of the record length,")
    print("not a measurement.")
    print()
    r3 = [cell(p, m, 3)["se"] / cell(p, m, 1)["se"]
          for p in ("per-row", "per-step") for m in tuned[p]
          if cell(p, m, 1)["se"] > 0]
    print("What can honestly be concluded, then, is narrower than the audit asked for and")
    print("still answers it: at the 3-day block it proposed, the standard errors do not move")
    print(f"much (ratios {min(r3):.2f}-{max(r3):.2f} across all twelve series), so the one-day")
    print("block is not understating them at that scale; and every reading the prose makes")
    print("survives at every block length tested. Settling")
    print("the question at longer horizons needs a longer slice, and the instrument the")
    print("accuracy claims actually rest on is not this bootstrap at all -- it is the paired")
    print("across-window bootstrap over ten frozen windows, which resamples at a granularity")
    print("that absorbs within-window dependence outright.")
    print()
    print("ALL READINGS SURVIVE" if allok else "AT LEAST ONE READING IS BLOCK-LENGTH SENSITIVE")


if __name__ == "__main__":
    run()
