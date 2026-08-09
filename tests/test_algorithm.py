"""Tests for robust mean estimators and online learning algorithms.

All tests are deterministic (fixed seeds) and run against the installed
``dfsl`` package.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np
import pytest

from dfsl import (
    ESTIMATORS,
    AdaptiveClip,
    OnlineGradientDescent,
    RobustOMD,
    ScaleNormalizedOGD,
    SyntheticHeavyTailed,
    catoni_mean,
    get_estimator,
    median_of_means,
    trimmed_mean,
)


def _contaminated_sample() -> np.ndarray:
    """1000 N(0, 1) draws with the first 5% replaced by +1000 outliers."""
    rng = np.random.default_rng(42)
    x = rng.standard_normal(1000)
    x[:50] = 1000.0
    return x


class TestTrimmedMean:
    def test_exact_hand_computed_values(self) -> None:
        # n=5, k=floor(0.2*5)=1: drop 0.0 and 100.0, mean([1, 2, 3]) = 2.
        assert trimmed_mean(
            np.array([0.0, 1.0, 2.0, 3.0, 100.0]), trim_fraction=0.2
        ) == pytest.approx(2.0)
        # n=10, k=1: drop 1 and 10, mean(2..9) = 5.5.
        assert trimmed_mean(np.arange(1.0, 11.0), trim_fraction=0.1) == pytest.approx(5.5)
        # k=0: plain mean.
        assert trimmed_mean(
            np.array([5.0, 1.0, 3.0]), trim_fraction=0.0
        ) == pytest.approx(3.0)

    def test_order_invariance(self) -> None:
        x = np.array([100.0, 3.0, 0.0, 2.0, 1.0])
        assert trimmed_mean(x, trim_fraction=0.2) == pytest.approx(2.0)

    def test_empty_input_raises(self) -> None:
        with pytest.raises(ValueError):
            trimmed_mean(np.array([]))

    @pytest.mark.parametrize("trim_fraction", [0.5, 0.6, -0.1])
    def test_invalid_trim_fraction_raises(self, trim_fraction: float) -> None:
        with pytest.raises(ValueError):
            trimmed_mean(np.array([1.0, 2.0, 3.0]), trim_fraction=trim_fraction)


class TestRobustLocation:
    def test_outlier_resistance(self) -> None:
        x = _contaminated_sample()
        # The plain mean is dragged far away from the true location 0 ...
        assert float(np.mean(x)) > 10.0
        # ... while the robust estimators stay close to 0.
        assert abs(catoni_mean(x, alpha=10.0)) < 0.5
        assert abs(median_of_means(x, n_blocks=200)) < 0.5
        assert abs(trimmed_mean(x, trim_fraction=0.1)) < 0.5

    def test_catoni_constant_array(self) -> None:
        assert catoni_mean(np.full(17, 3.25)) == pytest.approx(3.25)

    def test_median_of_means_default_rng_is_deterministic(self) -> None:
        x = _contaminated_sample()
        assert median_of_means(x, n_blocks=200) == median_of_means(x, n_blocks=200)

    @pytest.mark.parametrize("estimator", [catoni_mean, median_of_means])
    def test_empty_input_raises(self, estimator: Callable[..., float]) -> None:
        with pytest.raises(ValueError):
            estimator(np.array([]))


class TestEstimatorRegistry:
    def test_registry_contents(self) -> None:
        assert set(ESTIMATORS) == {"mean", "catoni", "median_of_means", "trimmed_mean"}

    def test_get_estimator_returns_expected_callables(self) -> None:
        assert get_estimator("catoni") is catoni_mean
        assert get_estimator("median_of_means") is median_of_means
        assert get_estimator("trimmed_mean") is trimmed_mean
        mean_fn = get_estimator("mean")
        value = mean_fn(np.array([1.0, 2.0, 3.0]))
        assert isinstance(value, float)
        assert value == pytest.approx(2.0)

    def test_unknown_name_lists_options(self) -> None:
        with pytest.raises(ValueError) as excinfo:
            get_estimator("definitely_not_an_estimator")
        message = str(excinfo.value)
        assert "catoni" in message
        assert "trimmed_mean" in message


class TestGradientClipping:
    def test_adaptive_clip_gradient_matches_rolling_quantile(self) -> None:
        learner = AdaptiveClip(dim=1, window=256, clip_quantile=0.9)
        norms = [float(k) for k in range(1, 11)]
        for k in norms:
            learner._clip_gradient(np.array([k]))
        # The UNCLIPPED norm 100 must be appended BEFORE tau is computed, so
        # tau = quantile([1..10, 100], 0.9) = 10.0 exactly.
        clipped = learner._clip_gradient(np.array([100.0]))
        expected_tau = float(np.quantile(np.array(norms + [100.0]), 0.9))
        assert expected_tau == pytest.approx(10.0)
        assert float(np.linalg.norm(clipped)) == pytest.approx(expected_tau)
        assert clipped[0] > 0.0
        # A gradient below the threshold passes through unchanged.
        small = learner._clip_gradient(np.array([0.5]))
        np.testing.assert_array_equal(small, np.array([0.5]))

    def test_adaptive_clip_warm_up_needs_ten_norms(self) -> None:
        learner = AdaptiveClip(dim=1, window=256, clip_quantile=0.9)
        for _ in range(8):
            learner._clip_gradient(np.array([1.0]))
        # 9th norm: history holds only 9 entries, so no clipping yet.
        ninth = learner._clip_gradient(np.array([100.0]))
        np.testing.assert_array_equal(ninth, np.array([100.0]))
        # 10th norm: clipping activates and the current norm is in the window:
        # tau = quantile([1]*8 + [100, 200], 0.9) = 110.0.
        tenth = learner._clip_gradient(np.array([200.0]))
        expected_tau = float(np.quantile(np.array([1.0] * 8 + [100.0, 200.0]), 0.9))
        assert expected_tau == pytest.approx(110.0)
        assert float(np.linalg.norm(tenth)) == pytest.approx(expected_tau)

    def test_robust_omd_clip_gradient_uses_estimator_threshold(self) -> None:
        learner = RobustOMD(
            dim=1,
            estimator=lambda a: float(np.mean(a)),
            clip_multiplier=3.0,
            window=256,
        )
        norms = [float(k) for k in range(1, 11)]
        for k in norms:
            # Warm-up (< 10 norms) and norms below tau pass through unchanged.
            out = learner._clip_gradient(np.array([k]))
            np.testing.assert_array_equal(out, np.array([k]))
        # tau = 3 * mean([1..10, 100]) = 3 * 155/11; the unclipped norm 100 is
        # appended before the estimator sees the history.
        clipped = learner._clip_gradient(np.array([100.0]))
        expected_tau = 3.0 * float(np.mean(norms + [100.0]))
        assert expected_tau == pytest.approx(465.0 / 11.0)
        assert float(np.linalg.norm(clipped)) == pytest.approx(expected_tau)
        assert clipped[0] > 0.0
        # The history must store the UNCLIPPED norm 100, not the clipped value:
        # tau = 3 * mean([1..10, 100, 100]) = 63.75.
        clipped_again = learner._clip_gradient(np.array([100.0]))
        expected_tau_again = 3.0 * float(np.mean(norms + [100.0, 100.0]))
        assert expected_tau_again == pytest.approx(63.75)
        assert float(np.linalg.norm(clipped_again)) == pytest.approx(expected_tau_again)


class TestScaleNormalizedOGD:
    def test_effective_gradient_is_capped(self) -> None:
        # The normalized gradient handed to the update step never exceeds the cap.
        learner = ScaleNormalizedOGD(dim=4, cap=10.0)
        rng = np.random.default_rng(0)
        for _ in range(50):
            g = rng.standard_normal(4) * rng.uniform(0.1, 1000.0)
            ghat = learner._clip_gradient(g)
            assert float(np.linalg.norm(ghat)) <= 10.0 + 1e-9

    def test_normalized_gradient_is_scale_invariant(self) -> None:
        # Scaling the whole gradient stream by c leaves clip(g/s, M) unchanged,
        # because the tracked scale s also scales by c. This is the core property.
        a = ScaleNormalizedOGD(dim=3, cap=10.0)
        b = ScaleNormalizedOGD(dim=3, cap=10.0)
        rng = np.random.default_rng(1)
        c = 50.0
        for _ in range(40):
            g = rng.standard_normal(3)
            np.testing.assert_allclose(a._clip_gradient(g), b._clip_gradient(c * g), rtol=1e-9)

    def test_never_diverges_on_extreme_magnitudes(self) -> None:
        # Deterministic non-divergence: extreme inputs cannot blow up the iterate,
        # since ||ghat|| <= cap and the step is cap*lr/sqrt(t).
        learner = ScaleNormalizedOGD(dim=3, learning_rate=1.0, cap=10.0)
        x = np.full(3, 1e150)
        for _ in range(20):
            loss = learner.update(x, 1.0, 1.0)
            assert isinstance(loss, float)
            assert loss >= 0.0
        assert np.isfinite(learner.weights).all()
        # Every step moves the iterate by at most cap*lr/sqrt(t); after 20 steps
        # ||w|| <= cap*lr*sum_{t<=20} 1/sqrt(t) < cap*lr*2*sqrt(20). No divergence.
        assert float(np.linalg.norm(learner.weights)) < 10.0 * 1.0 * 2.0 * np.sqrt(20)

    def test_stays_bounded_under_heavy_contamination(self) -> None:
        # The point of SN-OGD is stability under heavy tails + contamination: the
        # iterate stays bounded regardless of learning rate (Theorem 1), even where
        # plain OGD would diverge. (Accuracy is a separate, lr-tuning question.)
        dataset = SyntheticHeavyTailed(
            n_steps=4000, dim=5, noise="student_t", df=2.1,
            contamination=0.1, contamination_scale=100.0, seed=3,
        )
        learner = ScaleNormalizedOGD(dim=5, learning_rate=1.0)
        result = learner.run(dataset)
        assert np.isfinite(learner.weights).all()
        assert np.all(np.isfinite(result.losses))
        # Bounded by the summed capped steps cap*lr*sum 1/sqrt(t) <= cap*lr*2*sqrt(T).
        assert float(np.linalg.norm(learner.weights)) < 10.0 * 1.0 * 2.0 * np.sqrt(4000)

    def test_learns_on_easy_stream(self) -> None:
        dataset = SyntheticHeavyTailed(
            n_steps=8000, dim=5, noise="gaussian", noise_scale=0.1, seed=1
        )
        learner = ScaleNormalizedOGD(dim=5, learning_rate=1.0)
        learner.run(dataset)
        # Scale-normalized steps converge more slowly than tuned OGD; require a
        # clear signal recovery rather than a tight tolerance.
        d = float(np.linalg.norm(learner.weights - dataset.true_weights))
        assert d < 0.5 * float(np.linalg.norm(dataset.true_weights))

    def test_two_timescale_tracker_option_stays_bounded(self) -> None:
        # The theory-analyzed peak-hold tracker is a drop-in option and must also
        # keep the iterate bounded under heavy tails + contamination.
        dataset = SyntheticHeavyTailed(
            n_steps=4000, dim=5, noise="student_t", df=2.1,
            contamination=0.1, contamination_scale=100.0, seed=3,
        )
        learner = ScaleNormalizedOGD(dim=5, learning_rate=1.0, scale_tracker="two_timescale")
        result = learner.run(dataset)
        assert np.isfinite(learner.weights).all()
        assert np.all(np.isfinite(result.losses))
        assert float(np.linalg.norm(learner.weights)) < 10.0 * 1.0 * 2.0 * np.sqrt(4000)

    def test_invalid_scale_tracker_raises(self) -> None:
        with pytest.raises(ValueError):
            ScaleNormalizedOGD(dim=3, scale_tracker="not_a_tracker")


class TestOnlineLearners:
    def test_ogd_converges_on_easy_stream(self) -> None:
        dataset = SyntheticHeavyTailed(
            n_steps=5000, dim=5, noise="gaussian", noise_scale=0.1, seed=1
        )
        learner = OnlineGradientDescent(dim=5, learning_rate=0.5)
        learner.run(dataset)
        np.testing.assert_allclose(
            learner.weights, dataset.true_weights, rtol=0.0, atol=0.2
        )

    def test_robust_learners_beat_ogd_under_contamination(self) -> None:
        dataset = SyntheticHeavyTailed(
            n_steps=8000,
            dim=5,
            noise="student_t",
            df=2.1,
            contamination=0.05,
            contamination_scale=100.0,
            seed=3,
        )
        learning_rate = 0.1

        def final_distance(learner: OnlineGradientDescent) -> float:
            learner.run(dataset)
            return float(np.linalg.norm(learner.weights - dataset.true_weights))

        d_ogd = final_distance(OnlineGradientDescent(dim=5, learning_rate=learning_rate))
        d_adaptive = final_distance(AdaptiveClip(dim=5, learning_rate=learning_rate))
        d_robust = final_distance(
            RobustOMD(dim=5, learning_rate=learning_rate, estimator="catoni")
        )
        assert d_adaptive < d_ogd
        assert d_robust < d_ogd

    def test_update_returns_finite_nonnegative_float(self) -> None:
        dataset = SyntheticHeavyTailed(n_steps=20, dim=4, noise="student_t", df=2.5, seed=9)
        learner = OnlineGradientDescent(dim=4, learning_rate=0.1)
        weight = 2.5
        for x, y, _ in dataset:
            pred = learner.predict(x)
            loss = learner.update(x, y, weight)
            assert isinstance(loss, float)
            assert math.isfinite(loss)
            assert loss >= 0.0
            # Prequential contract: weighted squared loss of the prediction made
            # with the parameters held BEFORE the update step.
            assert loss == pytest.approx(weight * (pred - y) ** 2)

    def test_update_survives_extreme_magnitudes(self) -> None:
        # Raw Jane Street features span several orders of magnitude; a diverging
        # iterate must saturate the loss to inf and skip the step, never raise
        # OverflowError or poison the weights with inf/nan.
        for learner in (
            OnlineGradientDescent(dim=3, learning_rate=1.0),
            RobustOMD(dim=3, learning_rate=1.0, estimator="trimmed_mean"),
        ):
            x = np.full(3, 1e160)
            for _ in range(5):
                loss = learner.update(x, 1.0, 1.0)
                assert isinstance(loss, float)
                assert loss >= 0.0
            assert np.isfinite(learner.weights).all()

    def test_seeded_runs_are_deterministic(self) -> None:
        first = self._seeded_run()
        second = self._seeded_run()
        assert first.losses.shape == (600,)
        assert np.array_equal(first.losses, second.losses)
        assert np.array_equal(first.predictions, second.predictions)

    @staticmethod
    def _seeded_run():
        dataset = SyntheticHeavyTailed(
            n_steps=600, dim=4, noise="student_t", df=2.5, seed=7
        )
        learner = RobustOMD(
            dim=4, learning_rate=0.1, estimator="catoni", window=64, seed=0
        )
        return learner.run(dataset)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
