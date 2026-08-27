"""Grid-interior audit: no claim may be read off the edge of the range that produced it.

Four separate defects in this project have had one shape -- *a statistic computed at the edge of
a swept range, reported as if the range were the domain*:

  * round-5 (E.12)  the Cutkosky--Mehta cell was tuned on a grid whose optimum sat on a
                    boundary, with the true optimum off the edge.
  * T4 step 2       normalized-GD never diverges on the committed grid, so its stability ceiling
                    is right-censored; the uncorrected code printed a 1.88x spread and a
                    FALSIFIED verdict that was purely an artifact of the grid ending.
  * T4B run 1       the clippers were launched on LRS_SF, whose FLOOR sits above their entire
                    operating range; every setting diverged and "diverges 10/10" would have been
                    an artifact of where the sweep started.
  * T4B invariant   sup||g|| was taken from a different window than the ceilings, which is the
                    same error in the domain rather than the range.

``research_grid_adequacy.py`` checks this for Table-2's learning rates, but it does so by
*re-running* the sweeps (10-20 min) and only for that one table. This is the static counterpart:
it reads committed artifacts only, covers every grid-based claim in a declared registry, and is
cheap enough to run as a test. The registry is the point -- an edge is not automatically a bug,
but an **undeclared** edge is, exactly as ``PAPER_CLAIMS`` treats a number that drifts from its
CSV.

Two distinct failures are checked, because they are not the same thing:

  OPTIMUM AT AN EDGE   the argmax of a metric sits at the smallest or largest grid value, so the
                       reported optimum is a lower bound on the true one.
  CEILING NOT BRACKETED  a divergence threshold is claimed but the sweep either never diverges
                       (censored above) or diverges everywhere (censored below), so no threshold
                       was located at all.

Usage::

    .venv/Scripts/python.exe scripts/research_grid_interior.py            # audit the registry
    .venv/Scripts/python.exe scripts/research_grid_interior.py --survey   # scan every artifact
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

GRID_COLS = ("learning_rate", "lr", "cap", "M", "tau", "c_units", "block", "W")


# --------------------------------------------------------------------------- primitives
def optimum_edge(df, grid_col, metric_col, group_cols=(), diverged_col=None):
    """For each group, where does the argmax of `metric_col` sit within the grid?

    Returns one dict per group with `position` in {"low-edge", "interior", "high-edge",
    "degenerate"}. "degenerate" means fewer than three distinct grid values, where "interior"
    is not a meaningful category.
    """
    out = []
    groups = ([{}] if not group_cols
              else df.select(group_cols).unique().sort(group_cols).to_dicts())
    for g in groups:
        sub = df
        for k, v in g.items():
            sub = sub.filter(pl.col(k).is_null() if v is None else pl.col(k) == v)
        if diverged_col is not None and diverged_col in sub.columns:
            sub = sub.filter(~pl.col(diverged_col))
        sub = sub.filter(pl.col(metric_col).is_finite()).sort(grid_col)
        if sub.height == 0:
            out.append({**g, "position": "degenerate", "n": 0, "argmax": None,
                        "lo": None, "hi": None})
            continue
        vals = sorted(set(sub[grid_col].to_list()))
        best = sub.sort(metric_col, descending=True).row(0, named=True)
        a = best[grid_col]
        if len(vals) < 3:
            pos = "degenerate"
        elif a == vals[0]:
            pos = "low-edge"
        elif a == vals[-1]:
            pos = "high-edge"
        else:
            pos = "interior"
        out.append({**g, "position": pos, "n": len(vals), "argmax": a,
                    "lo": vals[0], "hi": vals[-1],
                    "metric": round(float(best[metric_col]), 5)})
    return out


def ceiling_status(df, grid_col, diverged_col, group_cols=(), min_points=2):
    """For each group, is the divergence threshold bracketed by the grid?

    "located" means the sweep contains both a stable point and a diverged point above it.
    "censored-high" means nothing diverged: the ceiling is above the grid. "censored-low" means
    everything diverged: the ceiling is below the grid, and no stable setting was ever seen.
    """
    out = []
    groups = ([{}] if not group_cols
              else df.select(group_cols).unique().sort(group_cols).to_dicts())
    for g in groups:
        sub = df
        for k, v in g.items():
            sub = sub.filter(pl.col(k).is_null() if v is None else pl.col(k) == v)
        # Some artifacts store the flag as text ("true"/"True"). Coerce rather than skip: a
        # string dtype is a serialisation detail, not a reason to leave a sweep unaudited.
        sub = sub.sort(grid_col)
        if sub.schema[diverged_col] == pl.String:
            sub = sub.with_columns(
                pl.col(diverged_col).str.to_lowercase().is_in(["true", "1", "yes"])
                .alias(diverged_col)
            )
        stable = sub.filter(~pl.col(diverged_col))
        div = sub.filter(pl.col(diverged_col))
        # A single grid point is not a censored sweep, it is not a sweep. Saying "censored"
        # there would bury the real findings in rows that were never asking the question --
        # a check nobody can read is a check nobody runs.
        if sub.select(grid_col).n_unique() < min_points:
            st = "degenerate"
        elif stable.height == 0:
            st = "censored-low"
        elif div.height == 0:
            st = "censored-high"
        else:
            st = "located"
        out.append({**g, "status": st,
                    "last_stable": (float(stable.row(stable.height - 1, named=True)[grid_col])
                                    if stable.height else None),
                    "first_diverged": (float(div.row(0, named=True)[grid_col])
                                       if div.height else None)})
    return out


# ---------------------------------------------------------------------------- the registry
# (label, csv, kind, kwargs, expected)  -- `expected` maps each group key to the status that is
# ACCEPTED for it, with the reason. Anything not listed must be "interior"/"located".
REGISTRY = [
    (
        "tab:jane / fig:main lr sweep, scale-free methods",
        "normalize_continuous.csv", "optimum",
        {"grid_col": "learning_rate", "metric_col": "weighted_r2",
         "group_cols": ["method"], "diverged_col": "diverged"},
        {"ogd": "low-edge  -- OGD's optimum is at the grid floor; the instrument gives it "
                "LRS_OGD, a lower decade, and tab:jane sources its number from there"},
    ),
    (
        "tab:jane / fig:main stability ceiling, scale-free methods",
        "normalize_continuous.csv", "ceiling",
        {"grid_col": "learning_rate", "diverged_col": "diverged", "group_cols": ["method"]},
        {"normgd": "censored-high -- normalized-GD does not diverge anywhere on this grid. "
                   "T4 recorded this; it is why the P invariant is inconclusive, and the "
                   "paper makes no ceiling claim for it beyond 'stays bounded far higher'"},
    ),
    (
        "the clippers' single-window sweep (C-23's source)",
        "continuous_stream.csv", "ceiling",
        {"grid_col": "learning_rate", "diverged_col": "diverged", "group_cols": ["method"]},
        {"adaptive_clip": "censored-high -- sweep stops at 3e-2 with the method still improving; "
                          "this is precisely what made C-23 look like a taxonomy correction, and "
                          "T4B located the real ceiling at [1e-2,2e-2) on the instrument",
         "robust_omd[catoni]": "censored-high -- same sweep, same reason",
         "robust_omd[median_of_means]": "censored-high -- same sweep, same reason",
         "robust_omd[trimmed_mean]": "censored-high -- same sweep, same reason"},
    ),
    (
        "the data-free Jane mini-slice (audit finding 6's reviewer path)",
        "jane_mini.csv", "ceiling",
        {"grid_col": "lr", "diverged_col": "diverged", "group_cols": ["method", "protocol"]},
        {"Normalized-GD (M->0)": "censored-high -- a bounded scale-free method on a seeded "
                                 "mini-slice at small rates. No ceiling is claimed for this "
                                 "artifact; it exists to show the PATH runs without market "
                                 "data, not to locate a stability boundary",
         "SN-OMD (M=5)": "censored-high -- same artifact, same reason",
         "Scale-adaptive OGD (M->inf)": "censored-high per-step only -- same artifact; the "
                                        "per-row arm does locate a ceiling"},
    ),
    (
        "T4B clipper ceiling on the frozen instrument",
        "t4b_clipper_ceiling.csv", "declared",
        {"flag_col": "ceiling_located", "group_cols": ["protocol", "method"]},
        {},
    ),
]


def _fmt(g, keys):
    return " / ".join(str(g[k]) for k in keys) if keys else "(all)"


def audit() -> int:
    print("=" * 100)
    print("GRID-INTERIOR AUDIT -- no claim may be read off the edge of the range that made it")
    print("=" * 100)
    bad = []
    for label, csv, kind, kw, expected in REGISTRY:
        path = RES / csv
        if not path.exists():
            print(f"\n### {label}\n  MISSING: {csv}")
            bad.append((label, csv, "missing artifact"))
            continue
        df = pl.read_csv(path)
        print(f"\n### {label}\n    {csv}")
        gcols = kw.get("group_cols", [])
        if kind == "optimum":
            for r in optimum_edge(df, **kw):
                key = _fmt(r, gcols)
                ok = r["position"] in ("interior", "degenerate")
                note = expected.get(r[gcols[0]] if gcols else None) if expected else None
                mark = "ok " if ok else ("DECLARED" if note else "**UNDECLARED**")
                print(f"  {mark:12s} {key:30s} argmax={r['argmax']} in "
                      f"[{r['lo']},{r['hi']}]  {r['position']}")
                if note:
                    print(f"               {note}")
                if not ok and not note:
                    bad.append((label, key, r["position"]))
        elif kind == "ceiling":
            for r in ceiling_status(df, **kw):
                key = _fmt(r, gcols)
                ok = r["status"] == "located"
                note = expected.get(r[gcols[0]] if gcols else None) if expected else None
                mark = "ok " if ok else ("DECLARED" if note else "**UNDECLARED**")
                print(f"  {mark:12s} {key:30s} {r['status']:14s} "
                      f"stable<={r['last_stable']} diverged@{r['first_diverged']}")
                if note:
                    print(f"               {note}")
                if not ok and not note:
                    bad.append((label, key, r["status"]))
        elif kind == "declared":
            for row in df.iter_rows(named=True):
                key = _fmt(row, gcols)
                ok = bool(row[kw["flag_col"]])
                print(f"  {'ok ' if ok else '**UNDECLARED**':12s} {key:30s} "
                      f"ceiling_located={ok}")
                if not ok:
                    bad.append((label, key, "ceiling not located"))

    print("\n" + "=" * 100)
    if bad:
        print(f"{len(bad)} UNDECLARED edge/censoring finding(s):")
        for lab, key, what in bad:
            print(f"  {lab} :: {key} :: {what}")
        print("\nEither widen the grid, or declare the edge in REGISTRY with the reason it is")
        print("acceptable. A declared edge is a disclosed limitation; an undeclared one is a")
        print("number reported as if the sweep were the domain.")
    else:
        print("No undeclared edge or censoring findings. Every grid-based claim in the registry")
        print("either has an interior optimum and a bracketed ceiling, or declares why not.")
    print("=" * 100)
    return 1 if bad else 0


def survey() -> int:
    """Scan every artifact with a grid column -- a map, not a gate."""
    print("SURVEY: every committed artifact carrying a grid axis\n")
    for path in sorted(RES.rglob("*.csv")):
        try:
            df = pl.read_csv(path, infer_schema_length=2000)
        except Exception:
            continue
        grids = [c for c in GRID_COLS if c in df.columns]
        if not grids or "diverged" not in df.columns:
            continue
        # `arm` matters: c12b_blockmed holds two FIXED settings evaluated across ten windows,
        # not a sweep, and omitting it makes the two arms' rates look like a two-point grid.
        gcols = [c for c in ("method", "learner", "protocol", "arm") if c in df.columns]
        for gc in grids[:1]:
            # A sweep with three points or fewer cannot locate a ceiling, so flagging it as
            # censored is noise. The survey is a map and needs judgement; REGISTRY is the gate.
            rows = ceiling_status(df, gc, "diverged", gcols, min_points=4)
            flagged = [r for r in rows if r["status"] not in ("located", "degenerate")]
            if flagged:
                print(f"  {path.relative_to(RES).as_posix():46s} grid={gc}")
                for r in flagged:
                    print(f"      {_fmt(r, gcols):32s} {r['status']}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--survey", action="store_true")
    a = ap.parse_args()
    raise SystemExit(survey() if a.survey else audit())
