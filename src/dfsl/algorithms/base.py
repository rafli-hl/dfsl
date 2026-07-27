"""Base classes for online learners and run results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import polars as pl

from dfsl.utils.seed import get_rng


@dataclass
class RunResult:
    """Container for the per-step outcome of a sequential run.

    Attributes
    ----------
    predictions : np.ndarray
        Prediction made at each step, before the update.
    targets : np.ndarray
        Observed target at each step.
    weights : np.ndarray
        Sample weight at each step.
    losses : np.ndarray
        Prequential weighted squared loss at each step.
    """

    predictions: np.ndarray
    targets: np.ndarray
    weights: np.ndarray
    losses: np.ndarray

    def to_frame(self) -> pl.DataFrame:
        """Return the run as a polars DataFrame with a step index column."""
        n = len(self.losses)
        return pl.DataFrame(
            {
                "step": np.arange(n, dtype=np.int64),
                "prediction": self.predictions,
                "target": self.targets,
                "weight": self.weights,
                "loss": self.losses,
            }
        )

    def cumulative_loss(self) -> np.ndarray:
        """Return the cumulative sum of per-step losses."""
        return np.cumsum(self.losses)


class OnlineLearner(ABC):
    """Abstract sequential learner following the predict-then-update protocol."""

    def __init__(self, dim: int, seed: int | None = None) -> None:
        self.dim = dim
        self.rng = get_rng(seed)

    @abstractmethod
    def predict(self, x: np.ndarray) -> float:
        """Predict the target for feature vector ``x``."""

    @abstractmethod
    def update(self, x: np.ndarray, y: float, weight: float = 1.0) -> float:
        """Observe ``(x, y, weight)``, take one learning step.

        Returns the prequential weighted squared loss
        ``weight * (predict(x) - y) ** 2`` computed with the parameters held
        before the update step.
        """

    def run(self, dataset: Iterable[tuple[np.ndarray, float, float]]) -> RunResult:
        """Run the learner over a stream of ``(x, y, weight)`` triples."""
        predictions: list[float] = []
        targets: list[float] = []
        weights: list[float] = []
        losses: list[float] = []
        for x, y, w in dataset:
            predictions.append(self.predict(x))
            targets.append(y)
            weights.append(w)
            losses.append(self.update(x, y, w))
        return RunResult(
            predictions=np.asarray(predictions, dtype=np.float64),
            targets=np.asarray(targets, dtype=np.float64),
            weights=np.asarray(weights, dtype=np.float64),
            losses=np.asarray(losses, dtype=np.float64),
        )


class OnlineGradientDescent(OnlineLearner):
    """Online gradient descent for linear regression with squared loss.

    Uses a decaying step size ``learning_rate / sqrt(t)`` and an optional
    Euclidean projection onto a ball of radius ``projection_radius``.
    """

    def __init__(
        self,
        dim: int,
        learning_rate: float = 0.1,
        projection_radius: float | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(dim=dim, seed=seed)
        self.learning_rate = learning_rate
        self.projection_radius = projection_radius
        self.weights = np.zeros(dim)
        self.t = 0

    def predict(self, x: np.ndarray) -> float:
        """Return the linear prediction ``w @ x``."""
        return float(self.weights @ x)

    def update(self, x: np.ndarray, y: float, weight: float = 1.0) -> float:
        """Take one weighted squared-loss gradient step; return prequential loss.

        Numerically saturating: an overflowing loss is reported as ``inf``
        rather than raising, and a step with a non-finite gradient is skipped
        so the iterate can never be poisoned with ``inf``/``nan`` entries.
        """
        self.t += 1
        pred = self.predict(x)
        with np.errstate(over="ignore", invalid="ignore"):
            err = np.float64(pred) - np.float64(y)
            loss = float(np.float64(weight) * err * err)
            g = 2.0 * weight * err * x
        g = self._clip_gradient(g)
        if np.isfinite(g).all():
            self.weights -= (self.learning_rate / np.sqrt(self.t)) * g
            if self.projection_radius is not None:
                norm = float(np.linalg.norm(self.weights))
                if norm > self.projection_radius:
                    self.weights *= self.projection_radius / norm
        return loss

    def _clip_gradient(self, g: np.ndarray) -> np.ndarray:
        """Gradient-clipping hook; identity for plain OGD."""
        return g