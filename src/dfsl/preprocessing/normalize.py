"""Online and batch feature normalization utilities."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl


class OnlineStandardizer:
    """Streaming per-feature standardizer using Welford's algorithm.

    Maintains running mean and (population) variance per feature and
    standardizes incoming vectors with the statistics seen so far.

    Parameters
    ----------
    dim : int
        Feature dimension.
    eps : float
        Variance floor added inside the square root for numerical stability.
    """

    def __init__(self, dim: int, eps: float = 1e-8) -> None:
        self.dim = dim
        self.eps = eps
        self.count = 0
        self.mean = np.zeros(dim, dtype=np.float64)
        self.M2 = np.zeros(dim, dtype=np.float64)

    def partial_fit(self, x: np.ndarray) -> "OnlineStandardizer":
        """Update running statistics with one observation ``x``."""
        x = np.asarray(x, dtype=np.float64)
        self.count += 1
        delta = x - self.mean
        self.mean += delta / self.count
        self.M2 += delta * (x - self.mean)
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        """Standardize ``x`` with the current running statistics."""
        x = np.asarray(x, dtype=np.float64)
        if self.count < 2:
            return x - self.mean
        return (x - self.mean) / np.sqrt(self.variance + self.eps)

    def fit_transform_step(self, x: np.ndarray) -> np.ndarray:
        """Update the statistics with ``x``, then return its standardized value."""
        return self.partial_fit(x).transform(x)

    @property
    def variance(self) -> np.ndarray:
        """Running population variance per feature (zeros before any data)."""
        if self.count > 0:
            return self.M2 / self.count
        return np.zeros(self.dim, dtype=np.float64)


def standardize(df: pl.DataFrame, cols: Sequence[str]) -> pl.DataFrame:
    """Standardize ``cols`` to zero mean and unit variance.

    Columns whose standard deviation is zero or null are left unchanged.
    """
    exprs = []
    for c in cols:
        std = df.get_column(c).std()
        if std is None or std == 0:
            continue
        mean = df.get_column(c).mean()
        exprs.append(((pl.col(c) - mean) / std).alias(c))
    if exprs:
        df = df.with_columns(exprs)
    return df


def clip_extremes(
    df: pl.DataFrame,
    cols: Sequence[str],
    lower_q: float = 0.005,
    upper_q: float = 0.995,
) -> pl.DataFrame:
    """Winsorize ``cols`` at the given lower and upper empirical quantiles."""
    return df.with_columns(
        [
            pl.col(c).clip(pl.col(c).quantile(lower_q), pl.col(c).quantile(upper_q))
            for c in cols
        ]
    )
