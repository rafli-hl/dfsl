"""Synthetic heavy-tailed linear regression streams."""

from __future__ import annotations

import numpy as np

from .base import SequentialDataset


class SyntheticHeavyTailed(SequentialDataset):
    """Linear regression stream with heavy-tailed noise and optional contamination.

    Data model: ``y_t = x_t @ w* + eps_t`` with standard Gaussian features,
    a unit-norm random ground-truth weight vector ``w*``, and noise drawn from
    a configurable (possibly heavy-tailed) distribution. A fraction of targets
    can additionally be contaminated with large-magnitude outliers.

    Parameters
    ----------
    n_steps : int
        Length of the stream.
    dim : int
        Feature dimension.
    noise : str
        One of ``"gaussian"``, ``"student_t"``, ``"pareto"``, ``"cauchy"``.
    noise_scale : float
        Multiplicative scale applied to the raw noise draws.
    df : float
        Degrees of freedom (Student-t) or shape parameter (Pareto).
    contamination : float
        Fraction of steps whose targets receive adversarial outliers.
    contamination_scale : float
        Magnitude of the injected outliers (random sign).
    seed : int
        Seed for the numpy Generator driving all randomness.

    Attributes
    ----------
    true_weights : np.ndarray
        Unit-norm ground-truth weight vector, shape ``(dim,)``.
    y_clean : np.ndarray
        Noise-free targets ``X @ w*``, shape ``(n_steps,)``.
    contamination_mask : np.ndarray
        Boolean mask of contaminated steps, shape ``(n_steps,)``.
    """

    def __init__(
        self,
        n_steps: int = 10000,
        dim: int = 10,
        noise: str = "student_t",
        noise_scale: float = 1.0,
        df: float = 2.5,
        contamination: float = 0.0,
        contamination_scale: float = 50.0,
        seed: int = 0,
    ) -> None:
        rng = np.random.default_rng(seed)
        n = n_steps

        w_star = rng.standard_normal(dim)
        w_star = w_star / np.linalg.norm(w_star)
        self.true_weights: np.ndarray = w_star

        X = rng.standard_normal((n, dim))

        if noise == "gaussian":
            eps = noise_scale * rng.standard_normal(n)
        elif noise == "student_t":
            eps = noise_scale * rng.standard_t(df, n)
        elif noise == "pareto":
            eps = noise_scale * rng.pareto(df, n) * rng.choice([-1.0, 1.0], n)
        elif noise == "cauchy":
            eps = noise_scale * rng.standard_cauchy(n)
        else:
            raise ValueError(
                f"Unknown noise type {noise!r}. Valid options: "
                "'gaussian', 'student_t', 'pareto', 'cauchy'."
            )

        y = X @ w_star + eps
        self.y_clean: np.ndarray = X @ w_star

        mask = np.zeros(n, dtype=bool)
        if contamination > 0:
            k = int(round(contamination * n))
            idx = rng.choice(n, size=k, replace=False)
            y[idx] += contamination_scale * rng.choice([-1.0, 1.0], k)
            mask[idx] = True
        self.contamination_mask: np.ndarray = mask

        self.X = np.asarray(X, dtype=np.float64)
        self.y = np.asarray(y, dtype=np.float64)
        self.weights = np.ones(n_steps, dtype=np.float64)
