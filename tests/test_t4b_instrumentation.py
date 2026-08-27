"""T4B's instrumentation gate: the harness must reproduce the library learners.

Same purpose as C10M's gate. ``research_t4b_clipper_windows`` re-implements the clipped OGD
loop so it can run on the ten-window instrument's vectorised calling convention, which the
``dfsl.algorithms`` classes do not expose. If that loop drifts from the classes, T4B measures a
reimplementation and its verdict is about this file rather than about the clippers.

This caught a real defect on the first run: the script hand-rolled median-of-means with 8
unpermuted blocks, while ``dfsl.estimators.median_of_means`` permutes the sample and defaults to
24 blocks. The iterate paths differed by up to 3.7e-2 relative. The run was stopped and the
script switched to calling the library estimator.

Data-free by construction -- a seeded random linear stream -- so it is a real check in a
checkout with no market data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from research_t4b_clipper_windows import clip_perrow  # noqa: E402

from dfsl.algorithms import AdaptiveClip, RobustOMD  # noqa: E402


def _stream(n=1500, d=10, seed=20260827):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, d))
    y = X @ rng.normal(size=d) + rng.standard_t(3.0, size=n) * 0.8
    return X, y, np.ones(n)


def _library_predictions(learner, X, y, wts):
    out = np.empty(len(y))
    for i in range(len(y)):
        out[i] = learner.predict(X[i])
        learner.update(X[i], y[i], wts[i])
    return out


@pytest.mark.parametrize("lr", [0.01, 0.05])
@pytest.mark.parametrize("kind", ["adaptive_clip", "robust_omd"])
def test_harness_reproduces_library_learner(kind: str, lr: float) -> None:
    """T4B's loop must match dfsl's class on the same stream, to floating-point noise."""
    X, y, wts = _stream()
    d = X.shape[1]
    if kind == "adaptive_clip":
        lib = AdaptiveClip(dim=d, learning_rate=lr, window=512)
    else:
        lib = RobustOMD(dim=d, learning_rate=lr, estimator="median_of_means",
                        window=512, clip_multiplier=3.0)

    mine = clip_perrow(X, y, wts, kind, lr)
    theirs = _library_predictions(lib, X, y, wts)

    scale = max(1e-12, float(np.max(np.abs(theirs))))
    rel = float(np.max(np.abs(mine - theirs))) / scale
    assert rel < 1e-10, (
        f"{kind} at lr={lr}: T4B's harness and dfsl.{type(lib).__name__} disagree by "
        f"{rel:.3e} relative. T4B would be measuring a reimplementation -- fix the harness "
        f"rather than loosening this bound."
    )
