"""Mechanical staleness guard: committed data artifacts must match their generator.

Motivation. This bug class has cost the paper twice: a leaky-R^2 CSV and, later, a
``tracker_a1.csv`` whose 6.7/8.1/62 ratios were left stale after the causal-standardization
fix changed the code that produces them (the paper quoted the old build product for several
audit passes). Prose review does not catch a number that no longer matches its script. This
test does: it re-runs each artifact's generator into a temp directory and fails on numeric
diff against the committed file.

Scope. Only *deterministic* CSVs that back numbers in the paper are guarded here. Stochastic
or expensive artifacts (MNIST, the 400-seed synthetic sweep) are out of scope for a fast,
mechanical test -- they are pinned by fixed seeds in their own scripts instead. PNG figures
are intentionally excluded too: binary/rasterization diffs are platform-fragile and would
produce false failures; the numbers a figure encodes live in the CSV it is drawn from, which
*is* guarded. Adding a new guarded CSV is one entry in ``ARTIFACTS``.

Skips cleanly when the Jane Street parquet is absent (same guard as test_dataset.py), so it
is a no-op in a data-less CI checkout and a real check on the author's machine.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import numpy as np
import polars as pl
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
JANE_TRAIN_DIR = PROJECT_ROOT / "data" / "raw" / "jane" / "train.parquet"
DATA_AVAILABLE = JANE_TRAIN_DIR.exists()

requires_jane_data = pytest.mark.skipif(
    not DATA_AVAILABLE,
    reason="Jane Street data not found under data/raw/jane; run 'python scripts/download_data.py' first.",
)

# Each entry: (generator module name, committed CSV path, string key column used to align
# rows before comparing the numeric columns). The generator is expected to write the CSV
# under its module-level ``OUT`` directory, which the test redirects to a temp dir.
ARTIFACTS = [
    ("research_tracker", PROJECT_ROOT / "results" / "research" / "tracker_a1.csv", "tracker"),
]


def _regenerate(module_name: str, out_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Import the generator with its OUT redirected to ``out_dir`` and run its main()."""
    monkeypatch.syspath_prepend(str(SCRIPTS_DIR))
    # argparse-based scripts read sys.argv; give them a clean argv so defaults are used.
    monkeypatch.setattr(sys, "argv", [module_name])
    module = __import__(module_name)
    # Redirect writes: generators reference module-global OUT (and ROOT for a relative_to
    # print). Point both at the temp tree so nothing touches the committed artifact.
    monkeypatch.setattr(module, "OUT", out_dir, raising=False)
    monkeypatch.setattr(module, "ROOT", out_dir.parent.parent.parent, raising=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    module.main()


def _numeric_frame(path: Path) -> tuple[pl.DataFrame, list[str]]:
    df = pl.read_csv(path)
    num_cols = [c for c, dt in zip(df.columns, df.dtypes) if dt.is_numeric()]
    return df, num_cols


@requires_jane_data
@pytest.mark.parametrize("module_name,committed_csv,key_col", ARTIFACTS,
                         ids=[a[0] for a in ARTIFACTS])
def test_committed_csv_matches_generator(
    module_name: str, committed_csv: Path, key_col: str, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert committed_csv.exists(), f"committed artifact missing: {committed_csv}"

    out_dir = tmp_path / "results" / "research"
    _regenerate(module_name, out_dir, monkeypatch)

    fresh_csv = out_dir / committed_csv.name
    assert fresh_csv.exists(), f"generator {module_name} did not write {committed_csv.name}"

    committed, num_cols = _numeric_frame(committed_csv)
    fresh, _ = _numeric_frame(fresh_csv)

    # Align rows by the string key so row-order changes don't cause spurious failures.
    committed = committed.sort(key_col)
    fresh = fresh.sort(key_col)
    assert committed[key_col].to_list() == fresh[key_col].to_list(), (
        f"{committed_csv.name}: row keys differ between committed and freshly generated"
    )

    stale = []
    for col in num_cols:
        c = committed[col].to_numpy().astype(float)
        f = fresh[col].to_numpy().astype(float)
        if not np.allclose(c, f, rtol=1e-6, atol=1e-9, equal_nan=True):
            for k, cv, fv in zip(committed[key_col].to_list(), c, f):
                if not np.isclose(cv, fv, rtol=1e-6, atol=1e-9, equal_nan=True):
                    stale.append(f"    {col} [{k}]: committed={cv!r}  regenerated={fv!r}")
    assert not stale, (
        f"{committed_csv.name} is STALE -- it no longer matches {module_name}.py. "
        f"Regenerate it (`python scripts/{module_name}.py`) and re-check every paper "
        f"number sourced from it:\n" + "\n".join(stale)
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
