"""The anonymized supplement's exclusion list must fail CLOSED, not open.

Why this test exists
--------------------
``make_anon_release.EXCLUDE_GLOBS`` is applied by plain substring containment::

    if any(g in f for g in EXCLUDE_GLOBS): continue

which makes the entries quietly sensitive to how a path is spelled. The prior-venue
exclusion was written as ``"paper/icml2026."`` -- with a trailing dot, because at the time
the ICML files were flat (``paper/icml2026.tex``, ``paper/icml2026.pdf``). When those files
were later moved into ``paper/icml2026/``, that entry **stopped matching** and the exclusion
failed open: a supplement built from the moved tree would have shipped the superseded
prior-venue source and PDF to a double-blind reviewer.

The export's own identity self-check would not have caught it. That check looks for author
identity tokens, and prior-venue material is identity-clean -- the leak is *submission
history*, a different kind. So the export would have reported "self-check clean" while
shipping exactly what the exclusion exists to withhold.

This test pins the pair that actually has to agree: the intent of each exclusion and the
paths it is supposed to cover, under **both** layouts. It imports the constants only and
touches neither git nor the filesystem, so it runs in a data-less checkout.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import make_anon_release as anon  # noqa: E402


def excluded(path: str) -> bool:
    """Exactly the predicate make_anon_release.tracked_files applies."""
    return path in anon.EXCLUDE_EXACT or any(g in path for g in anon.EXCLUDE_GLOBS)


# Paths that must NEVER reach the supplement. Both ICML layouts appear deliberately:
# the flat one is what the exclusion was written against, the nested one is what broke it.
MUST_EXCLUDE = [
    ("prior venue, flat layout", "paper/icml2026.tex"),
    ("prior venue, flat layout", "paper/icml2026.pdf"),
    ("prior venue, flat layout", "paper/icml2026.sty"),
    ("prior venue, nested layout", "paper/icml2026/icml2026.tex"),
    ("prior venue, nested layout", "paper/icml2026/icml2026.pdf"),
    ("prior venue, nested build output", "paper/icml2026/icml2026.log"),
    ("prior venue, nested build output", "paper/icml2026/build.log"),
    ("internal audit notes", "audit/AUDIT_REPORT.md"),
    ("internal audit notes", "audit/ICLR2027_SUMMARY.md"),
    ("stray latexmk output", "out/icml2026.synctex(busy)"),
    ("committed bytecode", "src/dfsl/__pycache__/preprocessing.cpython-312.pyc"),
    ("the builder itself", "scripts/make_anon_release.py"),
]

# Paths that must SURVIVE. Without these, an over-broad exclusion could pass the test above
# by gutting the supplement -- the failure mode in the opposite direction.
MUST_KEEP = [
    ("the submitted paper", "paper/iclr2027/iclr2027.tex"),
    ("the submitted paper's bibliography", "paper/iclr2027/refs.bib"),
    ("figures", "paper/figures/fig1_problem.png"),
    ("library source", "src/dfsl/preprocessing.py"),
    ("research scripts", "scripts/research_windows_replication.py"),
    ("results", "results/research/windows_replication.csv"),
    ("tests", "tests/test_artifacts_fresh.py"),
]


@pytest.mark.parametrize("reason,path", MUST_EXCLUDE, ids=[p for _, p in MUST_EXCLUDE])
def test_must_be_excluded(reason: str, path: str) -> None:
    assert excluded(path), (
        f"{path!r} ({reason}) is NOT excluded from the anonymized supplement.\n"
        f"EXCLUDE_GLOBS matches by substring containment, so an entry written for one path "
        f"spelling stops matching when files move. Update EXCLUDE_GLOBS in "
        f"scripts/make_anon_release.py so it covers this path."
    )


@pytest.mark.parametrize("reason,path", MUST_KEEP, ids=[p for _, p in MUST_KEEP])
def test_must_be_kept(reason: str, path: str) -> None:
    assert not excluded(path), (
        f"{path!r} ({reason}) is being excluded from the anonymized supplement. "
        f"An exclusion entry is over-broad and is removing material the supplement needs."
    )


def test_prior_venue_glob_has_no_trailing_dot() -> None:
    """Pin the specific regression: a trailing dot silently un-covers the nested layout."""
    entries = [g for g in anon.EXCLUDE_GLOBS if "icml2026" in g]
    assert entries, "the prior-venue exclusion has disappeared from EXCLUDE_GLOBS"
    for g in entries:
        assert not g.endswith("."), (
            f"exclusion entry {g!r} ends with '.', which matches only the flat layout "
            f"(paper/icml2026.tex) and NOT paper/icml2026/icml2026.tex. Drop the trailing "
            f"dot so the entry survives the files being moved into a directory."
        )
