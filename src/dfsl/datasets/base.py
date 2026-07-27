"""Abstract base class for sequential (streaming) regression datasets."""

from __future__ import annotations

from abc import ABC
from collections.abc import Iterator

import numpy as np


class SequentialDataset(ABC):
    """Base class for datasets consumed one step at a time by online learners.

    Concrete subclasses must expose the following float64 numpy arrays:

    - ``X`` : shape ``(n_steps, dim)``, the feature stream.
    - ``y`` : shape ``(n_steps,)``, the regression targets.
    - ``weights`` : shape ``(n_steps,)``, per-step sample weights.

    Iteration and length are implemented here in terms of those arrays.
    """

    X: np.ndarray
    y: np.ndarray
    weights: np.ndarray

    @property
    def dim(self) -> int:
        """Number of features per step."""
        return int(self.X.shape[1])

    @property
    def n_steps(self) -> int:
        """Number of steps in the stream."""
        return int(self.X.shape[0])

    def __len__(self) -> int:
        """Return the number of steps in the stream."""
        return self.n_steps

    def __iter__(self) -> Iterator[tuple[np.ndarray, float, float]]:
        """Yield ``(x_t, y_t, w_t)`` triples in stream order."""
        for i in range(self.n_steps):
            yield self.X[i], float(self.y[i]), float(self.weights[i])
