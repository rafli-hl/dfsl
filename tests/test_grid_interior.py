"""Every grid-based claim must have an interior optimum and a bracketed ceiling, or declare why not.

Four defects in this project have had one shape -- a statistic read off the edge of the range
that produced it (E.12's boundary optimum, T4's right-censored ceiling, T4B's grid floor, T4B's
mixed-stream `sup`). Each was caught by hand, after the fact, by someone happening to look.

``research_grid_adequacy.py`` guards the same property for Table 2, but by re-running the sweeps
(10-20 min) and only for that table. This is the static gate: it reads committed bytes, so it is
a real check in a checkout with no market data, and it runs in a second.

The registry in ``research_grid_interior.REGISTRY`` is the contract. An edge is not automatically
a bug -- but an **undeclared** edge is, on the same principle as ``PAPER_CLAIMS``: a number whose
provenance is not stated cannot be audited. Adding a declaration is cheap and forces the reason
to be written down; leaving one out fails here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from research_grid_interior import (  # noqa: E402
    REGISTRY,
    RES,
    ceiling_status,
    optimum_edge,
)


def _key(row, group_cols):
    return " / ".join(str(row[c]) for c in group_cols) if group_cols else "(all)"


@pytest.mark.parametrize("entry", REGISTRY, ids=[e[0] for e in REGISTRY])
def test_no_undeclared_grid_edge(entry) -> None:
    label, csv, kind, kw, expected = entry
    path = RES / csv
    assert path.exists(), f"{label}: registry points at a missing artifact, {csv}"
    df = pl.read_csv(path)
    group_cols = kw.get("group_cols", [])

    problems = []
    if kind == "optimum":
        for r in optimum_edge(df, **kw):
            if r["position"] in ("interior", "degenerate"):
                continue
            if group_cols and expected.get(r[group_cols[0]]):
                continue
            problems.append(
                f"    {_key(r, group_cols)}: argmax {r['argmax']} sits at the "
                f"{r['position']} of [{r['lo']}, {r['hi']}]"
            )
    elif kind == "ceiling":
        for r in ceiling_status(df, **kw):
            if r["status"] in ("located", "degenerate"):
                continue
            if group_cols and expected.get(r[group_cols[0]]):
                continue
            problems.append(
                f"    {_key(r, group_cols)}: {r['status']} -- stable to "
                f"{r['last_stable']}, first divergence {r['first_diverged']}"
            )
    elif kind == "declared":
        for row in df.iter_rows(named=True):
            if not bool(row[kw["flag_col"]]):
                problems.append(f"    {_key(row, group_cols)}: ceiling not located")
    else:
        pytest.fail(f"{label}: unknown registry kind {kind!r}")

    assert not problems, (
        f"{label} ({csv}): {len(problems)} undeclared edge/censoring finding(s):\n"
        + "\n".join(problems)
        + "\n\n  Either widen the grid so the claim sits inside it, or add a declaration to "
        "REGISTRY saying why the edge is acceptable. A declared edge is a disclosed "
        "limitation; an undeclared one is a number reported as if the sweep were the domain."
    )
