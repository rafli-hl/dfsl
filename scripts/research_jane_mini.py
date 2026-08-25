"""A reviewer-runnable Jane path: seeded mini-slice, plus a hash check on the real one.

The headline market numbers need the Jane Street Kaggle data, which the competition rules
do not let us redistribute, so a reviewer without a Kaggle account has until now been
unable to run *any* of the Jane code path -- not the loader, not the causal
standardization, not the group-boundary batching, not the weighted-R^2 evaluation. The
synthetic suite is data-free but exercises none of that.

This closes the gap from both ends.

**Without the data.** ``--build`` writes a deterministic mini-slice in the exact Jane
schema (79 features, nine responders, the ``date_id``/``time_id``/``symbol_id``/``weight``
metadata, one parquet part per day) from a fixed seed, and ``--run`` puts it through the
*same* ``JaneStreetDataset`` loader and the *same* update harness the paper's tables use.
The stream carries the paper's mechanism and nothing else: a drifting volatility scale with
**Gaussian** innovations, so the pooled gradient tail can only be heavy because the scale
moves -- and causal normalization is therefore able to remove it.

What that reproduces is the *dichotomy*, not the numbers. Scale-dependent OGD destabilizes
as the rate rises while every bounded scale-free method stays bounded, and causal
normalization lightens the Hill index. It is a smoke test with teeth: it fails if the
loader, the tracker's predictability, the clipping, or the evaluation breaks. It is not
evidence for the paper's R^2 values, and the output says so.

**With the data.** ``--verify`` recomputes the canonical slice -- ``date_range=(0,120)``,
``max_rows=150000``, causal standardization -- and prints the sha256 of the resulting
arrays, so a reviewer holding their own Kaggle download can confirm in one command that
their input is byte-identical to ours before spending the long compute.

Usage::

    .venv/Scripts/python.exe scripts/research_jane_mini.py --build --run
    .venv/Scripts/python.exe scripts/research_jane_mini.py --verify      # needs the real data
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_batched_check import _step, group_boundaries  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402
from dfsl.evaluation.metrics import weighted_r2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MINI = ROOT / "data" / "raw" / "jane_mini"
RES = ROOT / "results" / "research"

N_FEATURES = 79
SEED = 0

# The canonical slice the paper's Jane tables are computed on.
CANON = dict(date_range=(0, 120), max_rows=150_000, standardize=True)
# sha256 of that slice, recorded by running --verify on a machine that has the data.
# Empty means "not yet pinned"; --verify prints the value to paste here.
CANON_SHA = "7ec2ab6fc13f23adec33be2d38cef8d83701bc1bd6ae88adb1a1769dc1597987"

METHODS = [
    ("OGD (scale-dependent)", "ogd", 0.0, False),
    ("Normalized-GD (M->0)", "normgd", 0.0, True),
    ("Scale-adaptive OGD (M->inf)", "snomd", 1e9, False),
    ("SN-OMD (M=5)", "snomd", 5.0, True),
]
LRS = [1e-3, 1e-2, 1e-1, 0.5, 1.0, 2.0, 5.0]


# --------------------------------------------------------------------------- build
def build(n_days: int = 20, n_times: int = 150, n_symbols: int = 10,
          seed: int = SEED, base: Path | None = None) -> Path:
    """Write a seeded mini-slice in the Jane schema.

    The construction is deliberately thin, and its one deliberate choice is that the
    innovations are **Gaussian**. Any heaviness in the pooled gradient-norm tail is then
    manufactured entirely by the drifting scale -- the same construction as the GARCH
    surrogate null control, and the paper's own claim in its cleanest form. A Student-t
    innovation would also produce a heavy pooled tail, but through a channel normalization
    cannot remove, which would make the test prove less.

    The scale is a within-day slow drift on top of a between-day regime with occasional
    jumps: the piecewise-slowly-varying picture the tracker analysis assumes. Rows are laid
    out as ``n_times`` timestamps x ``n_symbols`` symbols per day so that the per-step
    protocol has the real group structure to batch over; without that, every group is a
    single row and per-step silently collapses onto per-row.

    Everything else about the real data -- the feature semantics, which responder matters,
    the symbol universe -- is absent, which is the point. Nothing here can be mistaken for
    the competition data.
    """
    rng = np.random.default_rng(seed)
    beta = rng.normal(0.0, 1.0, N_FEATURES) / np.sqrt(N_FEATURES)

    out = (base or MINI) / "train.parquet"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.rglob("*.parquet"):
        f.unlink()

    # Between-day regime: log-scale random walk with occasional jumps. The two constants
    # are set so that twenty days span a scale range of ~20x, which is the order of drift a
    # real multi-regime year carries; at much less drift there is too little heaviness to
    # manufacture and the lightening check below has nothing to detect.
    log_sigma = np.cumsum(rng.normal(0.0, 0.5, n_days))
    log_sigma += rng.normal(0.0, 1.5, n_days) * (rng.random(n_days) < 0.15)
    sigma_day = np.exp(log_sigma - log_sigma.mean())

    total = 0
    n = n_times * n_symbols
    time_id = np.repeat(np.arange(n_times, dtype=np.int64), n_symbols)
    symbol_id = np.tile(np.arange(n_symbols, dtype=np.int64), n_times)
    for d in range(n_days):
        X = rng.normal(0.0, 1.0, (n, N_FEATURES))
        # within-day slow drift on top of the day's regime, Gaussian innovations
        intraday = np.exp(np.linspace(-0.15, 0.15, n_times) * rng.normal(1.0, 0.5))
        sigma = sigma_day[d] * np.repeat(intraday, n_symbols)
        eps = rng.normal(0.0, 1.0, n) * sigma
        y6 = X @ beta * 0.3 + eps * 0.5
        cols = {
            "date_id": np.full(n, d, dtype=np.int64),
            "time_id": time_id,
            "symbol_id": symbol_id,
            "weight": np.exp(rng.normal(0.0, 0.4, n)),
        }
        for j in range(N_FEATURES):
            cols[f"feature_{j:02d}"] = X[:, j]
        for j in range(9):
            cols[f"responder_{j}"] = y6 if j == 6 else rng.normal(0.0, 1.0, n)
        part = out / f"chunk_{d:03d}"
        part.mkdir(parents=True, exist_ok=True)
        pl.DataFrame(cols).write_parquet(part / "part-0.parquet")
        total += n

    shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"built {total} rows over {n_days} days "
          f"({n_times} times x {n_symbols} symbols) -> {shown}")
    print(f"  day-scale drift {sigma_day.min():.3f}..{sigma_day.max():.3f} "
          f"({sigma_day.max()/sigma_day.min():.1f}x), Gaussian innovations "
          f"(so a heavy pooled tail can only come from the drift)")
    return out


# ------------------------------------------------------------------------- run path
def _perrow(X, y, wts, mode, cap, lr):
    d = X.shape[1]
    w = np.zeros(d)
    s = None
    preds = np.empty(len(y))
    norms = np.empty(len(y))
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i])
            preds[i] = pred
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
            norms[i] = float(np.linalg.norm(g))
        w, s = _step(mode, cap, w, g, s, i + 1, lr)
    return preds, float(np.linalg.norm(w)), norms


def _batched(X, y, wts, starts, mode, cap, lr):
    d = X.shape[1]
    w = np.zeros(d)
    s = None
    preds = np.empty(len(y))
    ends = np.append(starts[1:], len(y))
    for k, (a, b) in enumerate(zip(starts, ends), start=1):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w
            preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        w, s = _step(mode, cap, w, g, s, k, lr)
    return preds, float(np.linalg.norm(w))


def hill(x: np.ndarray, k: int) -> float:
    """Hill tail-index estimate on the k largest order statistics."""
    x = np.sort(x[np.isfinite(x) & (x > 0)])[::-1]
    k = min(k, len(x) - 1)
    if k < 10:
        return float("nan")
    return float(1.0 / np.mean(np.log(x[:k] / x[k])))


DIVERGED = 1e6      # ||w_T|| above this is divergence, not a merely bad rate


def grads_at_wstar(X, y, wts):
    """Gradient norms at the best fixed linear predictor, as the paper's diagnostic uses.

    The tail diagnostic is a statement about the gradient *process*, so it is taken at a
    fixed w -- not along a trajectory, which would confound the tail with the learner's own
    divergence. w* is the weighted least-squares solution on the slice.
    """
    A = X * wts[:, None]
    wstar = np.linalg.solve(A.T @ X + 1e-6 * np.eye(X.shape[1]), A.T @ y)
    resid = X @ wstar - y
    return np.abs(2.0 * wts * resid) * np.linalg.norm(X, axis=1)


def run() -> int:
    if not (MINI / "train.parquet").exists():
        print("mini-slice not built; run with --build first")
        return 1
    ds = JaneStreetDataset(data_dir=MINI, max_rows=None, standardize=True)
    X, y, wts = ds.X, ds.y, ds.weights
    starts = group_boundaries(ds.meta)
    print("=" * 88)
    print(f"JANE MINI-SLICE  --  {len(y)} rows, {len(starts)} groups, "
          f"{ds.meta['date_id'].n_unique()} days, seed {SEED}")
    print("  synthetic. This reproduces the paper's MECHANISM, not its numbers.")
    print("=" * 88)

    rows = []
    for protocol in ("per-row", "per-step"):
        print(f"\n{protocol.upper()}   final iterate norm at each rate "
              f"(D = diverged, i.e. > {DIVERGED:.0g}):")
        print(f"  {'method':30s} " + " ".join(f"{lr:>9g}" for lr in LRS))
        for label, mode, cap, bounded in METHODS:
            cells = []
            for lr in LRS:
                if protocol == "per-row":
                    p, wn, _ = _perrow(X, y, wts, mode, cap, lr)
                else:
                    p, wn = _batched(X, y, wts, starts, mode, cap, lr)
                r2 = float(weighted_r2(y, p, wts))
                div = (not np.isfinite(wn)) or wn > DIVERGED
                cells.append("        D" if div else f"{wn:9.2f}")
                rows.append({"protocol": protocol, "method": label, "lr": lr,
                             "r2": r2 if np.isfinite(r2) else None,
                             "w_norm": wn if np.isfinite(wn) else None,
                             "diverged": div, "bounded_family": bounded})
            n_div = sum(1 for c in cells if c.strip() == "D")
            print(f"  {label:30s} " + " ".join(cells) + f"   {n_div}/{len(LRS)} diverged")

    # ---- the assertions the paper's reading rests on ---------------------------------
    print("\n" + "-" * 88)
    ok = True
    for protocol in ("per-row", "per-step"):
        sub = [r for r in rows if r["protocol"] == protocol]
        free = sum(1 for r in sub if r["bounded_family"] and r["diverged"])
        dep = sum(1 for r in sub if not r["bounded_family"] and r["diverged"])
        good = free == 0 and dep > 0
        ok &= good
        print(f"  [{'PASS' if good else 'FAIL'}] {protocol}: the bounded scale-free rows "
              f"diverge {free}/{2*len(LRS)}; the scale-dependent and uncapped rows "
              f"{dep}/{2*len(LRS)}")

    gnorms = grads_at_wstar(X, y, wts)
    k = max(30, len(gnorms) // 20)
    raw = hill(gnorms, k)
    s = None
    tracked = np.empty(len(gnorms))
    for i, gn in enumerate(gnorms):
        sc = max(s if s is not None else gn, 1e-8)
        s = gn if s is None else 0.99 * s + 0.01 * min(gn, 8.0 * s)
        tracked[i] = gn / sc
    norm = hill(tracked, k)
    lighter = np.isfinite(raw) and np.isfinite(norm) and norm > raw
    ok &= bool(lighter)
    print(f"  [{'PASS' if lighter else 'FAIL'}] Hill index at w*, k={k}: pooled "
          f"{raw:.2f} -> causally normalized {norm:.2f} "
          f"({'lighter' if lighter else 'NOT lighter'}; the lightening is the mechanism)")

    RES.mkdir(parents=True, exist_ok=True)
    out = RES / "jane_mini.csv"
    pl.DataFrame(rows).write_csv(out)
    print(f"\n[saved {out.relative_to(ROOT)}]")
    print("These are NOT the paper's Jane numbers. The tables in the paper need the "
          "Kaggle data;\nwhat this shows is that the same code path reproduces the "
          "stability dichotomy and the\nnormalization lightening on a stream whose "
          "drift and tail we set ourselves.")
    return 0 if ok else 1


# ---------------------------------------------------------------------- verify path
def verify() -> int:
    """Hash the canonical real slice so a reviewer can confirm their download matches."""
    try:
        ds = JaneStreetDataset(**CANON)
    except FileNotFoundError as exc:
        print(f"real Jane data not present: {exc}")
        return 1
    h = hashlib.sha256()
    for arr in (ds.X, ds.y, ds.weights):
        h.update(np.ascontiguousarray(arr, dtype=np.float64).tobytes())
    digest = h.hexdigest()
    print(f"canonical slice: {ds.X.shape[0]} rows x {ds.X.shape[1]} features")
    print(f"  date_range={CANON['date_range']}  max_rows={CANON['max_rows']}  "
          f"standardize={CANON['standardize']}")
    print(f"  sha256(X|y|w) = {digest}")
    if not CANON_SHA:
        print("  (no pin recorded yet; paste this into CANON_SHA)")
        return 0
    match = digest == CANON_SHA
    print(f"  pinned        = {CANON_SHA}")
    print("  => " + ("MATCH: your slice is byte-identical to the paper's."
                     if match else
                     "MISMATCH: your download differs from the paper's input."))
    return 0 if match else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true", help="write the seeded mini-slice")
    ap.add_argument("--run", action="store_true", help="run the Jane code path on it")
    ap.add_argument("--verify", action="store_true", help="hash the real canonical slice")
    ap.add_argument("--days", type=int, default=20)
    ap.add_argument("--times", type=int, default=150)
    ap.add_argument("--symbols", type=int, default=10)
    a = ap.parse_args()
    if not (a.build or a.run or a.verify):
        a.build = a.run = True
    rc = 0
    if a.build:
        build(a.days, a.times, a.symbols)
    if a.run:
        rc |= run()
    if a.verify:
        rc |= verify()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
