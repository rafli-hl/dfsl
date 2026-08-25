"""The data-free Jane path must keep working, or the supplement's claim about it is stale.

``scripts/research_jane_mini.py`` is what a reviewer without the Kaggle data runs, so it is
the one part of the Jane code path that CI can actually cover: the loader, the causal
standardization, the ``(date_id, time_id)`` group boundaries the per-step protocol batches
over, the tracker's predictable scale, the cap, and the weighted-R^2 evaluation.

The test builds a deliberately tiny slice, so it checks *mechanics* rather than magnitudes.
The tail-lightening assertion the script itself makes needs the default size to be stable
and is left to the script; what is pinned here is that the pieces fit together and that the
stability dichotomy -- bounded scale-free rows stay bounded where a scale-dependent rate
does not -- is reproduced by this code path at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

jm = pytest.importorskip("research_jane_mini")

from dfsl import JaneStreetDataset  # noqa: E402


@pytest.fixture(scope="module")
def mini(tmp_path_factory):
    base = tmp_path_factory.mktemp("jane_mini")
    jm.build(n_days=4, n_times=25, n_symbols=5, base=base)
    return base


def test_slice_loads_with_the_real_loader(mini):
    ds = JaneStreetDataset(data_dir=mini, standardize=True)
    assert ds.X.shape == (4 * 25 * 5, 79)
    assert ds.y.shape == (500,)
    assert np.isfinite(ds.X).all() and np.isfinite(ds.y).all()
    # causal standardization clips to +-8 and never uses a future row
    assert np.abs(ds.X).max() <= 8.0 + 1e-9


def test_group_structure_is_real(mini):
    """Per-step must have groups to batch over, not one row per group."""
    ds = JaneStreetDataset(data_dir=mini, standardize=True)
    starts = jm.group_boundaries(ds.meta)
    assert len(starts) == 4 * 25, "one group per (date_id, time_id)"
    assert len(starts) < len(ds.y), "per-step would collapse onto per-row"


def test_stability_dichotomy_reproduces(mini):
    """A scale-free cap keeps the iterate bounded at a rate that breaks plain OGD."""
    ds = JaneStreetDataset(data_dir=mini, standardize=True)
    X, y, wts = ds.X, ds.y, ds.weights
    lr = 5.0
    _, ogd_norm, _ = jm._perrow(X, y, wts, "ogd", 0.0, lr)
    _, sn_norm, _ = jm._perrow(X, y, wts, "snomd", 5.0, lr)
    _, ngd_norm, _ = jm._perrow(X, y, wts, "normgd", 0.0, lr)
    assert not (np.isfinite(ogd_norm) and ogd_norm <= jm.DIVERGED), (
        f"plain OGD was expected to diverge at lr={lr}, got ||w||={ogd_norm:.3g}"
    )
    for label, n in (("SN-OMD", sn_norm), ("normalized-GD", ngd_norm)):
        assert np.isfinite(n) and n <= jm.DIVERGED, (
            f"{label} is in the bounded scale-free family and must not diverge at "
            f"lr={lr}; got ||w||={n:.3g}"
        )


def test_hill_estimator_orders_known_tails():
    """Guard the diagnostic itself: a heavier tail must read a smaller index."""
    rng = np.random.default_rng(0)
    heavy = np.abs(rng.standard_t(1.5, 200_000))
    light = np.abs(rng.standard_t(6.0, 200_000))
    k = 10_000
    assert jm.hill(heavy, k) < jm.hill(light, k)


def test_canonical_slice_pin_is_recorded():
    """The reviewer-facing hash must be a real pin, not a placeholder."""
    assert len(jm.CANON_SHA) == 64, "CANON_SHA must be a recorded sha256"
    assert all(c in "0123456789abcdef" for c in jm.CANON_SHA)
