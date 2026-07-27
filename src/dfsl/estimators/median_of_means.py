"""Median-of-means estimator of the mean."""

from __future__ import annotations

import numpy as np

from ..utils.seed import get_rng


def median_of_means(
    x: np.ndarray,
    n_blocks: int | None = None,
    delta: float = 0.05,
    rng: np.random.Generator | int | None = None,
) -> float:
    """Median-of-means estimate of the mean.

    The sample is randomly permuted, split into ``n_blocks`` nearly-equal
    blocks, and the median of the block means is returned. With
    ``n_blocks ~ 8 * log(1/delta)`` this gives a sub-Gaussian deviation bound
    at confidence ``1 - delta`` under only a finite-variance assumption.

    Parameters
    ----------
    x : np.ndarray
        1-D array of observations.
    n_blocks : int or None
        Number of blocks; defaults to ``max(1, min(n, ceil(8 * log(1/delta))))``.
    delta : float
        Confidence level used to choose the default number of blocks.
    rng : np.random.Generator, int or None
        Randomness source; ``None`` uses the deterministic
        ``np.random.default_rng(0)`` for reproducibility.

    Returns
    -------
    float
        The median of the block means.

    Raises
    ------
    ValueError
        If ``x`` is empty.
    """
    arr = np.asarray(x, dtype=np.float64).ravel()
    n = arr.size
    if n == 0:
        raise ValueError("median_of_means requires a non-empty input array.")

    if n_blocks is None:
        n_blocks = max(1, min(n, int(np.ceil(8.0 * np.log(1.0 / delta)))))

    generator = np.random.default_rng(0) if rng is None else get_rng(rng)
    perm = generator.permutation(n)
    blocks = np.array_split(arr[perm], n_blocks)
    block_means = np.array([np.mean(block) for block in blocks], dtype=np.float64)
    return float(np.median(block_means))
