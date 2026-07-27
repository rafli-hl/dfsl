"""Train a single online learner from a YAML experiment config."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from dfsl.evaluation import summarize_run
from dfsl.factory import apply_max_steps, build_dataset, build_learner, load_experiment_config
from dfsl.utils.io import ensure_dir, find_project_root, save_json, save_yaml
from dfsl.utils.logger import get_logger
from dfsl.utils.seed import set_seed


def main(argv: list[str] | None = None) -> Path:
    """Run the training CLI and return the output directory.

    Parameters
    ----------
    argv : list[str] | None
        Command-line arguments; ``None`` reads ``sys.argv``.

    Returns
    -------
    Path
        Directory containing ``run.parquet``, ``metrics.json`` and
        ``config.yaml``.
    """
    parser = argparse.ArgumentParser(description="Train an online learner from a YAML config.")
    parser.add_argument("--config", required=True, help="Path to an experiment YAML config.")
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory (default: <output_root>/<config stem> under the project root).",
    )
    parser.add_argument("--seed", type=int, default=None, help="Override the config seed.")
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
    if args.seed is not None:
        cfg["seed"] = int(args.seed)
    set_seed(int(cfg["seed"]))
    cfg["dataset"] = apply_max_steps(cfg["dataset"], args.max_steps)

    if args.output is not None:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
    else:
        output = root / cfg["output_root"] / config_path.stem
    ensure_dir(output)

    dataset = build_dataset(cfg["dataset"])
    learner = build_learner(cfg["algorithm"], dim=dataset.dim)
    logger.info(
        "Training {} on {} dataset: {} steps, dim={}",
        type(learner).__name__,
        cfg["dataset"].get("type", "?"),
        len(dataset),
        dataset.dim,
    )
    result = learner.run(dataset)
    metrics = summarize_run(result)

    result.to_frame().write_parquet(output / "run.parquet")
    save_json(metrics, output / "metrics.json")
    save_yaml(cfg, output / "config.yaml")
    logger.info(
        "train done: mse={:.6g} mae={:.6g} weighted_r2={:.6g} mean_loss={:.6g} -> {}",
        metrics["mse"],
        metrics["mae"],
        metrics["weighted_r2"],
        metrics["mean_loss"],
        output,
    )
    return output


if __name__ == "__main__":
    main()
