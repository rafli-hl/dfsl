"""Regret analysis against the best fixed linear predictor in hindsight."""

from __future__ import annotations

import numpy as np

__all__ = [
    "best_fixed_linear",
    "linear_losses",
    "regret_curve",
    "empirical_regret_slope",
]


def best_fixed_linear(
    X: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray | None = None,
    reg: float = 1e-6,
) -> np.ndarray:
    """Best fixed linear comparator via weighted ridge regression.

    Solves ``(X^T W X + reg * I) w = X^T W y`` with ``np.linalg.solve``.

    Parameters
    ----------
    X : np.ndarray
        Design matrix, shape (n, d).
    y : np.ndarray
        Targets, shape (n,).
    weights : np.ndarray or None
        Sample weights on the diagonal of W; defaults to all ones.
    reg : float
        Ridge regularization strength.

    Returns
    -------
    np.ndarray
        Comparator weight vector, shape (d,), float64.
    """
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    w = np.ones(y.shape[0], dtype=np.float64) if weights is None else np.asarray(weights, dtype=np.float64)
    Xw = X * w[:, None]
    gram = X.T @ Xw + reg * np.eye(X.shape[1])
    rhs = Xw.T @ y
    return np.linalg.solve(gram, rhs)


def linear_losses(
    X: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    weights: np.ndarray | None = None,
) -> np.ndarray:
    """Per-step weighted squared losses of a fixed linear predictor.

    Parameters
    ----------
    X : np.ndarray
        Design matrix, shape (n, d).
    y : np.ndarray
        Targets, shape (n,).
    w : np.ndarray
        Fixed linear predictor weights, shape (d,).
    weights : np.ndarray or None
        Sample weights; defaults to all ones.

    Returns
    -------
    np.ndarray
        ``weights_i * (x_i @ w - y_i)^2``, shape (n,), float64.
    """
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    w = np.asarray(w, dtype=np.float64)
    wt = np.ones(y.shape[0], dtype=np.float64) if weights is None else np.asarray(weights, dtype=np.float64)
    residuals = X @ w - y
    return wt * residuals**2


def regret_curve(losses: np.ndarray, comparator_losses: np.ndarray) -> np.ndarray:
    """Cumulative regret of a learner against a comparator loss sequence.

    Parameters
    ----------
    losses : np.ndarray
        Per-step learner losses, shape (n,).
    comparator_losses : np.ndarray
        Per-step comparator losses, shape (n,).

    Returns
    -------
    np.ndarray
        ``np.cumsum(losses - comparator_losses)``, shape (n,).
    """
    losses = np.asarray(losses, dtype=np.float64)
    comparator_losses = np.asarray(comparator_losses, dtype=np.float64)
    return np.cumsum(losses - comparator_losses)


def empirical_regret_slope(regret: np.ndarray) -> float:
    """Empirical growth exponent of a cumulative regret curve.

    Fits a line to ``log(max(regret, 1e-12))`` versus ``log(t)`` (with
    ``t = 1..T``) over the second half of the horizon and returns its slope.
    Sublinear regret corresponds to a slope strictly below 1.

    Parameters
    ----------
    regret : np.ndarray
        Cumulative regret curve, shape (T,).

    Returns
    -------
    float
        The fitted slope; 0.0 when the final regret is non-positive or the
        curve is too short to fit a line.
    """
    regret = np.asarray(regret, dtype=np.float64)
    if regret.size == 0 or regret[-1] <= 0:
        return 0.0
    t = np.arange(1, regret.size + 1, dtype=np.float64)
    half = regret.size // 2
    log_t = np.log(t[half:])
    log_r = np.log(np.maximum(regret[half:], 1e-12))
    if log_t.size < 2:
        return 0.0
    slope, _ = np.polyfit(log_t, log_r, 1)
    return float(slope)
