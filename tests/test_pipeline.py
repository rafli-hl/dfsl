"""End-to-end pipeline tests: config parsing, factory wiring, and the train CLI."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from dfsl import RobustOMD, SyntheticHeavyTailed
from dfsl.evaluation import mae, mse, summarize_run, weighted_r2
from dfsl.factory import (
    apply_max_steps,
    build_dataset,
    build_learner,
    load_experiment_config,
)
from dfsl.utils.io import load_yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs"

SUMMARY_KEYS = {
    "n_steps",
    "total_weighted_loss",
    "mean_loss",
    "final_avg_loss",
    "mse",
    "mae",
    "weighted_r2",
}


@pytest.mark.parametrize("name", ["default.yaml", "synthetic.yaml", "jane.yaml"])
def test_experiment_configs_parse(name: str) -> None:
    config = load_experiment_config(CONFIG_DIR / name)
    assert isinstance(config, dict)
    assert "dataset" in config
    assert "algorithm" in config
    assert "type" in config["dataset"]
    assert "name" in config["algorithm"]


def test_ablation_config_has_sweep() -> None:
    config = load_yaml(CONFIG_DIR / "ablation.yaml")
    assert "dataset" in config
    assert "base_algorithm" in config
    assert "sweep" in config
    assert "algorithm" not in config
    for key in ("estimator", "window", "clip_multiplier"):
        assert key in config["sweep"]
        assert isinstance(config["sweep"][key], list)


def test_factory_round_trip() -> None:
    config = load_experiment_config(CONFIG_DIR / "synthetic.yaml")
    dataset_cfg = apply_max_steps(config["dataset"], 2000)
    # apply_max_steps must return a copy and not mutate the original config.
    assert config["dataset"]["n_steps"] == 20000
    dataset = build_dataset(dataset_cfg)
    assert isinstance(dataset, SyntheticHeavyTailed)
    assert len(dataset) == 2000
    learner = build_learner(config["algorithm"], dim=dataset.dim)
    assert isinstance(learner, RobustOMD)
    result = learner.run(dataset)
    metrics = summarize_run(result)
    assert SUMMARY_KEYS <= set(metrics)
    assert int(metrics["n_steps"]) == 2000
    for key in SUMMARY_KEYS:
        assert math.isfinite(float(metrics[key]))


def _load_train_module() -> ModuleType:
    train_path = PROJECT_ROOT / "experiments" / "train.py"
    spec = importlib.util.spec_from_file_location("dfsl_train_cli", train_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_train_main_smoke(tmp_path: Path) -> None:
    train = _load_train_module()
    out_dir = Path(
        train.main(
            [
                "--config",
                str(CONFIG_DIR / "synthetic.yaml"),
                "--output",
                str(tmp_path / "run"),
                "--max-steps",
                "1000",
            ]
        )
    )
    assert out_dir.is_dir()
    for artifact in ("run.parquet", "metrics.json", "config.yaml"):
        assert (out_dir / artifact).is_file()
    metrics = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
    assert math.isfinite(float(metrics["mse"]))


def test_weighted_r2_sanity() -> None:
    y = np.array([1.5, -2.0, 0.5, 3.0])
    assert weighted_r2(y, y.copy()) == pytest.approx(1.0)
    assert weighted_r2(y, np.zeros_like(y)) == pytest.approx(0.0)
    weights = np.array([0.5, 2.0, 1.0, 0.25])
    assert weighted_r2(y, y.copy(), weights) == pytest.approx(1.0)
    # Non-proportional weighted case (hand-computed): numerator = 3*(1-0)^2 = 3,
    # denominator = 3*1^2 + 1*2^2 = 7, so R2 = 1 - 3/7.
    y2 = np.array([1.0, 2.0])
    y2_hat = np.array([0.0, 2.0])
    w2 = np.array([3.0, 1.0])
    assert weighted_r2(y2, y2_hat, w2) == pytest.approx(1.0 - 3.0 / 7.0)
    # Same weights through the other weighted metrics: sum(w) = 4.
    assert mse(y2, y2_hat, w2) == pytest.approx(3.0 / 4.0)
    assert mae(y2, y2_hat, w2) == pytest.approx(3.0 / 4.0)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
