"""Jane Street Real-Time Market Data Forecasting dataset loader."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

import numpy as np
import polars as pl

from ..utils.io import find_project_root
from .base import SequentialDataset


class JaneStreetDataset(SequentialDataset):
    """Sequential view of the Jane Street Kaggle training data.

    Loads the hive-partitioned ``train.parquet`` directory lazily with polars,
    applies optional date/symbol filters, drops rows with a null target
    responder, sorts chronologically by ``(date_id, time_id, symbol_id)`` and
    materializes float64 numpy arrays for online learning.

    Parameters
    ----------
    data_dir : str | Path | None
        Directory containing ``train.parquet``. Defaults to
        ``<project root>/data/raw/jane``.
    responder : str
        Target column, default the competition target ``"responder_6"``.
    feature_cols : Sequence[str] | None
        Feature columns to load; defaults to all 79 features.
    max_rows : int | None
        Keep only the first ``max_rows`` rows after filtering and sorting.
    symbols : Sequence[int] | None
        Restrict to these ``symbol_id`` values.
    date_range : tuple[int, int] | None
        Inclusive ``(start, end)`` range of ``date_id`` values.
    fill_null : float
        Value used to fill missing feature entries.
    standardize : bool or str
        Feature z-scoring mode. ``True`` or ``"causal"`` uses a strictly
        past-only (expanding) estimate per row, so no future information leaks
        into the online evaluation. ``"full"`` uses full-sample statistics
        (look-ahead; inflates online R^2) and is kept only to reproduce
        pre-2026-07 results. ``False`` disables standardization. The raw
        features span several orders of magnitude, which makes unscaled
        gradient methods diverge.

    Attributes
    ----------
    X : np.ndarray
        Feature matrix, shape ``(n_steps, dim)``, float64.
    y : np.ndarray
        Target responder values, shape ``(n_steps,)``, float64.
    weights : np.ndarray
        Evaluation sample weights, shape ``(n_steps,)``, float64.
    meta : pl.DataFrame
        ``date_id``/``time_id``/``symbol_id`` columns for splitting/analysis.
    """

    FEATURE_COLS: ClassVar[list[str]] = [f"feature_{i:02d}" for i in range(79)]
    RESPONDER_COLS: ClassVar[list[str]] = [f"responder_{i}" for i in range(9)]
    METADATA_COLS: ClassVar[list[str]] = ["date_id", "time_id", "symbol_id", "weight"]

    @staticmethod
    def _causal_standardize(X: np.ndarray, eps: float = 1e-8, clip: float = 8.0) -> np.ndarray:
        """Z-score each feature using only past rows (strictly predictable).

        Row ``i`` is standardized with the mean/std of rows ``0..i-1`` (an
        expanding, causal estimate), so no future information leaks into any
        row. Row 0 is left uncentered (no history), and standardized values are
        clipped to ``[-clip, clip]`` as a numerical safeguard against the
        cold-start when an early feature has near-zero running spread. This
        replaces full-sample z-scoring, which peeks at the whole slice and
        inflates online R^2.
        """
        X = np.asarray(X, dtype=np.float64)
        n, d = X.shape
        if n <= 1:
            return X.copy()
        counts = np.arange(1, n + 1, dtype=np.float64).reshape(-1, 1)
        mean = np.cumsum(X, axis=0) / counts
        var = np.maximum(np.cumsum(X * X, axis=0) / counts - mean * mean, 0.0)
        std = np.sqrt(var)
        # shift so row i uses statistics from rows [0, i-1] only
        mean_prev = np.vstack([np.zeros((1, d)), mean[:-1]])
        std_prev = np.vstack([np.ones((1, d)), std[:-1]])
        Z = (X - mean_prev) / np.maximum(std_prev, eps)
        return np.clip(Z, -clip, clip)

    def __init__(
        self,
        data_dir: str | Path | None = None,
        responder: str = "responder_6",
        feature_cols: Sequence[str] | None = None,
        max_rows: int | None = None,
        symbols: Sequence[int] | None = None,
        date_range: tuple[int, int] | None = None,
        fill_null: float = 0.0,
        standardize: bool | str = False,
    ) -> None:
        if data_dir is None:
            data_dir = find_project_root() / "data" / "raw" / "jane"
        data_dir = Path(data_dir)
        train_path = data_dir / "train.parquet"
        if not train_path.exists():
            raise FileNotFoundError(
                f"Jane Street training data not found at {train_path}. "
                "Run 'python scripts/download_data.py' to download it."
            )

        cols = list(feature_cols) if feature_cols is not None else list(self.FEATURE_COLS)

        lf = pl.scan_parquet(str(train_path / "**" / "*.parquet"))
        if date_range is not None:
            lf = lf.filter(pl.col("date_id").is_between(date_range[0], date_range[1]))
        if symbols is not None:
            lf = lf.filter(pl.col("symbol_id").is_in(list(symbols)))
        lf = lf.filter(pl.col(responder).is_not_null())
        lf = lf.select([*self.METADATA_COLS, *cols, responder])
        lf = lf.sort(["date_id", "time_id", "symbol_id"])
        if max_rows is not None:
            lf = lf.head(max_rows)
        lf = lf.with_columns(
            [pl.col(c).cast(pl.Float64).fill_null(fill_null) for c in cols]
        )
        df = lf.collect()

        self.X = df.select(cols).to_numpy().astype(np.float64)
        self.feature_means: np.ndarray | None = None
        self.feature_stds: np.ndarray | None = None
        if standardize == "full":
            # Legacy full-sample z-scoring. This peeks at the whole slice
            # (look-ahead) and inflates online R^2; kept only to reproduce
            # pre-2026-07 numbers. Prefer causal standardization (the default
            # when ``standardize=True``) for honest sequential evaluation.
            self.feature_means = self.X.mean(axis=0)
            self.feature_stds = self.X.std(axis=0)
            self.X = self.X - self.feature_means
            scalable = self.feature_stds > 1e-12
            self.X[:, scalable] /= self.feature_stds[scalable]
        elif standardize:  # True or "causal": strictly past-only, no look-ahead
            self.X = self._causal_standardize(self.X)
        self.y = df.get_column(responder).cast(pl.Float64).to_numpy().astype(np.float64)
        self.weights = (
            df.get_column("weight").cast(pl.Float64).to_numpy().astype(np.float64)
        )
        self.meta = df.select(["date_id", "time_id", "symbol_id"])
