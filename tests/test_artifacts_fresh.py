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
import re
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


# ---------------------------------------------------------------------------
# (3) Paper-claim cross-check: a number PRINTED IN THE PAPER must match the CSV
#     it is sourced from.
#
# Why this guard exists, and why it is separate from the two above. The
# regeneration guard catches "the CSV no longer matches its generator". It does
# NOT catch "the paper quotes a number the CSV never said" -- which is the
# failure the independent audit logged as Finding 3 (a bootstrap-SE sentence
# sourced to a superseded run while the displayed table came from another), and
# whose recommended remedy was exactly this test. It also does not catch a CSV
# and its generator drifting *together*: when the predictable-scale defect was
# fixed, generator and artifact moved in lockstep, so a regeneration diff would
# have stayed green while twelve paper numbers went stale. Both failures are
# caught here, because this compares the two things that must agree for the
# paper to be true: the printed claim and the measurement behind it.
#
# It reads committed bytes only -- no Jane data, no regeneration -- so unlike
# ARTIFACTS it is a real check in a data-less CI checkout.
#
# Each entry: (label, regex over the .tex, csv name, row selector, checks) where
# every check is (regex group index, csv column, decimal places to compare at).
# Regexes must be specific enough to match exactly once; the test asserts that.
PAPER_TEX = PROJECT_ROOT / "paper" / "iclr2027" / "iclr2027.tex"

_SE = r"\{\\scriptscriptstyle\\pm(\.\d+)\}"

PAPER_CLAIMS = [
    (
        "tab:jane SN-OMD (both protocols)",
        r"\\textbf\{SN-OMD \(\$M\{=\}5\$, ours\)\}\s*&\s*\$([\d.]+)" + _SE
        + r"\$\s*&\s*\$([\d.]+)" + _SE + r"\$",
        "baselines_jane.csv", {"method": "SN-OMD M=5 (anchor)"},
        [(1, "per-row", "r2", 3), (2, "per-row", "se", 3),
         (3, "per-step", "r2", 3), (4, "per-step", "se", 3)],
    ),
    (
        "tab:jane normalized-GD (both protocols)",
        r"Normalized-GD \(\$M\\!\\to\\!0\$\)\s*&\s*\$([\d.]+)" + _SE
        + r"\$\s*&\s*\$([\d.]+)" + _SE + r"\$",
        "baselines_jane.csv", {"method": "normalized-GD (anchor)"},
        [(1, "per-row", "r2", 3), (2, "per-row", "se", 3),
         (3, "per-step", "r2", 3), (4, "per-step", "se", 3)],
    ),
    (
        "tab:jane scale-adaptive OGD (both protocols)",
        r"Scale-adaptive OGD \(\$M\\!\\to\\!\\infty\$\)&\s*\$([\d.]+)" + _SE
        + r"\$\s*&\s*\$([\d.]+)" + _SE + r"\$",
        "table1_errorbars.csv", {"method": "Scale-adaptive OGD (M->inf)"},
        [(1, "per-row", "r2", 3), (2, "per-row", "se", 3),
         (3, "per-step", "r2", 3), (4, "per-step", "se", 3)],
    ),
    (
        # Added after T4 step 0 found tab:jane's scale-dependent half unguarded -- the same
        # gap that let the app:tracker figures drift for two sessions (C-18). The leading
        # newline anchors this to tab:jane's own row: tab:replication also has a line
        # starting "OGD", but it prints no bootstrap SE and so cannot match.
        "tab:jane OGD (both protocols)",
        r"\nOGD\s+&\s*\$([\d.]+)" + _SE + r"\$\s*&\s*\$([\d.]+)" + _SE + r"\$",
        "table1_errorbars.csv", {"method": "OGD"},
        [(1, "per-row", "r2", 3), (2, "per-row", "se", 3),
         (3, "per-step", "r2", 3), (4, "per-step", "se", 3)],
    ),
    (
        "tab:replication uncapped-endpoint divergence count",
        r"Scale-adaptive OGD \(\$M\\!\\to\\!\\infty\$\)\s*&\s*---\s*&\s*\$(\d+)/10\$",
        "windows_replication_summary.csv", {"method": "Scale-adaptive OGD"},
        [(1, "per-row", "n_diverged", 0)],
    ),
    (
        "sec:experiments prose: uncapped endpoint diverges N/10 per-row",
        r"diverges on \$(\d+)/10\$ \(per-row\)",
        "windows_replication_summary.csv", {"method": "Scale-adaptive OGD"},
        [(1, "per-row", "n_diverged", 0)],
    ),
    (
        "sec:experiments prose: plain OGD diverges N/10 per-step",
        r"plain OGD's frozen rate diverges on \$(\d+)/10\$ \(per-step\)",
        "windows_replication_summary.csv", {"method": "OGD"},
        [(1, "per-step", "n_diverged", 0)],
    ),
    # tab:replication's two SN-OMD rows, adopted at matched tuning budget (C12, C12B).
    # These pin the MEANS; the divergence counts above pin the stability partition. Both
    # rows are tuned over (lr, M) -- the defect these replaced was a pinned cap.
    (
        "tab:replication SN-OMD (M tuned), both protocols",
        r"\\textbf\{SN-OMD \(\$M\$ tuned, ours\)\}\s*&\s*\$([\d.]+)\\pm(\.\d+)\$"
        r"\s*&\s*\$0/10\$\s*&\s*\$([\d.]+)\\pm(\.\d+)\$",
        "c12/c12_matched_summary.csv", {"method": "SN-OMD (M tuned)"},
        [(1, "per-row", "mean", 2), (2, "per-row", "std", 2),
         (3, "per-step", "mean", 2), (4, "per-step", "std", 2)],
    ),
    (
        "tab:replication SN-OMD + block-median tracker, both protocols",
        r"\+ block-median tracker\}\s*&\s*\$([\d.]+)\\pm(\.\d+)\$"
        r"\s*&\s*\$0/10\$\s*&\s*\$\\mathbf\{([\d.]+)\}\\pm(\.\d+)\$",
        "c12b/c12b_summary.csv", {"arm": "matched"},
        [(1, "per-row", "mean", 2), (2, "per-row", "std", 2),
         (3, "per-step", "mean", 2), (4, "per-step", "std", 2)],
    ),
    # The prose SE comparison in app:tracker. Audit finding 3 was exactly this sentence
    # quoting a superseded CSV, and it recurred once more as a last-digit disagreement with
    # the table it cites. Both halves are now pinned to the CSV the table itself is built
    # from, so the next reword has to keep them true.
    (
        "app:tracker prose: SN-OMD's per-row error bar",
        r"column---\$\\pm(\.\d+)\$, about twice normalized-GD's",
        "baselines_jane.csv", {"method": "SN-OMD M=5 (anchor)"},
        [(1, "per-row", "se", 3)],
    ),
    (
        "app:tracker prose: the normalized-GD bar it is compared against",
        r"about twice normalized-GD's \$\\pm(\.\d+)\$",
        "baselines_jane.csv", {"method": "normalized-GD (anchor)"},
        [(1, "per-row", "se", 3)],
    ),
    # The paired contrast behind app:tracker. These replace a guard that pointed at
    # tracker_bootstrap.csv, whose rows were computed with SN-OMD's cap pinned at M=5 --
    # superseded once tab:replication adopted the matched-budget rows. The guard did its
    # job: rewriting the sentence made it fail rather than letting the stale number sit.
    (
        "app:tracker per-row block-vs-EMA gap, matched budget",
        r"the EMA default by \$\+([\d.]+)\$\s*\n?\(\$\[\+([\d.]+),\+([\d.]+)\]\$",
        "c13_matched_bootstrap.csv",
        {"comparison": "block - EMA (SN-OMD, M tuned)", "window_set": "all 10 windows"},
        [(1, "per-row", "mean_diff", 3), (2, "per-row", "t95_lo", 3),
         (3, "per-row", "t95_hi", 3)],
    ),
    (
        "app:tracker per-row Cutkosky-Mehta tie, matched budget",
        r"baseline \(\$-([\d.]+)\$, CI \$\[-([\d.]+),\+([\d.]+)\]\$",
        "c13_matched_bootstrap.csv",
        {"comparison": "block - Cutkosky-Mehta", "window_set": "all 10 windows"},
        [(1, "per-row", "mean_diff", 3, -1), (2, "per-row", "t95_lo", 3, -1),
         (3, "per-row", "t95_hi", 3)],
    ),
    (
        "app:tracker Bonferroni: per-step block-vs-EMA, corrected interval",
        r"the per-step gaps over the EMA \(\$\+([\d.]+)\$, \$\[\+([\d.]+),\+([\d.]+)\]\$\)",
        "c13_matched_bootstrap.csv",
        {"comparison": "block - EMA (SN-OMD, M tuned)", "window_set": "all 10 windows"},
        [(1, "per-step", "mean_diff", 3), (2, "per-step", "bonf_lo", 3),
         (3, "per-step", "bonf_hi", 3)],
    ),
]


@pytest.mark.parametrize("label,pattern,csv_name,where,checks", PAPER_CLAIMS,
                         ids=[c[0] for c in PAPER_CLAIMS])
def test_paper_number_matches_its_csv(
    label: str, pattern: str, csv_name: str, where: dict, checks: list,
) -> None:
    """A number printed in the paper must equal the CSV cell it is sourced from."""
    assert PAPER_TEX.exists(), f"paper source missing: {PAPER_TEX}"
    tex = PAPER_TEX.read_text(encoding="utf-8")

    found = re.findall(pattern, tex)
    assert len(found) == 1, (
        f"{label}: expected the claim to appear exactly once in {PAPER_TEX.name}, "
        f"found {len(found)}. The paper was reworded -- update the pattern in "
        f"PAPER_CLAIMS so this guard keeps checking the real sentence."
    )
    groups = found[0] if isinstance(found[0], tuple) else (found[0],)

    df = pl.read_csv(PROJECT_ROOT / "results" / "research" / csv_name)
    mismatches = []
    for check in checks:
        # An optional 5th element is a sign multiplier, for a value the paper prints as a
        # magnitude after a literal minus (LaTeX "$-0.005$") while the CSV stores -0.005.
        gi, protocol, col, decimals = check[:4]
        sign = check[4] if len(check) > 4 else 1
        sel = df.filter(pl.col("protocol") == protocol)
        for k, v in where.items():
            sel = sel.filter(pl.col(k) == v)
        assert sel.height == 1, (
            f"{label}: selector {where} + protocol={protocol!r} matched {sel.height} "
            f"rows in {csv_name}, expected 1"
        )
        printed = sign * float(groups[gi - 1])
        measured = float(sel[col][0])
        # The printed figure must be A correct rounding of the measurement to the
        # precision it is printed at. Half-way values (0.2205 at 3 d.p.) have two
        # valid renderings, so the tolerance is inclusive of the tie -- this guard
        # is for numbers that drifted, not for a house rounding style.
        if abs(printed - measured) > 0.5 * 10 ** (-decimals) + 1e-9:
            mismatches.append(
                f"    {protocol} {col}: paper says {printed}, {csv_name} says "
                f"{measured:.6g} (rounds to {round(measured, decimals)})"
            )

    assert not mismatches, (
        f"{label}: the paper no longer matches its source CSV. Either the artifact was "
        f"regenerated without updating the manuscript, or the manuscript was edited away "
        f"from its measurement:\n" + "\n".join(mismatches)
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
