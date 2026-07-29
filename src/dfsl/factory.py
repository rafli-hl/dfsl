"""Config-driven construction of datasets and learners.

Used by the experiment CLIs and the test suite to build objects from the
YAML configuration schema (``configs/*.yaml``).
"""

from __future__ import annotations

from pathlib import Path

from .algorithms import (
    AdaptiveClip,
    OnlineGradientDescent,
    OnlineLearner,
    RobustOMD,
    ScaleNormalizedOGD,
)
from .datasets import JaneStreetDataset, SequentialDataset, SyntheticHeavyTailed
from .utils.io import find_project_root, load_yaml

ALGORITHMS: dict[str, type[OnlineLearner]] = {
    "ogd": OnlineGradientDescent,
    "adaptive_clip": AdaptiveClip,
    "robust_omd": RobustOMD,
    "scale_normalized_ogd": ScaleNormalizedOGD,
    "sn_ogd": ScaleNormalizedOGD,
}

DATASETS: dict[str, type[SequentialDataset]] = {
    "synthetic": SyntheticHeavyTailed,
    "jane": JaneStreetDataset,
}


def build_dataset(cfg: dict) -> SequentialDataset:
    """Build a :class:`SequentialDataset` from a dataset config dict.

    Parameters
    ----------
    cfg : dict
        Dataset section of an experiment config. Must contain a ``type`` key
        naming one of ``DATASETS``; remaining keys are passed to the dataset
        constructor verbatim.

    Returns
    -------
    SequentialDataset
        The constructed dataset.
    """
    cfg = dict(cfg)
    dataset_type = cfg.pop("type", None)
    if dataset_type is None or dataset_type not in DATASETS:
        raise ValueError(
            f"dataset config must contain a 'type' key with one of "
            f"{sorted(DATASETS)}, got {dataset_type!r}"
        )
    if dataset_type == "jane":
        data_dir = cfg.get("data_dir")
        if data_dir is not None:
            data_path = Path(data_dir)
            if not data_path.is_absolute():
                data_path = find_project_root() / data_path
            cfg["data_dir"] = data_path
        date_range = cfg.get("date_range")
        if isinstance(date_range, list):
            cfg["date_range"] = tuple(date_range)
    return DATASETS[dataset_type](**cfg)


def build_learner(cfg: dict, dim: int) -> OnlineLearner:
    """Build an :class:`OnlineLearner` from an algorithm config dict.

    Parameters
    ----------
    cfg : dict
        Algorithm section of an experiment config. Must contain a ``name``
        key naming one of ``ALGORITHMS``; remaining keys are passed to the
        learner constructor verbatim.
    dim : int
        Feature dimension, injected as the learner's ``dim`` argument.

    Returns
    -------
    OnlineLearner
        The constructed learner.
    """
    cfg = dict(cfg)
    name = cfg.pop("name", None)
    if name is None or name not in ALGORITHMS:
        raise ValueError(
            f"algorithm config must contain a 'name' key with one of "
            f"{sorted(ALGORITHMS)}, got {name!r}"
        )
    return ALGORITHMS[name](dim=dim, **cfg)


def apply_max_steps(dataset_cfg: dict, max_steps: int | None) -> dict:
    """Return a copy of ``dataset_cfg`` with the stream length capped.

    For synthetic datasets this caps ``n_steps``; for the Jane Street dataset
    it caps ``max_rows``. A falsy ``max_steps`` leaves the config unchanged.
    """
    cfg = dict(dataset_cfg)
    if not max_steps:
        return cfg
    dataset_type = cfg.get("type")
    if dataset_type == "synthetic":
        existing = cfg.get("n_steps")
        cfg["n_steps"] = int(max_steps) if existing is None else min(int(existing), int(max_steps))
    elif dataset_type == "jane":
        existing = cfg.get("max_rows")
        cfg["max_rows"] = int(max_steps) if existing is None else min(int(existing), int(max_steps))
    return cfg


def load_experiment_config(path: str | Path) -> dict:
    """Load an experiment YAML config and validate its required keys.

    Raises
    ------
    ValueError
        If the config is missing the ``dataset`` or ``algorithm`` key.
    """
    cfg = load_yaml(path)
    missing = [key for key in ("dataset", "algorithm") if key not in cfg]
    if missing:
        raise ValueError(f"experiment config {path} is missing required keys: {missing}")
    return cfg
