"""Benchmark the learner grid on a single dataset and compare regret."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import polars as pl

from dfsl.evaluation import best_fixed_linear, linear_losses, regret_curve, summarize_run
from dfsl.factory import apply_max_steps, build_dataset, build_learner, load_experiment_config
from dfsl.utils.io import ensure_dir, find_project_root
from dfsl.utils.logger import get_logger
from dfsl.utils.seed import set_seed
from dfsl.visualization import plot_loss_curves, plot_regret_curves

ROBUST_ESTIMATORS: tuple[str, ...] = ("catoni", "median_of_means", "trimmed_mean")


def _learner_grid(algo_cfg: dict) -> list[tuple[str, dict]]:
    """Build the (name, algorithm-config) benchmark grid from the base config."""
    learning_rate = float(algo_cfg.get("learning_rate", 0.1))
    window = int(algo_cfg.get("window", 256))
    clip_multiplier = float(algo_cfg.get("clip_multiplier", 3.0))
    grid: list[tuple[str, dict]] = [
        ("ogd", {"name": "ogd", "learning_rate": learning_rate}),
        ("adaptive_clip", {"name": "adaptive_clip", "learning_rate": learning_rate, "window": window}),
    ]
    for estimator in ROBUST_ESTIMATORS:
        grid.append(
            (
                f"robust_omd[{estimator}]",
                {
                    "name": "robust_omd",
                    "learning_rate": learning_rate,
                    "estimator": estimator,
                    "window": window,
                    "clip_multiplier": clip_multiplier,
                },
            )
        )
    return grid


def main(argv: list[str] | None = None) -> Path:
    """Run the benchmark CLI and return the output directory.

    Runs OGD, AdaptiveClip and RobustOMD (one variant per robust estimator)
    on the same dataset, then writes ``comparison.csv``, ``regret_curves.png``
    and ``loss_curves.png``.
    """
    parser = argparse.ArgumentParser(description="Benchmark online learners on one dataset.")
    parser.add_argument("--config", required=True, help="Path to an experiment YAML config.")
    parser.add_argument(
        "--output",
        default="results/benchmark",
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
    cfg = load_experiment_config(config_path)
    set_seed(int(cfg["seed"]))

    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    ensure_dir(output)

    dataset = build_dataset(apply_max_steps(cfg["dataset"], args.max_steps))
    logger.info("Benchmarking on {} steps, dim={}", len(dataset), dataset.dim)

    w_star = best_fixed_linear(dataset.X, dataset.y, dataset.weights)
    comparator_losses = linear_losses(dataset.X, dataset.y, w_star, dataset.weights)

    rows: list[dict] = []
    regrets: dict[str, np.ndarray] = {}
    losses: dict[str, np.ndarray] = {}
    for name, learner_cfg in _learner_grid(cfg["algorithm"]):
        learner = build_learner(learner_cfg, dim=dataset.dim)
        result = learner.run(dataset)
        metrics = summarize_run(result)
        regret = regret_curve(result.losses, comparator_losses)
        regrets[name] = regret
        losses[name] = result.losses
        rows.append({"learner": name, **metrics, "final_regret": float(regret[-1])})
        logger.info(
            "{}: mse={:.6g} weighted_r2={:.6g} final_regret={:.6g}",
            name,
            metrics["mse"],
            metrics["weighted_r2"],
            float(regret[-1]),
        )

    pl.DataFrame(rows).write_csv(output / "comparison.csv")
    plot_regret_curves(regrets, path=output / "regret_curves.png")
    plot_loss_curves(losses, path=output / "loss_curves.png")
    logger.info("benchmark artifacts written to {}", output)
    return output


if __name__ == "__main__":
    main()
