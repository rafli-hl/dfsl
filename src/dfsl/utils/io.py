"""File-system and serialization helpers (YAML/JSON, project-root discovery)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def find_project_root(
    start: Path | None = None,
    markers: tuple[str, ...] = ("pyproject.toml", ".git"),
) -> Path:
    """Walk upward from ``start`` until a directory containing a marker is found.

    Parameters
    ----------
    start : Path or None
        Directory to start from; defaults to the current working directory.
    markers : tuple of str
        File or directory names that identify the project root.

    Returns
    -------
    Path
        The first ancestor directory containing one of the markers.

    Raises
    ------
    FileNotFoundError
        If no ancestor directory contains any of the markers.
    """
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in markers):
            return candidate
    raise FileNotFoundError(
        f"Could not find project root: walked up from {current!s} without finding "
        f"any of the markers {markers!r}. Run from inside the repository or pass "
        f"an explicit start path."
    )


def ensure_dir(path: str | Path) -> Path:
    """Create ``path`` (and parents) if needed and return it as a Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_yaml(path: str | Path) -> dict:
    """Load a YAML file with ``yaml.safe_load``; an empty file yields ``{}``."""
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {} if data is None else data


def save_yaml(obj: dict, path: str | Path) -> Path:
    """Write ``obj`` to ``path`` as YAML (unsorted keys), creating parent dirs."""
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False)
    return p


def load_json(path: str | Path) -> Any:
    """Load a JSON file and return the decoded object."""
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj: Any, path: str | Path, indent: int = 2) -> Path:
    """Write ``obj`` to ``path`` as JSON, creating parent dirs; return the Path."""
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent)
    return p