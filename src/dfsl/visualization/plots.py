"""Matplotlib figure helpers for regret, loss, and breakdown plots.

These helpers never call ``plt.show()``; figures are returned to the caller
and optionally saved (and closed) via :func:`save_figure`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.figure import Figure

from ..utils.io import ensure_dir

__all__ = ["save_figure", "plot_regret_curves", "plot_loss_curves", "plot_breakdown"]


def save_figure(fig: Figure, path: str | Path, dpi: int = 200) -> Path:
    """Save a figure to disk, creating parent directories, then close it.

    Parameters
    ----------
    fig : Figure
        The figure to save.
    path : str or Path
        Destination file path.
    dpi : int
        Output resolution.

    Returns
    -------
    Path
        The path the figure was written to.
    """
    out = Path(path)
    ensure_dir(out.parent)
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    return out


def plot_regret_curves(
    curves: dict[str, np.ndarray],
    title: str = "Cumulative regret",
    path: str | Path | None = None,
) -> Figure:
    """Plot one cumulative-regret curve per learner.

    Parameters
    ----------
    curves : dict[str, np.ndarray]
        Mapping from learner name to its cumulative regret curve.
    title : str
        Figure title.
    path : str, Path, or None
        If given, the figure is saved there via :func:`save_figure`.

    Returns
    -------
    Figure
        The created figure.
    """
    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    for name, curve in curves.items():
        curve = np.asarray(curve, dtype=np.float64)
        ax.plot(np.arange(1, curve.size + 1), curve, label=name)
    ax.set_xlabel("step")
    ax.set_ylabel("cumulative regret")
    ax.set_title(title)
    ax.legend()
    if path is not None:
        save_figure(fig, path)
    return fig


def plot_loss_curves(
    losses: dict[str, np.ndarray],
    window: int = 500,
    title: str = "Rolling mean loss",
    path: str | Path | None = None,
) -> Figure:
    """Plot rolling-mean per-step losses for one or more learners.

    The rolling mean is computed with
    ``np.convolve(x, np.ones(w) / w, mode="valid")`` where ``w`` is
    ``window`` clamped to the series length.

    Parameters
    ----------
    losses : dict[str, np.ndarray]
        Mapping from learner name to its per-step loss sequence.
    window : int
        Rolling-mean window size.
    title : str
        Figure title.
    path : str, Path, or None
        If given, the figure is saved there via :func:`save_figure`.

    Returns
    -------
    Figure
        The created figure.
    """
    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    for name, series in losses.items():
        x = np.asarray(series, dtype=np.float64)
        w = max(1, min(int(window), x.size))
        smoothed = np.convolve(x, np.ones(w) / w, mode="valid")
        ax.plot(np.arange(w - 1, x.size), smoothed, label=name)
    ax.set_xlabel("step")
    ax.set_ylabel("rolling mean loss")
    ax.set_title(title)
    ax.legend()
    if path is not None:
        save_figure(fig, path)
    return fig


def plot_breakdown(
    df: pl.DataFrame,
    x: str = "fraction",
    ys: Sequence[str] = ("mse", "weighted_r2"),
    title: str = "Breakdown under contamination",
    path: str | Path | None = None,
) -> Figure:
    """Plot metric curves from a breakdown-experiment frame.

    Parameters
    ----------
    df : pl.DataFrame
        Output of :func:`dfsl.evaluation.breakdown_experiment`.
    x : str
        Column used for the x-axis (contamination fraction).
    ys : Sequence[str]
        Metric columns to plot, one line each.
    title : str
        Figure title.
    path : str, Path, or None
        If given, the figure is saved there via :func:`save_figure`.

    Returns
    -------
    Figure
        The created figure.
    """
    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    x_values = df[x].to_numpy()
    for col in ys:
        ax.plot(x_values, df[col].to_numpy(), marker="o", label=col)
    ax.set_xlabel(x)
    ax.set_ylabel("metric value")
    ax.set_title(title)
    ax.legend()
    if path is not None:
        save_figure(fig, path)
    return fig
