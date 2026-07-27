"""Symmetrically trimmed mean estimator."""

from __future__ import annotations

import math

import numpy as np


def trimmed_mean(x: np.ndarray, trim_fraction: float = 0.1) -> float:
    """Symmetrically trimmed mean.

    Sorts the sample, drops ``floor(trim_fraction * n)`` observations from each
    end, and returns the mean of the remainder — a simple robust estimator with
    breakdown point ``trim_fraction``.

    Parameters
    ----------
    x : np.ndarray
        1-D array of observations.
    trim_fraction : float
        Fraction trimmed from each tail; must satisfy ``0 <= trim_fraction < 0.5``.

    Returns
    -------
    float
        Mean of the central ``n - 2k`` order statistics.

    Raises
    ------
    ValueError
        If ``x`` is empty or ``trim_fraction`` is outside ``[0, 0.5)``.
    """
    if not 0.0 <= trim_fraction < 0.5:
        raise ValueError(
            f"trim_fraction must satisfy 0 <= trim_fraction < 0.5, got {trim_fraction}."
        )
    arr = np.asarray(x, dtype=np.float64).ravel()
    n = arr.size
    if n == 0:
        raise ValueError("trimmed_mean requires a non-empty input array.")

    k = math.floor(trim_fraction * n)
    trimmed = np.sort(arr)[k : n - k]
    if trimmed.size == 0:
        return float(np.median(arr))
    return float(np.mean(trimmed))
