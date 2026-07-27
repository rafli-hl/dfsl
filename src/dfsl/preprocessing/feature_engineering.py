"""Feature engineering helpers for tabular market data frames."""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl


def fill_missing(
    df: pl.DataFrame, cols: Sequence[str], strategy: str = "zero"
) -> pl.DataFrame:
    """Fill nulls in ``cols`` according to ``strategy``.

    Strategies: ``"zero"`` fills with 0.0; ``"median"`` fills with the
    per-column median; ``"forward"`` forward-fills then fills remaining
    leading nulls with 0.0. Unknown strategies raise ValueError.
    """
    if strategy == "zero":
        exprs = [pl.col(c).fill_null(0.0) for c in cols]
    elif strategy == "median":
        exprs = [pl.col(c).fill_null(pl.col(c).median()) for c in cols]
    elif strategy == "forward":
        exprs = [pl.col(c).fill_null(strategy="forward").fill_null(0.0) for c in cols]
    else:
        raise ValueError(
            f"Unknown fill strategy {strategy!r}. Valid options: "
            "'zero', 'median', 'forward'."
        )
    return df.with_columns(exprs)


def add_lag_features(
    df: pl.DataFrame,
    cols: Sequence[str],
    lags: Sequence[int],
    group_col: str = "symbol_id",
    sort_cols: Sequence[str] = ("date_id", "time_id"),
) -> pl.DataFrame:
    """Add per-group lagged copies of ``cols``.

    Sorts by ``[group_col, *sort_cols]`` and adds a column ``'{col}_lag{k}'``
    equal to ``col`` shifted by ``k`` steps within each ``group_col`` group.
    """
    df = df.sort([group_col, *sort_cols])
    exprs = [
        pl.col(c).shift(k).over(group_col).alias(f"{c}_lag{k}")
        for c in cols
        for k in lags
    ]
    return df.with_columns(exprs)


def drop_high_missing(
    df: pl.DataFrame, cols: Sequence[str], max_missing_pct: float = 20.0
) -> list[str]:
    """Return the subset of ``cols`` whose null percentage is <= ``max_missing_pct``."""
    n = df.height
    if n == 0:
        return list(cols)
    keep: list[str] = []
    for c in cols:
        pct = 100.0 * df.get_column(c).null_count() / n
        if pct <= max_missing_pct:
            keep.append(c)
    return keep
