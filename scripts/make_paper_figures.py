"""Build the definitive ICML figure set (PNG) for the corrected SN-OGD story.

Regenerates a small, coherent, uniformly-styled set from the saved research
artifacts in results/research/ (no experiment re-run needed) into paper/figures/:

  fig1_problem.png    the problem: gradients are heavy-tailed (interaction) AND
                      nonstationary (tail index drifts below 2 across the record)
  fig2_mechanism.png  why scale-dependent clipping fails: the gradient scale drifts,
                      and a fixed-window adaptive threshold cannot both track and stay stable
  fig3_main.png       the result: SN-OGD attains the highest R^2 and never diverges,
                      across the whole learning-rate range
  fig4_tracker.png    discharging A1: a two-timescale tracker holds the lower bracket
                      at 100% with the smallest upward variation W_s

Also writes paper/figures/FIGURES.md (a manifest). All outputs are PNG at 300 dpi.

Usage::  python scripts/make_paper_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"
FIG = ROOT / "paper" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
TEXT_W = 6.75

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "cm",
        "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
        "legend.fontsize": 6.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "axes.linewidth": 0.6, "lines.linewidth": 1.2, "legend.frameon": False,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    }
)

# consistent per-method identity for fig3
ORDER = ["ogd", "normgd", "scale_adaptive", "sn_ogd"]
COLORS = {"ogd": "#d62728", "normgd": "#7f7f7f",
          "scale_adaptive": "#2ca02c", "sn_ogd": "#1f77b4"}
LABELS = {"ogd": "OGD (scale-dep.)", "normgd": r"normalized-GD ($M\to0$)",
          "scale_adaptive": r"scale-adaptive OGD ($M\to\infty$)", "sn_ogd": "SN-OMD (ours)"}
MARK = {"ogd": "o", "normgd": "s", "scale_adaptive": "D", "sn_ogd": "^"}


def _save(fig, name):
    fig.savefig(FIG / name)
    plt.close(fig)
    print(f"  wrote paper/figures/{name}")


def _ccdf(x, subsample=3000):
    a = np.sort(np.asarray(x, float))
    a = a[a > 0]
    surv = 1.0 - np.arange(a.size) / a.size
    if a.size > subsample:
        idx = np.unique(np.geomspace(1, a.size - 1, subsample).astype(int))
        a, surv = a[idx], surv[idx]
    return a, surv


def fig1_problem():
    g = np.load(RES / "gradnorm_at_wstar.npy")
    r = np.load(RES / "residual_at_wstar.npy")
    xn = np.load(RES / "featurenorm.npy")
    tails = pl.read_csv(RES / "intrinsic_gradient_tails.csv")
    alpha = {row["quantity"]: row["hill_alpha"] for row in tails.iter_rows(named=True)}
    daily = pl.read_csv(RES / "heavybudget_daily.csv").filter(pl.col("hill_alpha").is_finite())

    fig, ax = plt.subplots(1, 2, figsize=(TEXT_W, 2.5))
    a0 = ax[0]
    for lbl, arr, key, c in [
        (r"gradient $\|g\|$", g, "gradient_norm@w*", "#1f77b4"),
        (r"residual $|r|$", r, "residual@w*", "#2ca02c"),
        (r"feature $\|x\|$", xn, "feature_norm||x||", "#ff7f0e"),
    ]:
        v, s = _ccdf(arr / np.mean(arr))
        a0.plot(v, s, color=c, label=f"{lbl}: $\\hat\\alpha$={alpha[key]:.2f}")
    a0.set_xscale("log"); a0.set_yscale("log")
    a0.set_xlabel("value / mean"); a0.set_ylabel(r"survival $P(X\!\geq\!x)$")
    a0.set_title("(a) Heavy tail is an interaction effect")
    a0.legend(loc="lower left")

    a1 = ax[1]
    d = daily["date_id"].to_numpy(); al = daily["hill_alpha"].to_numpy()
    a1.plot(d, al, color="#2ca02c", marker="o", ms=2.2, lw=0.7)
    a1.axhline(2, color="#d62728", ls="--", lw=0.9); a1.axhline(4, color="k", ls=":", lw=0.7)
    below = al < 2
    a1.scatter(d[below], al[below], color="#d62728", s=13, zorder=5, label=r"$\hat\alpha<2$ (inf. var.)")
    a1.set_xlabel("trading day (full 1,699-day record)"); a1.set_ylabel(r"daily gradient Hill $\hat\alpha$")
    a1.set_title("(b) ...and nonstationary")
    a1.legend(loc="upper right", fontsize=6)
    _save(fig, "fig1_problem.png")


def fig2_mechanism():
    daily = pl.read_csv(RES / "nonstationarity_daily.csv").sort("date_id")
    tens = pl.read_csv(RES / "nonstationarity_threshold_tension.csv").sort("window")
    fig, ax = plt.subplots(1, 2, figsize=(TEXT_W, 2.5))

    a0 = ax[0]
    dd = daily["date_id"].to_numpy()
    a0.plot(dd, daily["median_gnorm"].to_numpy(), color="#1f77b4", marker="o", ms=2.2, label="median")
    a0.plot(dd, daily["p99_gnorm"].to_numpy(), color="#d62728", marker="^", ms=2.2, label="p99")
    a0.set_yscale("log"); a0.set_xlabel("trading day"); a0.set_ylabel(r"daily $\|g\|$ scale")
    a0.set_title("(a) Gradient scale drifts ~6$\\times$")
    a0.legend(loc="upper right")

    a1 = ax[1]
    W = tens["window"].to_numpy()
    a1.plot(W, tens["tau_dynamic_range_p95_p5"].to_numpy(), color="#9467bd", marker="o", label="threshold dynamic range")
    a1.set_xscale("log"); a1.set_xlabel(r"threshold window $W$")
    a1.set_ylabel(r"$\tau$ dynamic range (p95/p5)")
    a1.set_title("(b) A fixed clip threshold cannot win")
    a2 = a1.twinx()
    a2.plot(W, tens["clip_rate"].to_numpy(), color="#ff7f0e", marker="s", ls="--", label="clip rate")
    a2.set_ylabel("clip rate", color="#ff7f0e"); a2.tick_params(axis="y", labelcolor="#ff7f0e")
    a2.spines["top"].set_visible(False)
    a1.text(0.5, 0.92, "track $\\Rightarrow$ inherit swing;  smooth $\\Rightarrow$ lag",
            transform=a1.transAxes, ha="center", fontsize=6, color="#555555")
    _save(fig, "fig2_mechanism.png")


def fig3_main():
    # normalize_continuous.csv includes SN-OGD across its full (scale-invariant)
    # learning-rate range up to 2.0; continuous_stream.csv does not.
    df = pl.read_csv(RES / "normalize_continuous.csv")
    fig, ax = plt.subplots(1, 2, figsize=(TEXT_W, 2.6))
    a0 = ax[0]
    for n in ORDER:
        s = df.filter(pl.col("method") == n).sort("learning_rate")
        a0.plot(s["learning_rate"], s["weighted_r2"], color=COLORS[n], marker=MARK[n], ms=3.2, label=LABELS[n])
    a0.set_xscale("log"); a0.set_ylim(-0.10, 0.30); a0.axhline(0, color="k", lw=0.5)
    off = df.filter((pl.col("method") == "ogd") & (pl.col("weighted_r2") < -0.10))
    a0.scatter(off["learning_rate"].to_numpy(), np.full(off.height, -0.10),
               marker="v", color="#d62728", s=18, clip_on=False, zorder=6)
    a0.set_xlabel("learning rate"); a0.set_ylabel(r"weighted $R^2$")
    a0.set_title("(a) Accuracy vs. learning rate")
    a0.legend(loc="upper left")

    a1 = ax[1]
    for n in ORDER:
        s = df.filter(pl.col("method") == n).sort("learning_rate")
        a1.plot(s["learning_rate"], s["peak_rolling_loss"], color=COLORS[n], marker=MARK[n], ms=3.2)
    a1.set_xscale("log"); a1.set_yscale("log"); a1.axhspan(0, 6, color="#2ca02c", alpha=0.08)
    a1.text(0.97, 0.05, r"bounded ($\leq 6$)", fontsize=6, color="#2ca02c",
            ha="right", va="bottom", transform=a1.transAxes)
    a1.set_xlabel("learning rate"); a1.set_ylabel("peak rolling loss")
    a1.set_title("(b) Stability vs. learning rate")
    _save(fig, "fig3_main.png")


def fig4_tracker():
    t = pl.read_csv(RES / "tracker_a1.csv")
    short = [n.split(" (")[0] for n in t["tracker"].to_list()]
    colors = ["#7f7f7f", "#ff7f0e", "#1f77b4"][: len(short)]
    fig, ax = plt.subplots(1, 2, figsize=(TEXT_W, 2.3))
    a0 = ax[0]
    lo = t["lower_ok"].to_numpy()
    a0.barh(range(len(short)), lo, color=colors)
    for i, v in enumerate(lo):
        a0.text(min(v, 0.98), i, f" {v:.2f} ", va="center", ha="right", fontsize=6.5, color="white")
    a0.set_yticks(range(len(short))); a0.set_yticklabels(short, fontsize=6.5)
    a0.set_xlim(0, 1); a0.set_xlabel(r"lower bracket $s_t\geq\frac{1}{2}\sigma_t$")
    a0.set_title("(a) Stability-critical bracket")
    a1 = ax[1]
    ratio = t["W_s_over_Vsig"].to_numpy()
    a1.barh(range(len(short)), ratio, color=colors)
    for i, v in enumerate(ratio):
        a1.text(v, i, f" {v:.1f}$\\times$", va="center", ha="left", fontsize=6.5)
    a1.set_yticks(range(len(short))); a1.set_yticklabels([])
    a1.set_xscale("log"); a1.set_xlim(1, 100)
    a1.set_xlabel(r"$W_s / V_\sigma^+$ (lower = better)")
    a1.set_title("(b) Upward variation vs. true drift")
    _save(fig, "fig4_tracker.png")


MANIFEST = """# Figure set (definitive, corrected story)

Generated by `scripts/make_paper_figures.py` from `results/research/` artifacts.
All PNG, 300 dpi, uniform ICML styling.

- **fig1_problem.png** — the problem. (a) gradient tail (Hill $\\alpha\\approx2.43$) is
  heavier than its factors residual/feature ($\\alpha\\approx4$): a tail-dependence /
  interaction effect. (b) daily gradient tail index across the full 1,699-day record
  drifts and dips below 2 (infinite variance) on ~6% of days.
- **fig2_mechanism.png** — why scale-dependent clipping fails. (a) the gradient scale
  drifts ~6x across days. (b) a fixed-window adaptive clip threshold cannot win: a short
  window tracks the scale (so the step inherits the 6x swing), a long window is smooth
  but lags regime onsets.
- **fig3_main.png** — the result on a continuous multi-regime stream. (a) weighted $R^2$
  vs learning rate: SN-OMD climbs to ~0.24 across the whole range while OGD diverges
  (off-scale markers) and the clippers cliff. (b) peak rolling loss: SN-OMD stays bounded
  everywhere; the others explode.
- **fig4_tracker.png** — discharging assumption A1. A two-timescale envelope tracker holds
  the stability-critical lower bracket at 100% (a) with the smallest upward variation
  $W_s/V_\\sigma^+$ (b), on the real gradient-scale process.

These four figures are the definitive set used by `paper/icml2026.tex`. The old-story
first-pass paper (`main.tex`, `appendix.tex`) and its figures (`fig_heavytails.pdf`,
`fig_results.pdf`, `fig_ablation.pdf`) were removed 2026-07-30.
"""


def main():
    fig1_problem()
    fig2_mechanism()
    fig3_main()
    fig4_tracker()
    (FIG / "FIGURES.md").write_text(MANIFEST, encoding="utf-8")
    print("  wrote paper/figures/FIGURES.md")
    print("\nDefinitive figure set written to paper/figures/")


if __name__ == "__main__":
    main()
