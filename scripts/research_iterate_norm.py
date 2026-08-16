"""Directly measure the iterate norm ||w_t|| that Theorem (stability) bounds.

The paper's headline stability evidence (Table 1/Table replication divergence
counts, peak rolling loss) is a *loss* quantity, whereas ``thm:stability`` bounds
the *iterate norm* ||w_t|| <= ||w_1|| + 2 M eta sqrt(t) on R^d. For the bounded-
feature linear task the two are equivalent (a prediction w_t . x_t with bounded
||x_t|| blows up iff ||w_t|| does), but the paper never logs ||w_t|| itself. This
script closes that gap: it streams one Jane-Street window through the *reference*
learners (``dfsl.algorithms``) and records ||w_t|| at every step, so the object the
theorem controls is measured head-on.

For each method it reports the log-log growth exponent beta (||w_t|| ~ t^beta;
the theorem predicts beta <= 1/2 for any capped scale-free member) and, for the
capped SN-OMD, checks ||w_t|| stays under the theorem's envelope 2 M eta sqrt(t)
at every step. A figure overlays the traces against that sqrt(t) envelope.

Usage::

    python scripts/research_iterate_norm.py                       # window 1, lr=2
    python scripts/research_iterate_norm.py --lo 600 --hi 720      # a different window
    python scripts/research_iterate_norm.py --lr 2 --rows 150000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402
from dfsl.algorithms.base import OnlineGradientDescent  # noqa: E402
from dfsl.algorithms.scale_normalized import ScaleNormalizedOGD  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"
FIGS = ROOT / "paper" / "figures"


def build(name: str, dim: int, lr: float):
    """The three reference learners spanning the cap frontier (as in tab:replication)."""
    if name == "SN-OMD (M=5)":
        return ScaleNormalizedOGD(dim, learning_rate=lr, cap=5.0)
    if name == "Scale-adaptive OGD (M->inf)":
        return ScaleNormalizedOGD(dim, learning_rate=lr, cap=1e9)
    if name == "OGD":
        return OnlineGradientDescent(dim, learning_rate=lr)
    raise ValueError(name)


def run_norm_trace(learner, X, y, w):
    """Stream the window through ``learner``; return per-step (||w_t||, loss)."""
    n = X.shape[0]
    wnorm = np.empty(n, dtype=np.float64)
    loss = np.empty(n, dtype=np.float64)
    for i in range(n):
        loss[i] = learner.update(X[i], float(y[i]), float(w[i]))
        wn = float(np.linalg.norm(learner.weights))
        wnorm[i] = wn if np.isfinite(wn) else np.inf
    return wnorm, loss


def growth_exponent(wnorm: np.ndarray, t0: int = 1000) -> float:
    """Least-squares slope of log ||w_t|| vs log t over the finite tail t >= t0."""
    n = wnorm.size
    t = np.arange(1, n + 1, dtype=np.float64)
    m = (t >= t0) & np.isfinite(wnorm) & (wnorm > 0)
    if m.sum() < 10:
        return float("nan")
    b, _ = np.polyfit(np.log(t[m]), np.log(wnorm[m]), 1)
    return float(b)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lo", type=int, default=0)
    ap.add_argument("--hi", type=int, default=120)
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--lr", type=float, default=2.0, help="shared competitive rate")
    args = ap.parse_args()

    ds = JaneStreetDataset(date_range=(args.lo, args.hi), max_rows=args.rows, standardize=True)
    X, y, w = ds.X, ds.y, ds.weights
    dim = X.shape[1]
    n = X.shape[0]
    t = np.arange(1, n + 1, dtype=np.float64)
    print(f"window date[{args.lo},{args.hi})  n={n}  dim={dim}  lr={args.lr}")

    methods = ["SN-OMD (M=5)", "Scale-adaptive OGD (M->inf)", "OGD"]
    traces: dict[str, np.ndarray] = {}
    RES.mkdir(parents=True, exist_ok=True)
    rows_out = []
    for name in methods:
        learner = build(name, dim, args.lr)
        wnorm, loss = run_norm_trace(learner, X, y, w)
        traces[name] = wnorm
        beta = growth_exponent(wnorm)
        finite = wnorm[np.isfinite(wnorm)]
        final = float(wnorm[-1])
        peak = float(np.max(finite)) if finite.size else float("inf")
        n_nonfinite = int((~np.isfinite(wnorm)).sum())
        print(f"  {name:28s} beta(loglog)={beta:+.3f}  final||w||={final:.3g}  "
              f"peak||w||={peak:.3g}  nonfinite_steps={n_nonfinite}")
        for i in range(0, n, 50):  # downsample the CSV
            rows_out.append((name, int(t[i]), float(wnorm[i]), float(loss[i])))

    # Theorem envelope for the capped member: ||w_t|| <= ||w_1|| + 2 M eta sqrt(t),
    # here w_1 = 0, M = 5, eta = lr.  Verify SN-OMD never breaches it.
    M_sn, eta = 5.0, args.lr
    envelope = 2.0 * M_sn * eta * np.sqrt(t)
    sn = traces["SN-OMD (M=5)"]
    breaches = int(np.sum(np.isfinite(sn) & (sn > envelope + 1e-9)))
    print(f"  [theorem check] SN-OMD ||w_t|| <= 2*M*eta*sqrt(t): "
          f"breaches={breaches}/{n}  (envelope_final={envelope[-1]:.3g}, sn_final={sn[-1]:.3g})")

    import csv
    csv_path = RES / "iterate_norm.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        wri = csv.writer(f)
        wri.writerow(["method", "t", "wnorm", "loss"])
        wri.writerows(rows_out)
    print(f"  wrote {csv_path}")

    # ---- figure: ||w_t|| vs t (log-log) with the sqrt(t) envelope ----
    FIGS.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(5.2, 3.6))
    colors = {"SN-OMD (M=5)": "C0", "Scale-adaptive OGD (M->inf)": "C3", "OGD": "C1"}
    for name in methods:
        yv = np.where(np.isfinite(traces[name]), traces[name], np.nan)
        plt.loglog(t, yv, color=colors[name], lw=1.3, label=name)
    plt.loglog(t, envelope, "k--", lw=1.0, label=r"theorem bound $2M\eta\sqrt{t}$ (M=5)")
    # Clip the y-axis so the capped trace, the envelope, and the onset of divergence
    # are legible; catastrophically divergent traces (OGD ~1e150) exit the top.
    plt.ylim(3e-1, 1e8)
    plt.xlabel("step $t$")
    plt.ylabel(r"iterate norm $\|w_t\|$")
    plt.legend(fontsize=7, loc="upper left")
    plt.tight_layout()
    fig_path = FIGS / "fig8_iterate_norm.png"
    plt.savefig(fig_path, dpi=150)
    print(f"  wrote {fig_path}")


if __name__ == "__main__":
    main()
