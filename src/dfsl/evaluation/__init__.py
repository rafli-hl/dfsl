"""Evaluation metrics, regret analysis, and robustness experiments."""

from __future__ import annotations

from .metrics import mae, mse, summarize_run, weighted_r2
from .regret import best_fixed_linear, empirical_regret_slope, linear_losses, regret_curve
from .robustness import breakdown_experiment, contaminate_targets

__all__ = [
    "mse",
    "mae",
    "weighted_r2",
    "summarize_run",
    "best_fixed_linear",
    "linear_losses",
    "regret_curve",
    "empirical_regret_slope",
    "contaminate_targets",
    "breakdown_experiment",
]
