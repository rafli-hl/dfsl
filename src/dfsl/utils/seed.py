"""Seeding helpers for reproducible experiments."""

from __future__ import annotations

import random

import numpy as np


def set_seed(seed: int) -> np.random.Generator:
    """Seed Python's ``random`` and NumPy's legacy RNG; return a fresh Generator.

    Parameters
    ----------
    seed : int
        Seed applied to ``random.seed``, ``np.random.seed`` and the returned
        ``np.random.default_rng``.

    Returns
    -------
    np.random.Generator
        A generator seeded with ``seed``.
    """
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)


def get_rng(seed: int | np.random.Generator | None = None) -> np.random.Generator:
    """Resolve ``seed`` into a ``np.random.Generator``.

    A Generator is passed through unchanged, an int seeds a new generator, and
    ``None`` yields an OS-entropy-seeded generator.
    """
    if isinstance(seed, np.random.Generator):
        return seed
    return np.random.default_rng(seed)