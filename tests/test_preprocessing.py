"""Tests for streaming preprocessing utilities (``dfsl.preprocessing``)."""

from __future__ import annotations

import numpy as np
import pytest

from dfsl.preprocessing import OnlineStandardizer


class TestOnlineStandardizer:
    def test_welford_matches_batch_moments(self) -> None:
        rng = np.random.default_rng(0)
        X = rng.standard_normal((50, 3))
        s = OnlineStandardizer(dim=3)
        for row in X:
            s.partial_fit(row)
        assert s.count == 50
        np.testing.assert_allclose(s.mean, X.mean(axis=0), atol=1e-12)
        # Population variance (M2 / count), not the ddof=1 sample variance.
        np.testing.assert_allclose(s.variance, X.var(axis=0), atol=1e-12)

    def test_transform_recovers_standardization(self) -> None:
        rng = np.random.default_rng(1)
        X = rng.standard_normal((50, 3))
        eps = 1e-8
        s = OnlineStandardizer(dim=3, eps=eps)
        for row in X:
            s.partial_fit(row)
        x = np.array([0.5, -1.0, 2.0])
        expected = (x - X.mean(axis=0)) / np.sqrt(X.var(axis=0) + eps)
        np.testing.assert_allclose(s.transform(x), expected, atol=1e-12)

    def test_before_two_observations_only_centers(self) -> None:
        s = OnlineStandardizer(dim=2)
        x0 = np.array([3.0, -4.0])
        # count == 0: mean is zero, so transform is the identity.
        np.testing.assert_allclose(s.transform(x0), x0)
        s.partial_fit(x0)
        # count == 1: transform returns x - mean with mean == x0.
        np.testing.assert_allclose(
            s.transform(np.array([5.0, 0.0])), np.array([2.0, 4.0])
        )

    def test_variance_zeros_before_any_data(self) -> None:
        s = OnlineStandardizer(dim=4)
        np.testing.assert_array_equal(s.variance, np.zeros(4))

    def test_fit_transform_step_equals_partial_fit_then_transform(self) -> None:
        rng = np.random.default_rng(2)
        X = rng.standard_normal((20, 2))
        a = OnlineStandardizer(dim=2)
        b = OnlineStandardizer(dim=2)
        for row in X:
            out_a = a.fit_transform_step(row)
            out_b = b.partial_fit(row).transform(row)
            np.testing.assert_allclose(out_a, out_b)
        assert a.count == b.count == 20


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
