"""Robust mean estimators: Catoni, median-of-means, trimmed mean.

Uniform contract: each estimator takes a 1-D array-like and returns a python
float, raising ValueError on empty input.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from .catoni import catoni_mean
from .median_of_means import median_of_means
from .trimmed_mean import trimmed_mean


def _plain_mean(x: np.ndarray) -> float:
    """Non-robust baseline: the plain sample mean."""
    arr = np.asarray(x, dtype=np.float64).ravel()
    if arr.size == 0:
        raise ValueError("mean requires a non-empty input array.")
    return float(np.mean(arr))


ESTIMATORS: dict[str, Callable[..., float]] = {
    "mean": _plain_mean,
    "catoni": catoni_mean,
    "median_of_means": median_of_means,
    "trimmed_mean": trimmed_mean,
}


def get_estimator(name: str) -> Callable[..., float]:
    """Look up an estimator by name.

    Parameters
    ----------
    name : str
        One of the keys of ``ESTIMATORS``.

    Returns
    -------
    Callable[..., float]
        The estimator function.

    Raises
    ------
    ValueError
        If ``name`` is unknown; the message lists the valid options.
    """
    try:
        return ESTIMATORS[name]
    except KeyError:
        options = ", ".join(sorted(ESTIMATORS))
        raise ValueError(
            f"Unknown estimator {name!r}. Valid options: {options}."
        ) from None


__all__ = [
    "catoni_mean",
    "median_of_means",
    "trimmed_mean",
    "get_estimator",
    "ESTIMATORS",
]
