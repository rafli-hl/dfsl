"""dfsl — Distribution-Free Sequential Learning.

Robust online (sequential) regression under heavy-tailed / contaminated data:
robust mean estimators (Catoni, median-of-means, trimmed mean) plugged into
clipped online gradient methods.
"""

from __future__ import annotations

from .algorithms import (
    AdaptiveClip,
    OnlineGradientDescent,
    OnlineLearner,
    RobustOMD,
    RunResult,
)
from .datasets import JaneStreetDataset, SequentialDataset, SyntheticHeavyTailed
from .estimators import (
    ESTIMATORS,
    catoni_mean,
    get_estimator,
    median_of_means,
    trimmed_mean,
)

__version__ = "0.1.0"

__all__ = [
    "OnlineLearner",
    "OnlineGradientDescent",
    "AdaptiveClip",
    "RobustOMD",
    "RunResult",
    "SequentialDataset",
    "SyntheticHeavyTailed",
    "JaneStreetDataset",
    "catoni_mean",
    "median_of_means",
    "trimmed_mean",
    "get_estimator",
    "ESTIMATORS",
]
