"""Robustness experiments: target contamination and breakdown analysis."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import polars as pl

from ..algorithms.base import OnlineLearner
from ..datasets.base import SequentialDataset
from ..utils.seed import get_rng
from .metrics import mae, mse, weighted_r2

__all__ = ["contaminate_targets", "breakdown_experiment"]


def contaminate_targets(
    y: np.ndarray,
    fraction: float = 0.05,
    magnitude: float = 50.0,
    rng: np.random.Generator | int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Contaminate a fraction of targets with symmetric large outliers.

    Adds ``magnitude * s`` with random signs ``s in {-1, +1}`` to a
    ``rng``-chosen fraction of entries, sampled without replacement.

    Parameters
    ----------
    y : np.ndarray
        Clean targets, shape (n,); not modified in place.
    fraction : float
        Fraction of entries to contaminate.
    magnitude : float
        Absolute size of the additive outlier.
    rng : np.random.Generator, int, or None
        Randomness source; ``None`` uses ``np.random.default_rng(0)`` for
        reproducibility.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(contaminated copy of y, boolean contamination mask)``.
    """
    y = np.asarray(y, dtype=np.float64)
    gen = np.random.default_rng(0) if rng is None else get_rng(rng)
    n = y.shape[0]
    k = int(round(fraction * n))
    idx = gen.choice(n, size=k, replace=False)
    y_out = y.copy()
    y_out[idx] += magnitude * gen.choice([-1.0, 1.0], size=k)
    mask = np.zeros(n, dtype=bool)
    mask[idx] = True
    return y_out, mask


def breakdown_experiment(
    learner_factory: Callable[[], OnlineLearner],
    dataset: SequentialDataset,
    fractions: Sequence[float],
    magnitude: float = 50.0,
    seed: int = 0,
) -> pl.DataFrame:
    """Sweep contamination fractions and measure clean-target performance.

    For each fraction, a copy of ``dataset.y`` is contaminated with
    ``np.random.default_rng(seed)`` and a fresh learner from
    ``learner_factory`` is run over ``zip(dataset.X, y_contaminated,
    dataset.weights)``. Predictions are then scored against the ORIGINAL
    clean ``dataset.y``.

    Parameters
    ----------
    learner_factory : Callable[[], OnlineLearner]
        Zero-argument factory producing a fresh learner per fraction.
    dataset : SequentialDataset
        Dataset supplying ``X``, clean ``y``, and ``weights``.
    fractions : Sequence[float]
        Contamination fractions to sweep.
    magnitude : float
        Absolute size of the additive outliers.
    seed : int
        Seed for the contamination generator (fresh per fraction).

    Returns
    -------
    pl.DataFrame
        Columns ``fraction``, ``mse``, ``mae``, ``weighted_r2`` computed
        against the clean targets.
    """
    rows: list[dict[str, float]] = []
    for fraction in fractions:
        rng = np.random.default_rng(seed)
        y_contaminated, _ = contaminate_targets(
            dataset.y, fraction=float(fraction), magnitude=magnitude, rng=rng
        )
        learner = learner_factory()
        stream = (
            (x, float(y_t), float(w_t))
            for x, y_t, w_t in zip(dataset.X, y_contaminated, dataset.weights)
        )
        result = learner.run(stream)
        rows.append(
            {
                "fraction": float(fraction),
                "mse": mse(dataset.y, result.predictions, dataset.weights),
                "mae": mae(dataset.y, result.predictions, dataset.weights),
                "weighted_r2": weighted_r2(dataset.y, result.predictions, dataset.weights),
            }
        )
    return pl.DataFrame(rows)
