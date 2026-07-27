"""Robust online mirror descent with estimator-driven gradient clipping."""

from __future__ import annotations

from collections import deque
from typing import Callable

import numpy as np

from dfsl.algorithms.base import OnlineGradientDescent
from dfsl.estimators import get_estimator


class RobustOMD(OnlineGradientDescent):
    """Online mirror descent with a distribution-free clipping threshold.

    With the Euclidean mirror map, mirror descent reduces to projected gradient
    descent; robustness to heavy-tailed or contaminated gradients comes from
    clipping each gradient at ``clip_multiplier`` times a robust-statistics
    estimate (Catoni, median-of-means, or trimmed mean) of the typical gradient
    norm over a sliding window. The threshold requires only a bounded second
    moment of the gradient norms, making the method distribution-free.
    """

    def __init__(
        self,
        dim: int,
        learning_rate: float = 0.1,
        estimator: str | Callable[..., float] = "catoni",
        window: int = 256,
        clip_multiplier: float = 3.0,
        projection_radius: float | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(
            dim=dim,
            learning_rate=learning_rate,
            projection_radius=projection_radius,
            seed=seed,
        )
        self._estimator = get_estimator(estimator) if isinstance(estimator, str) else estimator
        self.window = window
        self.clip_multiplier = clip_multiplier
        self._norm_history: deque[float] = deque(maxlen=window)

    def _clip_gradient(self, g: np.ndarray) -> np.ndarray:
        """Clip ``g`` at a robust estimate of the typical gradient norm."""
        norm = float(np.linalg.norm(g))
        if not np.isfinite(norm):
            return g
        self._norm_history.append(norm)
        if len(self._norm_history) >= 10:
            m_hat = float(self._estimator(np.asarray(self._norm_history)))
            tau = self.clip_multiplier * max(m_hat, 1e-12)
            if norm > tau:
                g = g * (tau / norm)
        return g
