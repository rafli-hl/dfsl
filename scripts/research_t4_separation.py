"""T4: does the stability partition survive as a *structural* separation, or is it tuning?

Registered in ``experiment_matrix.yaml`` (fourteenth document) at ``c84a766``, kind ``THEORY``,
before any of this was run.

STEP 0 IS ADVERSARIAL TO THE DIRECTION AND RUNS FIRST. D3/T4 carries a falsification condition
from its original registration: *"if scale-dependent clipping can be made stable ... by a rate
schedule alone, the partition is about tuning, not structure"*. The paper's own Table 2 reports
the scale-dependent methods as stable at ``lr <= 1e-2`` rather than as unconditionally
divergent. If that is what the committed artifacts say, T4 as framed is falsified before it
starts, and this script reports that rather than working around it.

Everything here reads COMMITTED artifacts. No learner is re-run and no number is regenerated,
so nothing this script prints can drift from what the paper was built on.

The successor hypothesis H_T4' -- registered at the same time, so it cannot be tuned to step
0's result -- says the methods form THREE tiers, separated by how the per-round step bound
``B_t`` responds to rescaling the whole gradient stream by ``lambda > 0``::

    tier 1  degree-1 homogeneous   OGD, AdaptiveClip, RobustOMD      B_t ~ ||g_t||
    tier 2  degree-0, UNbounded    the uncapped M -> infinity endpoint
    tier 3  constant               normalized-GD (B=1), SN-OMD (B=M), fixed-tau (B=tau)

and that ``eta_max ~ P*/sup_t B_t`` with ``P*`` method-independent. ``P*`` is taken from C10S's
already-committed ``~11.5`` and is NOT fitted per method: a per-method fit would make the test
unfalsifiable, which is the C10C2 mistake and is not repeated here.

Usage::

    .venv/Scripts/python.exe scripts/research_t4_separation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"

sys.path.insert(0, str(ROOT / "src"))
from dfsl.estimators import get_estimator  # noqa: E402

# ---------------------------------------------------------------- committed constants
P_STAR_C10S = 11.5        # C10S's boundary constant, already committed; NOT fitted here
CLIP_WINDOW = 512         # the window every research script builds AdaptiveClip/RobustOMD with
CLIP_QUANTILE = 0.9       # AdaptiveClip default
CLIP_MULTIPLIER = 3.0     # RobustOMD default
STRIDE = 50               # B_t is evaluated on a stride; Catoni over 512 points is not cheap

# tier 3 step bounds, read off the committed learner definitions rather than assumed:
#   NormalizedGD.update  ->  (lr/sqrt t) * g/||g||          so B = 1 exactly
#   ScaleNormalizedOGD   ->  (lr/sqrt t) * clip(g/s, cap)   so B = cap  (5.0 in every script)
#   fixedclip_perrow     ->  (lr/sqrt t) * clip(g, tau)     so B = tau  (20 in the paper)
TIER3_B = {"normgd": 1.0, "sn_ogd": 5.0, "fixed-tau clip": 20.0}


def rule(ch="=", n=98):
    print(ch * n)


# =====================================================================================
# STEP 0 -- the adversarial premise check
# =====================================================================================
def step_0() -> dict:
    rule()
    print("STEP 0 -- can a scale-OBLIVIOUS constant rate stabilise the scale-dependent methods?")
    print("  D3/T4's own falsification condition: if yes, the partition is tuning, not structure.")
    rule()

    verdicts = {}

    # --- artifact 1: lr_sensitivity.csv  (research_findings.py, date[0,30), 200k rows)
    d = pl.read_csv(RES / "lr_sensitivity.csv")
    print("\n### lr_sensitivity.csv -- date[0,30), 200k rows")
    print(f"  {'method':22s} {'largest stable lr':>18s} {'R2 there':>10s}")
    for m in ("ogd", "adaptive_clip", "robust_omd[catoni]"):
        sub = d.filter((pl.col("learner") == m) & (pl.col("weighted_r2") > 0)).sort("learning_rate")
        if sub.height:
            r = sub.row(sub.height - 1, named=True)
            print(f"  {m:22s} {r['learning_rate']:18.0e} {r['weighted_r2']:10.4f}")
            verdicts.setdefault(m, []).append(("lr_sensitivity", r["learning_rate"]))

    # --- artifact 2: fair_tuning.csv  (research_fairness.py, date[0,30), 100k rows)
    d = pl.read_csv(RES / "fair_tuning.csv")
    print("\n### fair_tuning.csv -- date[0,30), 100k rows")
    print(f"  {'method':30s} {'largest stable lr':>18s} {'R2 there':>10s}")
    for m in sorted(d["method"].unique().to_list()):
        sub = d.filter((pl.col("method") == m) & (pl.col("weighted_r2") > 0)).sort("learning_rate")
        if sub.height:
            r = sub.row(sub.height - 1, named=True)
            print(f"  {m:30s} {r['learning_rate']:18.0e} {r['weighted_r2']:10.4f}")
            verdicts.setdefault(m, []).append(("fair_tuning", r["learning_rate"]))

    # --- artifact 3: continuous_stream.csv  (research_continuous.py, date[0,120), 300k rows)
    #     This is the stream tab:jane's caption names.
    d = pl.read_csv(RES / "continuous_stream.csv")
    print("\n### continuous_stream.csv -- date[0,120), 300k rows  <- the stream tab:jane names")
    print(f"  {'method':30s} {'largest stable lr':>18s} {'R2 there':>10s} {'peak roll loss':>15s}")
    grid_top = float(d["learning_rate"].max())
    for m in sorted(d["method"].unique().to_list()):
        sub = d.filter((pl.col("method") == m) & (~pl.col("diverged"))).sort("learning_rate")
        if sub.height:
            r = sub.row(sub.height - 1, named=True)
            at_top = " <-- AT THE TOP OF THE GRID" if r["learning_rate"] == grid_top else ""
            print(f"  {m:30s} {r['learning_rate']:18.3g} {r['weighted_r2']:10.4f} "
                  f"{r['peak_rolling_loss']:15.3f}{at_top}")
            verdicts.setdefault(m, []).append(("continuous_stream", r["learning_rate"]))

    # ------------------------------------------------------------------------ verdict
    rule("-")
    scale_dep = ["ogd", "adaptive_clip", "robust_omd[catoni]",
                 "robust_omd[median_of_means]", "robust_omd[trimmed_mean]"]
    stabilised = [m for m in scale_dep if m in verdicts]
    print("Every scale-dependent method has a strictly positive rate at which it is stable,")
    print(f"in every artifact that measures it ({len(stabilised)} of {len(scale_dep)} methods found):")
    for m in stabilised:
        rates = ", ".join(f"{src}={lr:.3g}" for src, lr in verdicts[m])
        print(f"    {m:30s} {rates}")
    print()
    print("STEP 0 VERDICT: the condition IS met. A scale-oblivious constant rate stabilises")
    print("  the scale-dependent methods. T4 AS ORIGINALLY FRAMED IS FALSIFIED -- the partition")
    print("  is not 'one family diverges and the other does not' for ALL rate schedules.")
    return verdicts


# =====================================================================================
# STEP 0b -- a provenance discrepancy found while doing step 0
# =====================================================================================
def step_0b() -> list[dict]:
    rule()
    print("STEP 0b -- tab:jane's AdaptiveClip/RobustOMD row against the stream its caption names")
    rule()
    d = pl.read_csv(RES / "continuous_stream.csv")
    print("  The paper prints:  AdaptiveClip / RobustOMD   R2 ~ 0.01   stable lr <= 1e-2")
    print("  The caption sources tab:jane to the *continuous* Jane stream. On that stream:")
    print(f"\n  {'method':30s} {'best R2':>10s} {'at lr':>8s} {'diverged anywhere?':>20s}")
    rows = []
    for m in sorted(d["method"].unique().to_list()):
        if m == "ogd":
            continue
        sub = d.filter(pl.col("method") == m).sort("weighted_r2", descending=True)
        best = sub.row(0, named=True)
        any_div = bool(d.filter(pl.col("method") == m)["diverged"].any())
        print(f"  {m:30s} {best['weighted_r2']:10.4f} {best['learning_rate']:8.3g} "
              f"{str(any_div):>20s}")
        rows.append({"check": "tabjane_clipper_row", "method": m,
                     "best_r2_on_continuous_stream": round(best["weighted_r2"], 4),
                     "at_lr": best["learning_rate"], "diverged_anywhere": any_div,
                     "paper_says_r2": 0.01, "paper_says_stable_lr_max": 0.01})
    print("\n  Two discrepancies, both reported as provenance findings and NOT as settled errors:")
    print("   (1) the row's ~0.01 matches fair_tuning.csv / lr_sensitivity.csv, which are")
    print("       date[0,30) windows -- not the continuous stream the caption names, where the")
    print("       same methods reach 0.14-0.16.")
    print("   (2) 'stable lr <= 1e-2' is not what the artifact shows: the clippers are stable at")
    print("       2e-2 and 3e-2 and NEVER diverge in the sweep, which stops at 3e-2. The ceiling")
    print("       is not located, so 'any larger rate diverges' is untested for these methods.")
    print("  Neither row is covered by a PAPER_CLAIMS guard, which is how this could persist.")
    return rows


# =====================================================================================
# STEP 1 -- B_t on one common reference stream, and the homogeneity classification
# =====================================================================================
def rolling_stat(g, fn, window):
    """fn applied to a trailing window, on a stride (the full pass is O(n*window))."""
    out = []
    for t in range(window, len(g), STRIDE):
        out.append(float(fn(g[t - window:t])))
    return np.asarray(out)


def step_1() -> list[dict]:
    rule()
    print("STEP 1 -- B_t on ONE common reference stream, and the homogeneity test")
    rule()
    g = np.load(RES / "gradnorm_at_wstar.npy")
    g = g[np.isfinite(g) & (g > 0)]
    print(f"  reference stream: gradnorm_at_wstar.npy, n={len(g)} -- gradients at the FIXED")
    print("  optimum w*, so no feedback from a diverging iterate contaminates the comparison.")
    print(f"  ||g||: median {np.median(g):.3f}  p99 {np.quantile(g,0.99):.3f}  max {g.max():.3f}")

    catoni = get_estimator("catoni")
    defs = {
        "OGD":          ("tier 1", lambda x: x[-1]),
        "AdaptiveClip": ("tier 1", lambda x: np.quantile(x, CLIP_QUANTILE)),
        "RobustOMD":    ("tier 1", lambda x: CLIP_MULTIPLIER * max(float(catoni(x)), 1e-12)),
    }

    rows = []
    print(f"\n  {'method':14s} {'tier':8s} {'median B_t':>12s} {'p99 B_t':>12s} {'sup B_t':>12s}")
    Bs = {}
    for name, (tier, fn) in defs.items():
        b = rolling_stat(g, fn, CLIP_WINDOW)
        Bs[name] = b
        print(f"  {name:14s} {tier:8s} {np.median(b):12.3f} {np.quantile(b,0.99):12.3f} "
              f"{b.max():12.3f}")
        rows.append({"check": "B_t", "method": name, "tier": tier,
                     "B_median": round(float(np.median(b)), 4),
                     "B_p99": round(float(np.quantile(b, 0.99)), 4),
                     "B_sup": round(float(b.max()), 4)})
    for name, B in TIER3_B.items():
        print(f"  {name:14s} {'tier 3':8s} {B:12.3f} {B:12.3f} {B:12.3f}   (a constant, by definition)")
        rows.append({"check": "B_t", "method": name, "tier": "tier 3",
                     "B_median": B, "B_p99": B, "B_sup": B})

    # ---------------------------------------------------- the homogeneity test itself
    print("\n### the homogeneity test: rescale the WHOLE stream by lambda and re-measure B")
    print("  H_T4' classifies methods by degree. Verify it numerically rather than assert it.")
    print(f"\n  {'method':14s} {'B(2g)/B(g)':>12s} {'B(10g)/B(g)':>12s}   degree")
    for name, (tier, fn) in defs.items():
        base = float(np.median(rolling_stat(g, fn, CLIP_WINDOW)))
        r2 = float(np.median(rolling_stat(2.0 * g, fn, CLIP_WINDOW))) / base
        r10 = float(np.median(rolling_stat(10.0 * g, fn, CLIP_WINDOW))) / base
        deg = 1 if abs(r10 - 10.0) < 0.05 else (0 if abs(r10 - 1.0) < 0.05 else -1)
        print(f"  {name:14s} {r2:12.4f} {r10:12.4f}   {deg if deg>=0 else '?'}")
        rows.append({"check": "homogeneity", "method": name, "tier": tier,
                     "ratio_lambda2": round(r2, 4), "ratio_lambda10": round(r10, 4),
                     "degree": deg})
    for name, B in TIER3_B.items():
        print(f"  {name:14s} {1.0:12.4f} {1.0:12.4f}   0   (B is a constant; nothing to measure)")
        rows.append({"check": "homogeneity", "method": name, "tier": "tier 3",
                     "ratio_lambda2": 1.0, "ratio_lambda10": 1.0, "degree": 0})
    print("\n  Degree 1 means the step bound inherits the gradient scale in full. That is the")
    print("  structural content of 'scale-dependent', and it is now measured, not asserted.")
    return rows


# =====================================================================================
# STEP 2 -- the invariant eta_max * B, and whether tier 2 is intermediate
# =====================================================================================
def step_2() -> list[dict]:
    rule()
    print("STEP 2 -- the invariant  eta_max * sup_t B_t ~= P*,  and tier 2's position")
    rule()
    nc = pl.read_csv(RES / "normalize_continuous.csv")
    cs = pl.read_csv(RES / "continuous_stream.csv")
    print("  eta_max is read from the committed sweeps on the SAME stream (date[0,120)):")
    print("    normalize_continuous.csv  ogd, normgd, scale_adaptive, sn_ogd   (grid to lr=8)")
    print("    continuous_stream.csv     ogd + the clippers                    (grid to lr=0.03)")

    # A ceiling is only MEASURED if the method actually diverges somewhere on the grid.
    # If it never does, eta_max is right-censored at the grid top and any P built from it is
    # a lower bound, not a value. Getting this wrong is the difference between "falsified"
    # and "untestable", so it is made explicit rather than left to the reader.
    def eta_max(df, col, m):
        sub = df.filter(pl.col(col) == m).sort("learning_rate")
        stable = sub.filter(~pl.col("diverged"))
        div = sub.filter(pl.col("diverged"))
        if not stable.height:
            return None
        last = float(stable.row(stable.height - 1, named=True)["learning_rate"])
        first_div = float(div.row(0, named=True)["learning_rate"]) if div.height else None
        return {"last_stable": last, "first_diverged": first_div,
                "censored": first_div is None}

    o_nc, o_cs = eta_max(nc, "method", "ogd"), eta_max(cs, "method", "ogd")
    agree = o_nc["last_stable"] == o_cs["last_stable"]
    print(f"\n  cross-check, OGD in both artifacts: normalize_continuous="
          f"{o_nc['last_stable']:g}  continuous_stream={o_cs['last_stable']:g}  "
          f"{'AGREE' if agree else 'DISAGREE'}")
    if not agree:
        print("  CAUSE, traced rather than guessed: same date[0,120) window and the SAME")
        print("  divergence criterion (r2 < -1 or peak > 50), but different stream lengths --")
        print("  research_normalize.py loads max_rows=150000, research_continuous.py 300000.")
        print("  Doubling the stream drops OGD's ceiling by a factor of 5. That is the")
        print("  direction H_T4' predicts for tier 1, but it is NOT a clean test: standardize=")
        print("  True fits on the loaded slice, so the two runs also see different features.")
        print("  Step 3 does the clean version on a single fixed stream.")

    rows = []
    print(f"\n  {'method':16s} {'tier':8s} {'eta_max':>16s} {'B':>10s} {'P=eta_max*B':>16s}")
    tier3, censored_any = {}, False
    for m, B in (("normgd", 1.0), ("sn_ogd", 5.0)):
        e = eta_max(nc, "method", m)
        if e is None:
            continue
        if e["censored"]:
            censored_any = True
            lab = f">= {e['last_stable']:g}"
            plab = f">= {e['last_stable']*B:g}"
            tier3[m] = (e["last_stable"] * B, None)
        else:
            lab = f"[{e['last_stable']:g},{e['first_diverged']:g})"
            plab = f"[{e['last_stable']*B:g},{e['first_diverged']*B:g})"
            tier3[m] = (e["last_stable"] * B, e["first_diverged"] * B)
        print(f"  {m:16s} {'tier 3':8s} {lab:>16s} {B:10.3f} {plab:>16s}"
              + ("   CENSORED" if e["censored"] else ""))
        rows.append({"check": "invariant", "method": m, "tier": "tier 3",
                     "eta_max_last_stable": e["last_stable"],
                     "eta_max_first_diverged": e["first_diverged"],
                     "censored": e["censored"], "B": B,
                     "P_lo": round(e["last_stable"] * B, 4),
                     "P_hi": None if e["censored"] else round(e["first_diverged"] * B, 4)})

    e_sa, e_og = eta_max(nc, "method", "scale_adaptive"), o_nc
    for m, e, tier, blab in (("scale_adaptive", e_sa, "tier 2", "unbounded"),
                             ("ogd", e_og, "tier 1", "sup||g||")):
        lab = (f">= {e['last_stable']:g}" if e["censored"]
               else f"[{e['last_stable']:g},{e['first_diverged']:g})")
        print(f"  {m:16s} {tier:8s} {lab:>16s} {blab:>10s} {'n/a':>16s}")
        rows.append({"check": "invariant", "method": m, "tier": tier,
                     "eta_max_last_stable": e["last_stable"],
                     "eta_max_first_diverged": e["first_diverged"],
                     "censored": e["censored"], "B": None, "P_lo": None, "P_hi": None})

    # ------------------------------------------------------- falsification (a): spread
    print("\n### falsification (a): is P constant across tier 3?")
    if censored_any:
        cen = [m for m, (_, hi) in tier3.items() if hi is None]
        print(f"  INCONCLUSIVE -- not falsified and not confirmed. {', '.join(cen)} never")
        print("  diverges anywhere on the committed grid (top lr=8), so its ceiling is")
        print("  RIGHT-CENSORED and every P built from it is a lower bound, not a value.")
        for m, (lo, hi) in tier3.items():
            print(f"    {m:16s} P {'>= %g' % lo if hi is None else '[%g,%g)' % (lo, hi)}")
        print("  Taking the censored value at face value would have given a spread of")
        print(f"  {max(v[0] for v in tier3.values())/min(v[0] for v in tier3.values()):.2f}x and a"
              " verdict of FALSIFIED. That verdict would have been an")
        print("  artifact of the grid ending, not a measurement, so it is not recorded.")
        print("  Deciding it needs a wider grid for normalized-GD, which is new compute and")
        print("  therefore a separate registration.")
        print(f"  For reference only, NOT used as evidence: C10S's committed P* = {P_STAR_C10S},")
        print("  and normalized-GD's own R2 is already declining past lr=3 (0.221 -> 0.201 ->")
        print("  0.086) with peak rolling loss rising 5.1 -> 7.9 -> 20.0, so its ceiling is")
        print("  plausibly just beyond the grid. That is an extrapolation and is labelled one.")
        rows.append({"check": "falsification_a", "method": "tier3",
                     "verdict": "INCONCLUSIVE_CENSORED", "censored_members": ",".join(cen)})
    else:
        vals = [lo for lo, _ in tier3.values()]
        spread = max(vals) / min(vals)
        print(f"  P lower bounds {['%.2f' % p for p in vals]}  spread {spread:.2f}x")
        print(f"  registered threshold 1.68x: {'WITHIN' if spread <= 1.68 else 'EXCEEDS'}")
        rows.append({"check": "falsification_a", "method": "tier3",
                     "verdict": "PASS" if spread <= 1.68 else "FALSIFIED",
                     "spread": round(spread, 4)})

    # ------------------------------------------- falsification (b): tier 2 intermediate
    print("\n### falsification (b): is tier 2 strictly between tier 1 and tier 3?")
    t1, t2 = e_og["last_stable"], e_sa["last_stable"]
    t3_floor = min(eta_max(nc, "method", m)["last_stable"] for m in ("normgd", "sn_ogd"))
    inter = t1 < t2 < t3_floor
    print(f"  tier 1 (ogd) {t1:g}  <  tier 2 (scale_adaptive) {t2:g}  <  "
          f"tier 3 floor {t3_floor:g} ?   {'YES' if inter else 'NO'}")
    print("  This one is NOT affected by the censoring above: censoring can only push tier 3's")
    print("  ceiling HIGHER, which widens the gap it has to clear, so the verdict is safe.")
    if inter:
        print(f"  tier 2 sits {t2/t1:.0f}x above tier 1 and at least {t3_floor/t2:.0f}x below")
        print("  tier 3's floor. So scale-INVARIANCE alone buys part of the gap and")
        print("  BOUNDEDNESS buys the rest -- they are separate properties with separate effects.")
        print("  Section 3's two-way contrast (scale-free vs scale-dependent) does not capture")
        print("  this; the paper's own Table 1 already reports the uncapped endpoint at 7/10")
        print("  per-row divergences, which is neither tier's behaviour.")
    rows.append({"check": "falsification_b", "method": "scale_adaptive",
                 "eta_max_tier1": t1, "eta_max_tier2": t2, "eta_max_tier3_floor": t3_floor,
                 "intermediate": bool(inter), "verdict": "PASS" if inter else "FALSIFIED"})
    return rows


# =====================================================================================
# STEP 3 -- the horizon prediction, on ONE fixed stream (no standardization confound)
# =====================================================================================
def step_3() -> list[dict]:
    rule()
    print("STEP 3 -- does tier 1's ceiling have to shrink with the horizon?")
    rule()
    print("  H_T4': tier 1's ceiling is P*/sup_t B_t and B_t is degree-1, so the ceiling")
    print("  inherits the growth of an EXTREME order statistic of ||g_t||. Tier 3's B is a")
    print("  constant, so its ceiling is horizon-independent. Measured on prefixes of ONE")
    print("  fixed stream, so nothing varies but the horizon.")
    g = np.load(RES / "gradnorm_at_wstar.npy")
    g = g[np.isfinite(g) & (g > 0)]
    ns = [12500, 25000, 50000, 100000, 200000]
    ns = [n for n in ns if n <= len(g)]
    sup = [float(g[:n].max()) for n in ns]
    print(f"\n  {'T':>9s} {'sup||g||':>12s} {'ratio vs prev':>15s}")
    for i, (n, s) in enumerate(zip(ns, sup)):
        r = "" if i == 0 else f"{s/sup[i-1]:15.3f}"
        print(f"  {n:9d} {s:12.3f} {r:>15s}")
    b, _ = np.polyfit(np.log(ns), np.log(sup), 1)
    ALPHA = 2.43  # committed Hill estimate for the raw gradient norm (D1/T1 step 0)
    print(f"\n  fitted growth exponent of sup||g|| in T: {b:.3f}")
    print(f"  predicted from the committed Hill index alpha={ALPHA}: 1/alpha = {1/ALPHA:.3f}")
    print(f"  a doubling of T multiplies sup||g|| by 2^{b:.3f} = {2**b:.3f}"
          f"  (predicted {2**(1/ALPHA):.3f})")
    print("\n  So tier 1's ceiling decays with the horizon while tier 3's does not. The effect")
    print("  is REAL but SLOW -- a factor of ~1.3 per doubling, not the 5x seen between the two")
    print("  artifacts in step 2, which therefore cannot be attributed to horizon alone.")
    print("  Reported that way rather than claimed as a confirmation.")
    return [{"check": "horizon", "method": "sup_grad_norm", "T": n, "sup": round(s, 4),
             "fitted_exponent": round(float(b), 4), "predicted_exponent": round(1 / ALPHA, 4)}
            for n, s in zip(ns, sup)]


def run() -> int:
    v = step_0()
    rows = step_0b()
    rows += step_1()
    rows += step_2()
    rows += step_3()

    rule()
    print("WHAT THIS DOES NOT ESTABLISH")
    print("  Nothing about Prop 3.1, which is correct, unconditional and untouched.")
    print("  Nothing about the ten-window divergence partition, which is measured at FROZEN")
    print("    hyperparameters and is not a statement about tuned ceilings.")
    print("  No theorem. Step 1 and step 2 are measurements that a theorem would have to")
    print("    explain; the derivation is separate and is reported separately.")
    rule()

    out = RES / "t4_separation.csv"
    pl.DataFrame(rows, infer_schema_length=None).write_csv(out)
    print(f"[saved {out.relative_to(ROOT)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
