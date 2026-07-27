"""Ablation over RobustOMD hyperparameters (estimator, window, clip multiplier)."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from dfsl.evaluation import mae, mse, weighted_r2
from dfsl.factory import apply_max_steps, build_dataset, build_learner
from dfsl.utils.io import ensure_dir, find_project_root, load_yaml
from dfsl.utils.logger import get_logger
from dfsl.utils.seed import set_seed
from dfsl.visualization import save_figure


def _plot_ablation_mse(df: pl.DataFrame, path: Path) -> None:
    """Plot mse vs window, one subplot per clip_multiplier, one line per estimator."""
    clip_values = sorted(df["clip_multiplier"].unique().to_list())
    estimators = list(dict.fromkeys(df["estimator"].to_list()))
    fig, axes = plt.subplots(
        1, len(clip_values), figsize=(4.0 * len(clip_values), 3.5), sharey=True
    )
    axes = np.atleast_1d(axes)
    for ax, clip_multiplier in zip(axes, clip_values):
        sub = df.filter(pl.col("clip_multiplier") == clip_multiplier)
        for estimator in estimators:
            est_rows = sub.filter(pl.col("estimator") == estimator).sort("window")
            ax.plot(
                est_rows["window"].to_numpy(),
                est_rows["mse"].to_numpy(),
                marker="o",
                label=estimator,
            )
        ax.set_xscale("log", base=2)
        ax.set_xlabel("window")
        ax.set_title(f"clip_multiplier={clip_multiplier:g}")
    axes[0].set_ylabel("mse")
    axes[0].legend()
    fig.tight_layout()
    save_figure(fig, path)


def main(argv: list[str] | None = None) -> Path:
    """Run the ablation CLI and return the output directory.

    Sweeps the cartesian product of the ``sweep`` lists in the config, runs a
    fresh RobustOMD learner per combination on one shared dataset, and writes
    ``ablation.csv`` plus ``ablation_mse.png``.
    """
    parser = argparse.ArgumentParser(description="RobustOMD hyperparameter ablation.")
    parser.add_argument(
        "--config",
        default="configs/ablation.yaml",
        help="Path to an ablation YAML config.",
    )
    parser.add_argument(
        "--output",
        default="results/ablation",
        help="Output directory (project-root-relative unless absolute).",
    )
    parser.add_argument(
        "--max-steps", type=int, default=None, help="Cap the number of dataset steps."
    )
    args = parser.parse_args(argv)

    logger = get_logger()
    root = find_project_root(Path(__file__).resolve().parent)

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    cfg = load_yaml(config_path)
    missing = [key for key in ("dataset", "base_algorithm", "sweep") if key not in cfg]
    if missing:
        raise ValueError(f"ablation config {config_path} is missing required keys: {missing}")
    set_seed(int(cfg["seed"]))

    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    ensure_dir(output)

    dataset = build_dataset(apply_max_steps(cfg["dataset"], args.max_steps))
    logger.info("Ablation dataset: {} steps, dim={}", len(dataset), dataset.dim)

    sweep = cfg["sweep"]
    rows: list[dict] = []
    for estimator, window, clip_multiplier in itertools.product(
        sweep["estimator"], sweep["window"], sweep["clip_multiplier"]
    ):
        algo_cfg = {
            **cfg["base_algorithm"],
            "estimator": estimator,
            "window": int(window),
            "clip_multiplier": float(clip_multiplier),
        }
        learner = build_learner(algo_cfg, dim=dataset.dim)
        result = learner.run(dataset)
        row = {
            "estimator": estimator,
            "window": int(window),
            "clip_multiplier": float(clip_multiplier),
            "mse": mse(result.targets, result.predictions, result.weights),
            "mae": mae(result.targets, result.predictions, result.weights),
            "weighted_r2": weighted_r2(result.targets, result.predictions, result.weights),
        }
        rows.append(row)
        logger.info(
            "estimator={} window={} clip_multiplier={:g}: mse={:.6g} weighted_r2={:.6g}",
            estimator,
            window,
            clip_multiplier,
            row["mse"],
            row["weighted_r2"],
        )

    df = pl.DataFrame(rows)
    df.write_csv(output / "ablation.csv")
    _plot_ablation_mse(df, output / "ablation_mse.png")
    logger.info("ablation artifacts written to {}", output)
    return output


if __name__ == "__main__":
    main()
