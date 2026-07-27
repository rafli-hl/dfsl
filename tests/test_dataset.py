"""Tests for sequential datasets: synthetic heavy-tailed streams and Jane Street.

The Jane Street tests are skipped (via a module-scope skipif marker) when the
raw competition data is not present under ``data/raw/jane``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from dfsl import JaneStreetDataset, SyntheticHeavyTailed

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JANE_TRAIN_DIR = PROJECT_ROOT / "data" / "raw" / "jane" / "train.parquet"
DATA_AVAILABLE = JANE_TRAIN_DIR.exists()

requires_jane_data = pytest.mark.skipif(
    not DATA_AVAILABLE,
    reason=(
        "Jane Street data not found under data/raw/jane; "
        "run 'python scripts/download_data.py' first."
    ),
)


class TestSyntheticHeavyTailed:
    def test_shapes_and_sizes(self) -> None:
        dataset = SyntheticHeavyTailed(n_steps=300, dim=7, seed=0)
        assert len(dataset) == 300
        assert dataset.n_steps == 300
        assert dataset.dim == 7
        assert dataset.X.shape == (300, 7)
        assert dataset.X.dtype == np.float64
        assert dataset.y.shape == (300,)
        assert dataset.weights.shape == (300,)
        assert np.all(dataset.weights == 1.0)
        assert dataset.true_weights.shape == (7,)
        assert float(np.linalg.norm(dataset.true_weights)) == pytest.approx(1.0)

    def test_iteration_matches_arrays(self) -> None:
        dataset = SyntheticHeavyTailed(n_steps=25, dim=3, seed=2)
        items = list(dataset)
        assert len(items) == 25
        for i, (x, y, w) in enumerate(items):
            assert isinstance(x, np.ndarray)
            assert x.shape == (3,)
            assert isinstance(y, float)
            assert isinstance(w, float)
            assert np.array_equal(x, dataset.X[i])
            assert y == dataset.y[i]
            assert w == dataset.weights[i]

    def test_seed_reproducibility(self) -> None:
        first = SyntheticHeavyTailed(n_steps=200, dim=4, seed=11)
        same = SyntheticHeavyTailed(n_steps=200, dim=4, seed=11)
        other = SyntheticHeavyTailed(n_steps=200, dim=4, seed=12)
        assert np.array_equal(first.X, same.X)
        assert np.array_equal(first.y, same.y)
        assert not np.array_equal(first.y, other.y)

    def test_contamination_mask_count(self) -> None:
        dataset = SyntheticHeavyTailed(n_steps=1000, dim=3, contamination=0.05, seed=5)
        mask = dataset.contamination_mask
        assert mask.dtype == np.bool_
        assert mask.shape == (1000,)
        assert int(mask.sum()) == int(round(0.05 * 1000))

    def test_unknown_noise_raises(self) -> None:
        with pytest.raises(ValueError):
            SyntheticHeavyTailed(n_steps=10, dim=2, noise="uniform", seed=0)


@requires_jane_data
class TestJaneStreetDataset:
    @pytest.fixture(scope="class")
    def dataset(self) -> JaneStreetDataset:
        return JaneStreetDataset(date_range=(0, 2), max_rows=2000)

    def test_feature_dimension(self, dataset: JaneStreetDataset) -> None:
        assert dataset.dim == 79
        assert dataset.X.shape == (len(dataset), 79)

    def test_row_budget(self, dataset: JaneStreetDataset) -> None:
        assert 0 < len(dataset) <= 2000

    def test_features_finite_after_fill(self, dataset: JaneStreetDataset) -> None:
        assert np.isfinite(dataset.X).all()

    def test_targets_within_clip_range(self, dataset: JaneStreetDataset) -> None:
        assert np.all(dataset.y >= -5.0)
        assert np.all(dataset.y <= 5.0)

    def test_weights_positive(self, dataset: JaneStreetDataset) -> None:
        assert np.all(dataset.weights > 0.0)

    def test_meta_has_id_columns(self, dataset: JaneStreetDataset) -> None:
        assert {"date_id", "time_id", "symbol_id"} <= set(dataset.meta.columns)

    def test_rows_sorted_by_date_then_time(self, dataset: JaneStreetDataset) -> None:
        date_id = dataset.meta["date_id"].to_numpy().astype(np.int64)
        time_id = dataset.meta["time_id"].to_numpy().astype(np.int64)
        key = date_id * 1_000_000 + time_id
        assert np.all(np.diff(key) >= 0)

    def test_standardize_zscores_features(self) -> None:
        dataset = JaneStreetDataset(date_range=(0, 1), max_rows=1500, standardize=True)
        means = dataset.X.mean(axis=0)
        stds = dataset.X.std(axis=0)
        assert np.allclose(means, 0.0, atol=1e-8)
        # scalable columns end up with unit spread; degenerate ones stay centered
        assert np.all((stds < 1e-8) | (np.abs(stds - 1.0) < 1e-6))
        assert dataset.feature_means is not None
        assert dataset.feature_stds is not None
        raw = JaneStreetDataset(date_range=(0, 1), max_rows=1500)
        assert raw.feature_means is None
        assert not np.allclose(raw.X.std(axis=0), stds)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
