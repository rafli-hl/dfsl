"""Synthetic streams with KNOWN, controlled (sigma_t, p_t): does regret scale as
T^{1/p}, as Theorem 3.2 (Theorem D.2 in the appendix) predicts, and how does it
depend on the path length P_T?

This is the experiment that directly tests the theorem (the Jane Street runs measure
R^2 and stability, not regret scaling). It is fully self-contained -- no external data.

Setup: online linear regression, loss (<w,x> - y)^2, x ~ N(0, I_d),
y_t = <u_t, x_t> + eps_t, with eps_t symmetric Student-t of tail index p (so the
gradient has a finite q-th moment for q < p) scaled by sigma. Regret is measured
against the true comparator u_t (so the comparator loss is the noise floor eps_t^2).
Learners are seed-batched (vectorised over seeds) for speed.

Methods: OGD, normalized-GD (g/||g||), fixed-tau clip, scale-dependent clip
(tau_t = c * running scale), and SN-OMD (clip(g/s_t, M), predictable winsorised-EMA s_t).

Usage:  python scripts/research_synthetic.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "research"
FIG = ROOT / "paper" / "figures"


def student_t(rng, p, shape):
    """Symmetric Student-t with tail index p (nu=p dof), unit-ish scale."""
    return rng.standard_t(df=p, size=shape)


def run_methods(rng, T, d, p, sigma, u_of_t, eta):
    """Seed-batched online run. Returns dict method -> cumulative regret array (T,).

    All learners share the same stream. State is (S, d); we accumulate the
    per-step loss-regret (loss_t - eps_t^2) summed over seeds, then divide by S.
    """
    S = 400  # seeds averaged over
    W = {m: np.zeros((S, d)) for m in METHODS}
    s_ema = {m: np.ones(S) for m in ("scaleclip", "snomd")}  # predictable scale trackers
    creg = {m: np.zeros(T) for m in METHODS}
    run = {m: 0.0 for m in METHODS}
    decay, winsor, M, cclip = 0.99, 8.0, 5.0, 3.0

    for t in range(T):
        x = rng.standard_normal((S, d))
        u = u_of_t(t)                                   # (d,)
        eps = sigma * student_t(rng, p, S)              # heavy-tailed noise
        y = x @ u + eps
        floor = eps * eps                               # comparator loss
        inv_sqrt_t = 1.0 / np.sqrt(t + 1.0)
        for m in METHODS:
            lr = eta[m] * inv_sqrt_t
            pred = np.einsum("sd,sd->s", W[m], x)
            resid = pred - y
            g = 2.0 * resid[:, None] * x                # (S, d)
            gn = np.linalg.norm(g, axis=1) + 1e-12
            if m == "ogd":
                step = g
            elif m == "normgd":
                step = g / gn[:, None]
            elif m == "fixedclip":
                step = g * np.minimum(1.0, TAU / gn)[:, None]
            elif m == "scaleclip":
                tau = cclip * s_ema[m]
                step = g * np.minimum(1.0, tau / gn)[:, None]
                s_ema[m] = decay * s_ema[m] + (1 - decay) * np.minimum(gn, winsor * s_ema[m])
            elif m == "snomd":
                v = g / s_ema[m][:, None]               # predictable s_t
                vn = np.linalg.norm(v, axis=1) + 1e-12
                step = v * np.minimum(1.0, M / vn)[:, None]
                s_ema[m] = decay * s_ema[m] + (1 - decay) * np.minimum(gn, winsor * s_ema[m])
            W[m] = W[m] - lr * step
            reg_t = float(np.mean(resid * resid - floor))
            run[m] += reg_t
            creg[m][t] = run[m]
    return creg


METHODS = ["ogd", "normgd", "fixedclip", "scaleclip", "snomd"]
LABELS = {"ogd": "OGD", "normgd": "normalized-GD", "fixedclip": "fixed-$\\tau$ clip",
          "scaleclip": "scale-dep. clip", "snomd": "SN-OMD"}
TAU = 20.0
ETA = {"ogd": 0.02, "normgd": 0.3, "fixedclip": 0.05, "scaleclip": 0.1, "snomd": 0.3}


def _msweep_one(rng, T, d, p, sigma, u, eta, M, const_step):
    """Return the per-seed steady-state excess loss (array of length S)."""
    S = 250
    decay, winsor = 0.99, 8.0
    W = np.zeros((S, d))
    s = np.ones(S)
    acc = np.zeros(S)
    cnt = 0
    for t in range(T):
        x = rng.standard_normal((S, d))
        eps = sigma * student_t(rng, p, S)
        y = x @ u + eps
        step_scale = eta if const_step else eta / np.sqrt(t + 1.0)
        pred = np.einsum("sd,sd->s", W, x)
        resid = pred - y
        g = 2.0 * resid[:, None] * x
        gn = np.linalg.norm(g, axis=1) + 1e-12
        v = g / s[:, None]
        vn = np.linalg.norm(v, axis=1) + 1e-12
        step = v * np.minimum(1.0, M / vn)[:, None]
        W = W - step_scale * step
        s = decay * s + (1 - decay) * np.minimum(gn, winsor * s)
        if t >= T // 2:
            acc += resid * resid - eps * eps
            cnt += 1
    return acc / cnt  # (S,) per-seed mean excess loss


def run_msweep(rng, T, d, p, sigma, u, M_grid, eta_grid, const_step=True):
    """SN-OMD steady-state excess loss vs cap M, each M at its OWN best step.

    M->0 is normalized-GD (s_t cancels, step ~ eta*M*g/||g||); M->inf is
    scale-adaptive OGD (step ~ eta*g/s_t, no truncation). We tune eta per M,
    because M and eta both scale the step: a fixed eta would conflate the cap
    with the learning rate and trivially favour small M. Returns, per M, the
    (mean, sem) steady-state excess loss across seeds at the best eta, so the
    figure carries a seed-noise band.
    """
    out = {}
    for M in M_grid:
        best_mean, best_arr = np.inf, None
        for eta in eta_grid:
            arr = _msweep_one(rng, T, d, p, sigma, u, eta, M, const_step)
            m = float(np.mean(arr))
            if np.isfinite(m) and m < best_mean:
                best_mean, best_arr = m, arr
        sem = float(np.std(best_arr) / np.sqrt(best_arr.size)) if best_arr is not None else np.nan
        out[M] = (best_mean, sem)
    return out


def fit_exponent(T_grid, reg):
    m = (reg > 0) & np.isfinite(reg)
    if m.sum() < 5:
        return float("nan")
    lx, ly = np.log(T_grid[m]), np.log(reg[m])
    return float(np.polyfit(lx, ly, 1)[0])


def main():
    rng = np.random.default_rng(0)
    d = 5
    T = 20000
    u_static = rng.standard_normal(d)
    u_static /= np.linalg.norm(u_static)

    print("=" * 72)
    print("TEST 1 -- regret scaling vs the predicted T^{1/p} (static comparator)")
    print("=" * 72)
    rows = []
    grid = np.unique(np.geomspace(200, T - 1, 40).astype(int))
    fig, axes = plt.subplots(1, 3, figsize=(6.75, 2.3), sharex=True, sharey=True)
    for ax, p in zip(axes, (1.3, 1.5, 2.0)):
        creg = run_methods(rng, T, d, p, 1.0, lambda t: u_static, ETA)
        print(f"\n  p = {p}   (predicted exponent 1/p = {1/p:.3f})")
        for m in METHODS:
            e = fit_exponent(grid, creg[m][grid])
            print(f"    {LABELS[m]:20s} fitted exponent = {e:.3f}")
            rows.append({"test": "Tp", "p": p, "method": m, "exponent": e,
                         "pred_1_over_p": 1 / p, "regret_T": float(creg[m][-1])})
            ax.plot(grid, np.maximum(creg[m][grid], 1e-9), lw=1.0, label=LABELS[m])
        ax.plot(grid, grid ** (1 / p) * (creg["snomd"][grid][-1] / grid[-1] ** (1 / p)),
                "k--", lw=0.8, label="$T^{1/p}$ ref")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_title(f"$p={p}$"); ax.set_xlabel("T")
    axes[0].set_ylabel("cumulative regret")
    axes[0].legend(fontsize=5.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / "fig5_synthetic.png", dpi=300)
    plt.close(fig)
    print(f"\n  wrote {FIG.relative_to(ROOT)}/fig5_synthetic.png")

    print("\n" + "=" * 72)
    print("TEST 2 -- dynamic regret vs path length P_T (p=1.5, N jumps)")
    print("=" * 72)
    for njumps in (0, 4, 16, 64):
        def u_of_t(t, nj=njumps):
            if nj == 0:
                return u_static
            seg = min(int(t / (T / nj)), nj)
            g = np.random.default_rng(1000 + seg).standard_normal(d)
            return g / np.linalg.norm(g)
        creg = run_methods(rng, T, d, 1.5, 1.0, u_of_t, ETA)
        P_T = njumps * np.sqrt(2.0)  # ~ per-jump comparator move (unit vectors)
        print(f"  P_T~{P_T:6.1f} (jumps={njumps:2d})   "
              + "  ".join(f"{LABELS[m].split()[0]}={creg[m][-1]:.0f}" for m in METHODS))
        for m in METHODS:
            rows.append({"test": "PT", "p": 1.5, "method": m, "njumps": njumps,
                         "P_T": P_T, "regret_T": float(creg[m][-1])})
    # fit dynamic regret vs P_T exponent for SN-OMD (predicted ~0.5 if sqrt(D P_T) binds)
    ptsub = [r for r in rows if r["test"] == "PT" and r["method"] == "snomd" and r["P_T"] > 0]
    px = np.log(np.array([r["P_T"] for r in ptsub]))
    py = np.log(np.array([r["regret_T"] for r in ptsub]))
    print(f"\n  SN-OMD dynamic-regret vs P_T: fitted exponent = {np.polyfit(px, py, 1)[0]:.3f} "
          f"(0.5 = sqrt(P_T), 1.0 = linear)")

    print("\n" + "=" * 72)
    print("TEST 3 -- the cap M interpolates normGD (M->0) and scale-adaptive OGD (M->inf)")
    print("=" * 72)
    print("  heavy tail p=1.5, static reachable u*, constant step (exposes normGD)")
    M_grid = np.array([0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 100.0])
    eta_grid = np.array([0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5])
    ms = run_msweep(rng, 12000, d, 1.5, 1.0, u_static, M_grid, eta_grid, const_step=True)
    means = {M: ms[M][0] for M in M_grid}
    sems = {M: ms[M][1] for M in M_grid}
    best_M = min(means, key=means.get)
    for M in M_grid:
        tag = "  <- normGD end" if M == M_grid[0] else ("  <- OGD end" if M == M_grid[-1] else
              ("  <- best" if M == best_M else ""))
        print(f"    M={M:6.2f}   excess loss = {means[M]:.4f} +/- {sems[M]:.4f}{tag}")
        rows.append({"test": "Msweep", "p": 1.5, "M": float(M),
                     "excess_loss": float(means[M]), "sem": float(sems[M])})
    interior = best_M not in (M_grid[0], M_grid[-1])
    print(f"\n  best M = {best_M} -> {'INTERIOR optimum (finite cap wins)' if interior else 'BOUNDARY'}")

    fig, ax = plt.subplots(figsize=(3.3, 2.3))
    ax.errorbar(M_grid, [means[M] for M in M_grid], yerr=[sems[M] for M in M_grid],
                fmt="o-", color="#1f77b4", lw=1.2, ms=3.5, capsize=2, elinewidth=0.7)
    ax.axvline(best_M, color="#d62728", ls="--", lw=0.8)
    ax.set_xscale("log"); ax.set_xlabel("cap $M$"); ax.set_ylabel("steady-state excess loss")
    ax.set_title("normGD ($M{\\to}0$) $-$ SN-OMD $-$ OGD ($M{\\to}\\infty$)", fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig6_msweep.png", dpi=300); plt.close(fig)
    print(f"  wrote {FIG.relative_to(ROOT)}/fig6_msweep.png")

    pl.DataFrame(rows).write_csv(OUT / "synthetic_regret.csv")
    print(f"\n  wrote {OUT.relative_to(ROOT)}/synthetic_regret.csv")


if __name__ == "__main__":
    main()
