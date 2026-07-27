"""Evaluate one or more finished training runs and plot their loss curves."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import polars as pl

from dfsl.utils.io import find_project_root, load_json
from dfsl.utils.logger import get_logger
from dfsl.visualization import plot_loss_curves


def main(argv: list[str] | None = None) -> Path:
    """Run the evaluation CLI and return the first run directory.

    For every run directory this reads ``metrics.json`` and ``run.parquet``,
    logs the stored metrics and writes ``loss_curve.png`` into the run
    directory. With multiple run directories a ``comparison.csv`` is written
    into the first run directory's parent.
    """
    parser = argparse.ArgumentParser(description="Evaluate finished training runs.")
    parser.add_argument(
        "--run-dir",
        nargs="+",
        required=True,
        help="One or more run directories produced by experiments/train.py.",
    )
    args = parser.parse_args(argv)

    logger = get_logger()
    root = find_project_root(Path(__file__).resolve().parent)

    run_dirs: list[Path] = []
    for raw in args.run_dir:
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        run_dirs.append(path)

    rows: list[dict] = []
    for run_dir in run_dirs:
        metrics = load_json(run_dir / "metrics.json")
        frame = pl.read_parquet(run_dir / "run.parquet")
        logger.info("run {}: {}", run_dir.name, metrics)
        losses = np.asarray(frame["loss"].to_numpy(), dtype=np.float64)
        plot_loss_curves(
            {run_dir.name: losses},
            title=f"Rolling mean loss: {run_dir.name}",
            path=run_dir / "loss_curve.png",
        )
        rows.append({"run": run_dir.name, **metrics})

    if len(run_dirs) > 1:
        comparison_path = run_dirs[0].parent / "comparison.csv"
        pl.DataFrame(rows).write_csv(comparison_path)
        logger.info("wrote comparison of {} runs to {}", len(run_dirs), comparison_path)
    return run_dirs[0]


if __name__ == "__main__":
    main()
