"""Weighted evaluation metrics for sequential prediction runs."""

from __future__ import annotations

import numpy as np

from ..algorithms.base import RunResult

__all__ = ["mse", "mae", "weighted_r2", "summarize_run"]


def _resolve_weights(y_true: np.ndarray, weights: np.ndarray | None) -> np.ndarray:
    """Return float64 weights, defaulting to all-ones matching ``y_true``."""
    if weights is None:
        return np.ones_like(y_true, dtype=np.float64)
    return np.asarray(weights, dtype=np.float64)


def mse(y_true: np.ndarray, y_pred: np.ndarray, weights: np.ndarray | None = None) -> float:
    """Weighted mean squared error.

    Parameters
    ----------
    y_true : np.ndarray
        Ground-truth targets, shape (n,).
    y_pred : np.ndarray
        Predictions, shape (n,).
    weights : np.ndarray or None
        Non-negative sample weights; defaults to all ones.

    Returns
    -------
    float
        ``sum(w * (y - yhat)^2) / sum(w)``.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    w = _resolve_weights(y_true, weights)
    return float(np.sum(w * (y_true - y_pred) ** 2) / np.sum(w))


def mae(y_true: np.ndarray, y_pred: np.ndarray, weights: np.ndarray | None = None) -> float:
    """Weighted mean absolute error.

    Parameters
    ----------
    y_true : np.ndarray
        Ground-truth targets, shape (n,).
    y_pred : np.ndarray
        Predictions, shape (n,).
    weights : np.ndarray or None
        Non-negative sample weights; defaults to all ones.

    Returns
    -------
    float
        ``sum(w * |y - yhat|) / sum(w)``.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    w = _resolve_weights(y_true, weights)
    return float(np.sum(w * np.abs(y_true - y_pred)) / np.sum(w))


def weighted_r2(y_true: np.ndarray, y_pred: np.ndarray, weights: np.ndarray | None = None) -> float:
    """Sample-weighted zero-mean R2 (the Jane Street competition metric).

    Uses the zero-mean formulation ``1 - sum(w*(y - yhat)^2) / sum(w*y^2)``;
    the denominator is NOT mean-centered.

    Parameters
    ----------
    y_true : np.ndarray
        Ground-truth targets, shape (n,).
    y_pred : np.ndarray
        Predictions, shape (n,).
    weights : np.ndarray or None
        Non-negative sample weights; defaults to all ones.

    Returns
    -------
    float
        Weighted zero-mean R2; 0.0 when the denominator is zero.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    w = _resolve_weights(y_true, weights)
    denominator = float(np.sum(w * y_true**2))
    if denominator == 0.0:
        return 0.0
    numerator = float(np.sum(w * (y_true - y_pred) ** 2))
    return 1.0 - numerator / denominator


def summarize_run(result: RunResult) -> dict[str, float]:
    """Summarize a prequential run into scalar metrics.

    Parameters
    ----------
    result : RunResult
        Output of :meth:`dfsl.algorithms.OnlineLearner.run`.

    Returns
    -------
    dict[str, float]
        Keys: ``n_steps``, ``total_weighted_loss``, ``mean_loss``,
        ``final_avg_loss`` (mean over the last ``max(1, n // 10)`` losses),
        ``mse``, ``mae``, ``weighted_r2``.
    """
    losses = np.asarray(result.losses, dtype=np.float64)
    n = int(losses.size)
    tail = losses[-max(1, n // 10) :]
    return {
        "n_steps": n,
        "total_weighted_loss": float(np.sum(losses)),
        "mean_loss": float(np.mean(losses)),
        "final_avg_loss": float(np.mean(tail)),
        "mse": mse(result.targets, result.predictions, result.weights),
        "mae": mae(result.targets, result.predictions, result.weights),
        "weighted_r2": weighted_r2(result.targets, result.predictions, result.weights),
    }
