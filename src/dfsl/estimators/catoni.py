"""Catoni's M-estimator of the mean for heavy-tailed data."""

from __future__ import annotations

import numpy as np


def _psi(t: np.ndarray) -> np.ndarray:
    """Catoni influence function ``psi(t) = sign(t) * log(1 + |t| + t^2 / 2)``."""
    return np.sign(t) * np.log1p(np.abs(t) + 0.5 * t * t)


def catoni_mean(
    x: np.ndarray,
    alpha: float | None = None,
    delta: float = 0.05,
    tol: float = 1e-8,
    max_iter: int = 200,
) -> float:
    """Catoni M-estimator of the mean.

    Solves ``sum_i psi(alpha * (x_i - theta)) = 0`` for ``theta`` by bisection
    on ``[min(x), max(x)]``; the influence sum is strictly decreasing in
    ``theta``, so bisection is valid whenever the bracket straddles zero.

    Parameters
    ----------
    x : np.ndarray
        1-D array of observations.
    alpha : float or None
        Scale parameter. If None it is set to
        ``sqrt(2 * log(1/delta) / (n * var(x, ddof=1)))``; degenerate samples
        (n < 2 or near-zero variance) fall back to the plain mean.
    delta : float
        Confidence level used in the default ``alpha``.
    tol : float
        Bisection interval-width tolerance.
    max_iter : int
        Maximum number of bisection iterations.

    Returns
    -------
    float
        The Catoni mean estimate.

    Raises
    ------
    ValueError
        If ``x`` is empty.
    """
    arr = np.asarray(x, dtype=np.float64).ravel()
    n = arr.size
    if n == 0:
        raise ValueError("catoni_mean requires a non-empty input array.")

    lo = float(np.min(arr))
    hi = float(np.max(arr))
    if hi == lo:
        # Constant array: its mean is exactly the constant.
        return lo

    if alpha is None:
        if n < 2:
            return float(np.mean(arr))
        s2 = float(np.var(arr, ddof=1))
        if s2 <= 1e-24:
            return float(np.mean(arr))
        alpha = float(np.sqrt(2.0 * np.log(1.0 / delta) / (n * s2)))

    def influence_sum(theta: float) -> float:
        return float(np.sum(_psi(alpha * (arr - theta))))

    f_lo = influence_sum(lo)
    f_hi = influence_sum(hi)
    # The sum is decreasing in theta: expect f_lo >= 0 >= f_hi.
    if f_lo < 0.0 or f_hi > 0.0:
        return float(np.mean(arr))

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = influence_sum(mid)
        if f_mid > 0.0:
            lo = mid
        else:
            hi = mid
        if hi - lo <= tol:
            break
    return float(0.5 * (lo + hi))
