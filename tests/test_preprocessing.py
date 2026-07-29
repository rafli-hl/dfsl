"""Tests for streaming preprocessing utilities (``dfsl.preprocessing``)."""

from __future__ import annotations

import numpy as np
import pytest

from dfsl.preprocessing import (
    OnlineScaleTracker,
    OnlineStandardizer,
    TwoTimescaleScaleTracker,
)


class TestOnlineScaleTracker:
    def test_initializes_to_first_norm(self) -> None:
        t = OnlineScaleTracker()
        # First step returns (and sets) the first observed norm.
        assert t.step(4.0) == pytest.approx(4.0)
        assert t.scale == pytest.approx(4.0)

    def test_step_is_predictable(self) -> None:
        # The value returned at each step must not depend on the current norm
        # (only on the past), so a huge spike does not affect its own returned scale.
        t = OnlineScaleTracker(decay=0.9, winsor=8.0)
        t.step(1.0)
        returned = t.step(1e6)
        # Returned scale is the pre-update estimate (~1.0), not influenced by 1e6.
        assert returned == pytest.approx(1.0, abs=1e-9)

    def test_winsorization_bounds_spike_influence(self) -> None:
        t = OnlineScaleTracker(decay=0.5, winsor=8.0)
        t.step(1.0)  # scale = 1.0
        t.step(1e9)  # spike capped at winsor*scale = 8.0 before updating the EMA
        # New scale = 0.5*1.0 + 0.5*min(1e9, 8*1.0) = 0.5 + 4.0 = 4.5, not ~5e8.
        assert t.scale == pytest.approx(4.5)

    def test_scale_invariance(self) -> None:
        # Scaling the whole norm stream by c scales every returned scale by c,
        # so the normalized gradient g/s is invariant -- the key SN-OGD property.
        rng = np.random.default_rng(0)
        norms = np.abs(rng.standard_normal(200)) + 0.1
        c = 37.0
        a = OnlineScaleTracker()
        b = OnlineScaleTracker()
        for n in norms:
            sa = a.step(float(n))
            sb = b.step(float(c * n))
            assert sb == pytest.approx(c * sa, rel=1e-9)

    def test_eps_before_data_and_invalid_norm_ignored(self) -> None:
        t = OnlineScaleTracker(eps=1e-6)
        assert t.scale == pytest.approx(1e-6)
        t.step(2.0)
        before = t.scale
        # Non-finite / negative norms are ignored and leave the estimate unchanged.
        assert t.step(np.inf) == pytest.approx(before)
        assert t.scale == pytest.approx(before)

    @pytest.mark.parametrize("decay", [-0.1, 1.0, 1.5])
    def test_invalid_decay_raises(self, decay: float) -> None:
        with pytest.raises(ValueError):
            OnlineScaleTracker(decay=decay)


class TestTwoTimescaleScaleTracker:
    def test_predictable_and_initializes_to_first_norm(self) -> None:
        t = TwoTimescaleScaleTracker(fast_window=8, decay=0.01)
        assert t.step(3.0) == pytest.approx(3.0)
        # A subsequent huge spike does not affect its own returned scale.
        assert t.step(1e6) == pytest.approx(3.0, abs=1e-9)

    def test_peak_hold_decays_slowly(self) -> None:
        # After a sustained high level the envelope holds and releases only at
        # rate (1 - decay) per step once the input drops.
        t = TwoTimescaleScaleTracker(fast_window=4, decay=0.05, scale=1.0)
        for _ in range(20):
            t.step(10.0)  # establish scale ~10
        high = t.scale
        assert high == pytest.approx(10.0, rel=0.2)
        # Now feed small norms; the median drops but the envelope releases slowly.
        t.step(0.1)
        after_one = t.scale
        assert after_one >= (1.0 - 0.05) * high - 1e-9  # fell by at most the decay rate

    def test_reacts_up_fast_to_a_rise(self) -> None:
        t = TwoTimescaleScaleTracker(fast_window=4, decay=1e-4)
        for _ in range(10):
            t.step(1.0)
        # A sustained jump to 50 lifts the envelope within about a window.
        for _ in range(6):
            t.step(50.0)
        assert t.scale > 10.0

    def test_scale_invariance(self) -> None:
        rng = np.random.default_rng(3)
        norms = np.abs(rng.standard_normal(150)) + 0.2
        c = 12.0
        a = TwoTimescaleScaleTracker(fast_window=16, decay=1e-3)
        b = TwoTimescaleScaleTracker(fast_window=16, decay=1e-3)
        for n in norms:
            sa = a.step(float(n))
            sb = b.step(float(c * n))
            assert sb == pytest.approx(c * sa, rel=1e-9)

    @pytest.mark.parametrize("kwargs", [{"fast_window": 0}, {"decay": 1.0}, {"scale": 0.0}])
    def test_invalid_params_raise(self, kwargs: dict) -> None:
        with pytest.raises(ValueError):
            TwoTimescaleScaleTracker(**kwargs)


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
