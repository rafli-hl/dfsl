"""Online gradient descent with quantile-based adaptive gradient clipping."""

from __future__ import annotations

from collections import deque

import numpy as np

from dfsl.algorithms.base import OnlineGradientDescent


class AdaptiveClip(OnlineGradientDescent):
    """OGD with gradients clipped at a rolling quantile of past gradient norms.

    Maintains a sliding window of unclipped gradient norms and clips each new
    gradient to the ``clip_quantile`` empirical quantile of that history,
    guarding against heavy-tailed loss gradients without distributional
    assumptions.
    """

    def __init__(
        self,
        dim: int,
        learning_rate: float = 0.1,
        clip_quantile: float = 0.9,
        window: int = 256,
        projection_radius: float | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(
            dim=dim,
            learning_rate=learning_rate,
            projection_radius=projection_radius,
            seed=seed,
        )
        self.clip_quantile = clip_quantile
        self.window = window
        self._norm_history: deque[float] = deque(maxlen=window)

    def _clip_gradient(self, g: np.ndarray) -> np.ndarray:
        """Clip ``g`` to the rolling quantile of past unclipped gradient norms."""
        norm = float(np.linalg.norm(g))
        if not np.isfinite(norm):
            return g
        self._norm_history.append(norm)
        if len(self._norm_history) >= 10:
            tau = float(np.quantile(np.asarray(self._norm_history), self.clip_quantile))
            if tau > 0 and norm > tau:
                g = g * (tau / norm)
        return g
