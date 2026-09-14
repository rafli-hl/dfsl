"""Structure C may move what the paper claims; it may not move or drop what the paper shows.

The greenlight for the restructure carried this as a discipline. It is checkable, so it is a
test: steps 2 and 3 carry the same risk as step 1, and the page budget creates steady pressure
to reclaim space from a number rather than from prose -- which is the edit least likely to be
noticed in review.

Skips when the baseline tag is absent (a shallow clone, or a checkout predating the tag), so it
never fails for a reason unrelated to the paper.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from check_restructure_invariant import DEFAULT_BASE, check, ref_exists  # noqa: E402


def test_restructure_moves_claims_not_measurements() -> None:
    if not ref_exists(DEFAULT_BASE):
        pytest.skip(f"baseline ref {DEFAULT_BASE!r} not present in this checkout")
    problems = check(DEFAULT_BASE)
    assert not problems, (
        "Structure C invariant violated against " + DEFAULT_BASE + ":\n"
        + "\n".join(f"  - {p}" for p in problems)
        + "\n\n  A claim reordering should not need to touch a float, and should not drop a "
        "measurement. If a measurement genuinely has to move, do it in its own commit so it is "
        "reviewed as a change to the evidence rather than as part of a reordering."
    )
