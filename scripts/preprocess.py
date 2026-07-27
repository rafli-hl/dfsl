"""Preprocess the raw Jane Street training data into a cleaned parquet file."""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

from dfsl.utils.io import ensure_dir, find_project_root
from dfsl.utils.logger import get_logger

FEATURE_COLS: list[str] = [f"feature_{i:02d}" for i in range(79)]
RESPONDER = "responder_6"


def main(argv: list[str] | None = None) -> Path:
    """Clean the raw training data and return the output directory.

    Writes ``train_clean.parquet`` (null responder rows dropped, feature nulls
    filled with 0.0, sorted by date/time/symbol) and ``feature_stats.parquet``
    (per-feature mean and std) into the output directory.
    """
    parser = argparse.ArgumentParser(description="Preprocess the Jane Street training data.")
    parser.add_argument(
        "--input",
        default="data/raw/jane",
        help="Raw data directory containing train.parquet (project-root-relative unless absolute).",
    )
    parser.add_argument(
        "--output",
        default="data/processed/jane",
        help="Output directory (project-root-relative unless absolute).",
    )
    parser.add_argument(
        "--date-range",
        type=int,
        nargs=2,
        default=None,
        metavar=("FIRST", "LAST"),
        help="Inclusive date_id range to keep.",
    )
    parser.add_argument("--max-rows", type=int, default=None, help="Cap the number of rows kept.")
    args = parser.parse_args(argv)

    logger = get_logger()
    root = find_project_root(Path(__file__).resolve().parent)
    input_dir = Path(args.input)
    if not input_dir.is_absolute():
        input_dir = root / input_dir
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    ensure_dir(output_dir)

    lf = pl.scan_parquet(str(input_dir / "train.parquet" / "**" / "*.parquet"))
    if args.date_range is not None:
        first, last = args.date_range
        lf = lf.filter(pl.col("date_id").is_between(first, last))
    lf = lf.filter(pl.col(RESPONDER).is_not_null())
    lf = lf.with_columns(
        [pl.col(col).cast(pl.Float64).fill_null(0.0) for col in FEATURE_COLS]
    )
    lf = lf.sort(["date_id", "time_id", "symbol_id"])
    if args.max_rows is not None:
        lf = lf.head(args.max_rows)

    clean_path = output_dir / "train_clean.parquet"
    logger.info("Writing cleaned data to {} ...", clean_path)
    lf.sink_parquet(clean_path)

    logger.info("Computing per-feature statistics ...")
    agg = lf.select(
        [pl.col(col).mean().alias(f"mean_{col}") for col in FEATURE_COLS]
        + [pl.col(col).std().alias(f"std_{col}") for col in FEATURE_COLS]
    ).collect()
    stats = pl.DataFrame(
        {
            "feature": FEATURE_COLS,
            "mean": [agg.item(0, f"mean_{col}") for col in FEATURE_COLS],
            "std": [agg.item(0, f"std_{col}") for col in FEATURE_COLS],
        }
    )
    stats_path = output_dir / "feature_stats.parquet"
    stats.write_parquet(stats_path)
    logger.info("Done. Outputs: {} and {}", clean_path, stats_path)
    return output_dir


if __name__ == "__main__":
    main()
