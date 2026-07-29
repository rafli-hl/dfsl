"""Scale-normalized online gradient descent (SN-OGD).

Decouples the update step from the (drifting, unknown) gradient scale: instead of
*clipping* the gradient to a scale-dependent threshold ``tau = c * scale`` (whose
step magnitude then scales with the drifting regime scale and can diverge under
nonstationarity), SN-OGD *normalizes* the gradient by a tracked robust scale and
caps it at a scale-free constant ``M``:

    ghat_t = clip( g_t / s_t , M ),     w_{t+1} = Pi( w_t - (lr / sqrt(t)) * ghat_t ).

Because ``||ghat_t|| <= M`` deterministically, the iterate cannot blow up for any
learning rate or realization -- the step no longer inherits the scale drift. See
``results/research/THEORY_SNOGD.md`` for the regret theory and
``results/research/FINDINGS.md`` (Finding 10) for the empirical validation.

Note: because the step is scale-invariant, ``learning_rate`` is in scale-normalized
units and its useful range is much larger (order 1) than for plain OGD.
"""

from __future__ import annotations

import numpy as np

from dfsl.algorithms.base import OnlineGradientDescent
from dfsl.preprocessing.normalize import OnlineScaleTracker, TwoTimescaleScaleTracker


def _resolve_tracker(spec, scale_decay: float, scale_winsor: float):
    """Build the scale tracker from ``spec``.

    ``spec`` may be ``None``/``"ema"`` (the default robustified-EMA tracker built
    from ``scale_decay``/``scale_winsor``), ``"two_timescale"`` (the peak-hold
    envelope with its defaults), or any object exposing ``.scale`` and ``.step``.
    """
    if spec is None or spec == "ema":
        return OnlineScaleTracker(decay=scale_decay, winsor=scale_winsor)
    if spec == "two_timescale":
        return TwoTimescaleScaleTracker()
    if hasattr(spec, "scale") and hasattr(spec, "step"):
        return spec
    raise ValueError(
        f"scale_tracker must be 'ema', 'two_timescale', or a tracker object, got {spec!r}"
    )


class ScaleNormalizedOGD(OnlineGradientDescent):
    """OGD with a scale-invariant, constant-capped gradient step.

    Parameters
    ----------
    dim : int
        Feature dimension.
    learning_rate : float
        Step-size scale for the ``lr / sqrt(t)`` schedule. In scale-normalized
        units (order 1 is typical), not comparable to plain-OGD learning rates.
    cap : float
        Scale-free cap ``M`` on the norm of the normalized gradient; bounds the
        per-step move and hence guarantees non-divergence.
    scale_tracker : None, str, or object
        Which scale tracker to use: ``None``/``"ema"`` (default, the robustified-EMA
        :class:`~dfsl.preprocessing.OnlineScaleTracker`, validated in Finding 10),
        ``"two_timescale"`` (the peak-hold envelope
        :class:`~dfsl.preprocessing.TwoTimescaleScaleTracker` analyzed in the theory),
        or any object exposing ``.scale`` and ``.step``.
    scale_decay, scale_winsor : float
        Parameters of the default EMA tracker (ignored if ``scale_tracker`` is
        ``"two_timescale"`` or an object).
    projection_radius : float or None
        Optional Euclidean projection radius (inherited from OGD).
    seed : int or None
        Unused placeholder for interface compatibility.
    """

    def __init__(
        self,
        dim: int,
        learning_rate: float = 1.0,
        cap: float = 10.0,
        scale_tracker=None,
        scale_decay: float = 0.99,
        scale_winsor: float = 8.0,
        projection_radius: float | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(
            dim=dim,
            learning_rate=learning_rate,
            projection_radius=projection_radius,
            seed=seed,
        )
        if cap <= 0.0:
            raise ValueError(f"cap must be positive, got {cap}")
        self.cap = cap
        self._tracker = _resolve_tracker(scale_tracker, scale_decay, scale_winsor)

    def _clip_gradient(self, g: np.ndarray) -> np.ndarray:
        """Return the scale-normalized, constant-capped gradient ``clip(g/s, M)``.

        Overflow-safe: the returned gradient always has norm ``<= cap`` and finite
        entries, so the update can never diverge even when ``g`` is so large that
        its Euclidean norm overflows to ``inf`` (finite entries, non-finite norm).
        """
        with np.errstate(over="ignore", invalid="ignore"):
            gmax = float(np.max(np.abs(g)))
            if not np.isfinite(gmax):
                return np.zeros_like(g)  # inf/nan entries: skip this step safely
            if gmax == 0.0:
                return g
            unit = g / gmax  # O(1) entries; norm below cannot overflow
            unit_norm = float(np.linalg.norm(unit))
            norm = gmax * unit_norm  # overflow-safe ||g||
            s = self._tracker.step(norm)
            ghat = g / s
            ghat_norm = float(np.linalg.norm(ghat))
            if np.isfinite(ghat_norm) and ghat_norm <= self.cap:
                return ghat
            # ||g/s|| exceeds the cap (or overflowed): step exactly at the cap in
            # the (overflow-safe) gradient direction.
            return unit * (self.cap / unit_norm)

    @property
    def scale(self) -> float:
        """Current tracked gradient-norm scale ``s_t``."""
        return self._tracker.scale
