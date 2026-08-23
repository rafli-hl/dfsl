"""Ledger C-10 -- a stream-comparable divergence criterion.

Registered in ``experiment_matrix.yaml`` (sixth document, direction C10C) as
``kind: INSTRUMENT_CONSTRUCTION``. Acceptance tests live in
``research_c10c_validate.py``; this module is only the definition.

Why the inherited criteria had to be replaced
---------------------------------------------
``research_windows_replication._diverged`` fires when peak rolling weighted squared error
exceeds **50**, a level calibrated to Jane's standardized targets. On a Student-t(1.5)
stream the target has infinite variance and that statistic is ~34 600 for *any* predictor,
including the zero predictor, so the rule fires on everything. ``research_crypto_algorithms``
uses **1e3** and fires on nothing, even at ``P = 128``. A state-based alternative is worse
than either: the step is bounded by ``(lr/sqrt(k))*M``, so ``||w_T|| <= 2*lr*M*sqrt(T)`` --
exactly what ``thm:stability`` guarantees -- and no state threshold can discriminate among
capped configurations at all.

A third non-comparability hides inside the first: the inherited rolling window is a fixed
2000 steps, which is 1.3% of a Jane window, 33% of a crypto window and 10% of a synthetic
stream. Here it is a *fraction* of the stream.

The criterion
-------------
Everything is measured against the best constant predictor **on the same window**, so no
per-stream constant survives::

    c*     = weighted mean of y            (the best constant under weighted squared loss)
    L      = weighted MSE of the learner   /  weighted MSE of c*
    Ppeak  = peak rolling weighted SE of the learner / that of c*

    diverged  <=>  L >= 2   or   Ppeak >= kappa          (kappa = 10)

Read: divergent if the learner is at least twice as bad as doing nothing overall, or if its
worst local stretch is an order of magnitude worse than doing nothing there. The first
clause is the scale-free half of the inherited rule, restated against the best constant
rather than against zero. ``kappa`` is a dimensionless multiple, not a loss level.
"""

from __future__ import annotations

import numpy as np

KAPPA_DEFAULT = 10.0
L_RATIO_LIMIT = 2.0
WINDOW_FRACTION = 10        # rolling window = T / WINDOW_FRACTION
WINDOW_MIN = 100


def rolling_window(n: int) -> int:
    """Rolling window as a fraction of the stream, never below WINDOW_MIN."""
    return max(WINDOW_MIN, int(n // WINDOW_FRACTION))


def best_constant(y, wts) -> float:
    """Best constant predictor under weighted squared loss: the weighted mean of y."""
    sw = float(np.sum(wts))
    return float(np.sum(wts * y) / sw) if sw > 0 else 0.0


def _weighted_mse(y, preds, wts) -> float:
    e = wts * (preds - y) ** 2
    e = np.where(np.isfinite(e), np.minimum(e, 1e300), 1e300)
    sw = float(np.sum(wts))
    return float(np.sum(e) / sw) if sw > 0 else float("inf")


def _peak_rolling(y, preds, wts, win) -> float:
    e = wts * (preds - y) ** 2
    e = np.where(np.isfinite(e), np.minimum(e, 1e300), 1e300)
    w = max(1, min(win, e.size))
    return float(np.max(np.convolve(e, np.ones(w) / w, mode="valid")))


def relative_divergence(y, preds, wts, kappa: float = KAPPA_DEFAULT) -> dict:
    """Classify one run. Returns the two ratios and the verdict.

    Both ratios are dimensionless: rescaling y, or moving to a stream with a different
    target variance or tail index, leaves them unchanged in a way an absolute threshold
    cannot be. A non-finite ratio counts as divergence.
    """
    y = np.asarray(y, float)
    preds = np.asarray(preds, float)
    wts = np.asarray(wts, float)
    win = rolling_window(y.size)
    c = best_constant(y, wts)
    ref = np.full(y.shape, c)

    L_model, L_ref = _weighted_mse(y, preds, wts), _weighted_mse(y, ref, wts)
    P_model, P_ref = _peak_rolling(y, preds, wts, win), _peak_rolling(y, ref, wts, win)

    # A degenerate window (constant y) has no reference scale; nothing can be judged.
    if not np.isfinite(L_ref) or L_ref <= 0 or not np.isfinite(P_ref) or P_ref <= 0:
        return {"diverged": False, "degenerate_reference": True,
                "L_ratio": float("nan"), "P_ratio": float("nan"),
                "L_model": L_model, "L_ref": L_ref, "window": win}

    L_ratio, P_ratio = L_model / L_ref, P_model / P_ref
    bad = (not np.isfinite(L_ratio)) or (not np.isfinite(P_ratio))
    diverged = bool(bad or L_ratio >= L_RATIO_LIMIT or P_ratio >= kappa)
    return {"diverged": diverged, "degenerate_reference": False,
            "L_ratio": float(L_ratio), "P_ratio": float(P_ratio),
            "by_L": bool(np.isfinite(L_ratio) and L_ratio >= L_RATIO_LIMIT),
            "by_P": bool(np.isfinite(P_ratio) and P_ratio >= kappa),
            "L_model": L_model, "L_ref": L_ref, "window": win}


def diverged(y, preds, wts, kappa: float = KAPPA_DEFAULT) -> bool:
    """Boolean form, drop-in for the inherited _diverged(y, preds, wts) signature."""
    return relative_divergence(y, preds, wts, kappa)["diverged"]
