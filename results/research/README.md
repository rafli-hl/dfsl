# Research & theory trail — reading guide

This folder is the full record behind *Distribution-Free Sequential Learning under a
Drifting Heavy Tail*: the problem, the data findings, the theory (with proofs), and
the reproducible scripts. Everything here is research material for the paper write-up;
the LaTeX in `paper/` is written separately.

**One-sentence thesis.** On heavy-tailed, *nonstationary* streams, plain OGD has no
usable learning rate; the fix is to make the step *scale-invariant* by normalizing the
gradient by a tracked scale (not clipping to a scale-dependent threshold), which
provably never diverges and attains the worst-tail dynamic rate.

---

## Read in this order

1. **`PROBLEM.md`** — what the problem is and why it is hard. The 3-axis map
   {bounded/unbounded domain} × {expectation/high-probability} × {known/unknown scale},
   plus the nonstationarity axis. Locates the open corner: *nonstationary × heavy-tailed
   × high-probability × parameter-free*.

2. **`FINDINGS.md`** — the empirical results on Jane Street (Findings 1–10). Highlights:
   - F1–2: OGD's "R²=−286" is a learning-rate artifact; the real story is a ~15× larger
     stable step from clipping.
   - F3–4: the intrinsic gradient tail is Hill α≈2.43 (not the 10¹⁴ divergence artifact),
     and it is an *interaction* effect — feature × residual tail dependence.
   - F5: fair per-method tuning overturns "Catoni is best" (hard-rejection > soft
     truncation).
   - F7–9: the heavy tail is *doubly* nonstationary (scale drifts 6×; tail index dips
     below 2); a scalar adaptive clip threshold provably cannot win.
   - **F10: SN-OGD never diverges and is the most accurate** (R²=0.24 vs clippers' 0.155),
     across the whole learning-rate range.

3. **`THEORY.md`** — the rates and the wall. Where `T^{1/p}` comes from; the dynamic
   lower bound `Σ_r σ_r L_r^{1/p}`; and the measured result that near-`√T` **dynamic**
   regret is information-theoretically out of reach on this data (heavy budget ≈ 6.8×√T),
   while *static* is fine — so the wall sits exactly at heavy-tails × nonstationarity.

4. **`THEORY_SNOGD.md`** — the algorithm (SN-OMD) and its two theorems: unconditional
   **stability**, and the **dynamic `T^{1/p}` regret** via the adaptive-step + summation-
   by-parts analysis (static §4′ and dynamic §5, both numerically verified). Key idea:
   the factor `1/s_t` replaces clipping's scale-*dependent* step bound with a scale-*free*
   one.

5. **`A1_TRACKER.md`** — discharging the scale-tracking assumption A1. One-sided
   requirement (lower bracket essential, over-estimation benign); the jump-cost lower
   bound; the two-timescale envelope; verification on the real scale process.
   *(Refined by `THEORY_FORMAL.md §4`.)*

6. **`THEORY_FORMAL.md`** — the formal appendix: complete proofs of the residual pieces
   (Freedman high-probability, clipped-moment/bias, per-round `p_t`, interval regret,
   post-jump lapse cost) and honest reductions for the two wrapper results (strongly-
   adaptive for unknown regime length; Zhang–Cutkosky for unknown `‖u‖`). Also corrects
   the `W_s=O(V_σ^+)` claim (needs decay `ρ≍1/L`) and states the genuine per-regime
   transition cost.

7. **`THEORY_SUMMARY.md`** — a self-contained consolidation of 3–6 in one note; read this
   if you want the theory end-to-end without the derivations.

---

## Honest status of the theory

- **Proved [R]:** stability (unconditional); the `T^{1/p}` rate; static and dynamic
  telescopes (numerically verified); clipped-moment/bias; per-round `p_t`→worst-`p`;
  Freedman high-probability; interval regret; post-jump lapse cost; the tracker `W_s`
  decomposition + design rule `ρ≍1/L`.
- **Reductions [G] (interface proved, wrapper cited):** unknown regime length →
  strongly-adaptive wrapper; unknown `‖u‖`/unbounded domain → Zhang–Cutkosky.
- **No conceptual gap remains.** The only non-self-contained pieces are the two cited
  wrapper theorems, whose exact interfaces SN-OMD is proved to meet.

---

## Reproducible scripts (`scripts/`)

| script | produces |
|---|---|
| `research_findings.py` | RQ1 lr-sensitivity, RQ2/3 intrinsic gradient tails |
| `research_fairness.py` | per-method lr tuning (fair ranking), standardization ablation |
| `research_windows.py` | per-window ranking stability |
| `research_continuous.py` | continuous multi-regime stream (deployability) |
| `research_nonstationarity.py` | scale/tail drift + threshold tension (Finding 9) |
| `research_heavybudget.py` | full-record tail index + dynamic heavy-budget wall |
| `research_normalize.py` | SN-OGD achievability (Finding 10) |
| `research_tracker.py` | A1 scale-tracker verification |
| `make_paper_figures.py` | the definitive figure set → `paper/figures/` |

Data artifacts (`*.csv`, `*.npy`) are the saved outputs; figures for the trail are the
`fig_*.png` here, and the paper set is in `paper/figures/` (see `FIGURES.md` there).

## Implementation

The method is a tested, first-class library learner: `dfsl.ScaleNormalizedOGD`
(+ `dfsl.preprocessing.OnlineScaleTracker`), config `configs/sn_ogd.yaml`. It reproduces
Finding 10 (R²=0.244 at lr=1.0). Full suite: 62 tests pass.
