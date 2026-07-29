"""Online and batch feature normalization utilities."""

from __future__ import annotations

from collections import deque
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


class OnlineScaleTracker:
    """Streaming robust estimate of the scale of a stream of gradient norms.

    Maintains a robustified exponential moving average of the observed norms: a
    single heavy-tailed spike contributes at most ``winsor`` times the current
    estimate, so the tracker follows the *regime* scale rather than chasing
    individual outliers. Used by :class:`~dfsl.algorithms.ScaleNormalizedOGD` to
    make the gradient step scale-invariant.

    The estimate returned by :meth:`step` is *predictable*: after warm-up it
    depends only on norms observed before the current one.

    Parameters
    ----------
    decay : float
        EMA decay ``beta`` in ``[0, 1)``; larger is slower/smoother.
    winsor : float
        A new norm is capped at ``winsor * current_scale`` before it updates the
        EMA, bounding the influence of a heavy-tailed spike.
    eps : float
        Scale floor, also the value returned before any data is seen.
    """

    def __init__(self, decay: float = 0.99, winsor: float = 8.0, eps: float = 1e-8) -> None:
        if not 0.0 <= decay < 1.0:
            raise ValueError(f"decay must be in [0, 1), got {decay}")
        if winsor <= 0.0:
            raise ValueError(f"winsor must be positive, got {winsor}")
        self.decay = decay
        self.winsor = winsor
        self.eps = eps
        self._scale: float | None = None

    @property
    def scale(self) -> float:
        """Current predictable scale estimate (``eps`` before any data)."""
        return self.eps if self._scale is None else max(self._scale, self.eps)

    def step(self, norm: float) -> float:
        """Return the scale to normalize the current norm by, then fold it in.

        On the first call the estimate is initialized to ``norm`` and returned.
        On later calls the *pre-update* (predictable) scale is returned and the
        winsorized ``norm`` updates the running estimate.
        """
        norm = float(norm)
        if not np.isfinite(norm) or norm < 0.0:
            return self.scale
        if self._scale is None:
            self._scale = max(norm, self.eps)
            return self._scale
        pre = max(self._scale, self.eps)
        capped = min(norm, self.winsor * self._scale)
        self._scale = self.decay * self._scale + (1.0 - self.decay) * capped
        return pre


class TwoTimescaleScaleTracker:
    """Two-timescale (peak-hold) scale tracker: react up fast, decay down slowly.

    ``s_t = max( C * median(recent ||g||),  (1 - decay) * s_{t-1} )``. The short
    trailing median reacts up quickly to a genuine scale increase while remaining
    robust to individual heavy-tailed spikes; the geometric ``(1 - decay)`` release
    lets ``s_t`` fall only slowly, so it never under-shoots a recent rise (protecting
    the lower bracket) and its upward variation stays small.

    This is the tracker analyzed in ``results/research/THEORY_FORMAL.md`` (§4); to
    keep the upward variation ``W_s = O(V_sigma^+)`` there, choose ``decay`` on the
    order of ``1 / regime_length`` (too large a decay churns and inflates ``W_s``).
    Same predictable ``step``/``scale`` interface as :class:`OnlineScaleTracker`.

    Parameters
    ----------
    fast_window : int
        Length of the trailing window whose median gives the fast scale read.
    decay : float
        Geometric release rate ``rho`` in ``[0, 1)``; smaller = slower release.
    scale : float
        Multiplier ``C`` applied to the median (e.g. to bias toward the lower bracket).
    eps : float
        Scale floor, also the value returned before any data is seen.
    """

    def __init__(
        self, fast_window: int = 64, decay: float = 1e-4, scale: float = 1.0, eps: float = 1e-8
    ) -> None:
        if fast_window < 1:
            raise ValueError(f"fast_window must be >= 1, got {fast_window}")
        if not 0.0 <= decay < 1.0:
            raise ValueError(f"decay must be in [0, 1), got {decay}")
        if scale <= 0.0:
            raise ValueError(f"scale must be positive, got {scale}")
        self.fast_window = fast_window
        self.decay = decay
        self.C = scale
        self.eps = eps
        self._buf: deque[float] = deque(maxlen=fast_window)
        self._scale: float | None = None

    @property
    def scale(self) -> float:
        """Current predictable scale estimate (``eps`` before any data)."""
        return self.eps if self._scale is None else max(self._scale, self.eps)

    def step(self, norm: float) -> float:
        """Return the (predictable) envelope scale, then fold ``norm`` in."""
        norm = float(norm)
        if not np.isfinite(norm) or norm < 0.0:
            return self.scale
        if self._scale is None:
            self._scale = max(norm, self.eps)
            self._buf.append(norm)
            return self._scale
        pre = max(self._scale, self.eps)  # predictable: based on past only
        self._buf.append(norm)
        fast = self.C * float(np.median(self._buf))
        self._scale = max(fast, (1.0 - self.decay) * self._scale)
        return pre


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
