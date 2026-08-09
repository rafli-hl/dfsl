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

Two guard styles.
  (1) Regeneration guard (``ARTIFACTS``): re-run the generator and diff. Requires the Jane
      data and a fast, deterministic generator.
  (2) Input-hash tripwire (``INPUT_HASHES``): pin the sha256 of a *derived input* that many
      paper numbers are computed from but which is too slow to regenerate in a unit test
      (the @w* gradient-norm sample feeds the A3 W_s/beta numbers, tab:tracker, the
      tracker_a1.csv regeneration above, and the headline alpha@w*). If that file ever
      changes, every downstream number must be re-derived -- this test fails and says which.
      It only reads bytes, so it runs even in a data-less checkout (a pure identity check).
"""

from __future__ import annotations

import hashlib
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

# Derived inputs too slow to regenerate in a unit test, pinned by content hash instead.
# Each entry: (committed path, expected sha256, one-line note on what depends on it). If a
# hash mismatches, the file was regenerated -> re-verify every paper number it feeds.
# ``gradnorm_at_wstar.npy`` is written by research_findings.py (200k causal gradient norms at
# the fixed least-squares predictor); research_tracker.py consumes it, so the regeneration
# guard above is only meaningful while this input is itself pinned.
INPUT_HASHES = [
    (
        PROJECT_ROOT / "results" / "research" / "gradnorm_at_wstar.npy",
        "f0ec26872105da240f37250bebfe06ebe9a0e247fc7732ee105ce9310d19c42f",
        "A3 W_s/beta (Sec 4.3), tab:tracker ratios, tracker_a1.csv, and the alpha@w* tail index",
    ),
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


@pytest.mark.parametrize("path,expected_sha,depends", INPUT_HASHES,
                         ids=[p.name for p, _, _ in INPUT_HASHES])
def test_input_artifact_hash_pinned(path: Path, expected_sha: str, depends: str) -> None:
    """A derived input feeding several paper numbers must not silently change.

    Pure byte-hash of a committed file: no Jane data, no regeneration, platform-independent.
    A mismatch means the file was rebuilt -> the numbers it feeds are potentially stale.
    """
    assert path.exists(), f"pinned input artifact missing: {path}"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected_sha, (
        f"{path.name} CHANGED (sha256 {actual} != pinned {expected_sha}). It feeds: {depends}. "
        f"Re-derive those numbers from the new file, then update the pinned hash in "
        f"INPUT_HASHES to bless the change."
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
