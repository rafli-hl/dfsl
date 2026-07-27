"""Loguru-based logger configuration (only configured when explicitly requested)."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def get_logger(level: str = "INFO", log_file: str | Path | None = None):
    """Configure and return the loguru logger.

    Removes existing sinks, adds a stderr sink at ``level`` and, if
    ``log_file`` is given, an additional file sink at the same level.

    Parameters
    ----------
    level : str
        Minimum log level for all sinks (e.g. "INFO", "DEBUG").
    log_file : str, Path or None
        Optional path for a file sink; parent directories are created.

    Returns
    -------
    loguru.Logger
        The configured global loguru logger.
    """
    logger.remove()
    logger.add(sys.stderr, level=level)
    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(log_path, level=level)
    return logger