# Research state

**This file is new as of 2026-08-23.** The Phase-1 `research_state.md` referenced by the
Phase-2 brief — including its §17 candidate ranking — is absent from this repository and
`git log --all` confirms it was never committed here. Neither were `RESEARCH_CHARTER.md`,
`claim_ledger.md`, or any `results/research/r1_*` artifact. This file records state from
the first Phase-2 session that ran in this repository, and does not reconstruct Phase 1.

## Environment (verified 2026-08-23)

- Branch `research/c10-q6`, cut from `paper-submission` at `e66768d`.
- Jane data **present**: `data/raw/jane/` is 12 GB of hive-partitioned parquet
  (`train.parquet/partition_id=0..9`), not a single file. Loads in ~0.8 s per
  150 000-row window.
- Test suite: **84 passed** in `.venv`. A bare `python -m pytest` fails with
  `ModuleNotFoundError: dfsl` — the project venv is required.
- Compute: 12 cores, 43 GB free disk, single-process foreground runs.

## Session 1 — direction C10/Q6 (complete)

**Question.** On the ten-window benchmark a constant scale (fixed-tau clip) beat the
predictable tracked scale the method is built on. Property of the scale process, or
artifact of tuning budget?

**Selection rationale.** C10/Q6 was chosen over T1, T4 and E2 because it could falsify a
central premise rather than confirm one, and because the phenomenon was already present
in committed artifacts so no new measurement was needed to motivate it. R1c was excluded
as not actionable: no `r1_*` artifact exists in this repository.

**Result.** H1 survived, decisively — `fraction_closed = 1.32` against a registered
threshold of 0.50, per-row. The gap did not merely close, it reversed: at matched budget
SN-OMD 0.2270 vs fixed-tau 0.2020 held-out, winning 9/9 held-out windows and 10/10
overall. Full write-up: `results/research/c10/r_c10_summary.md`. Ledger: `claim_ledger.md`
C-1 through C-6.

**Key structural fact established.** The two methods are one algorithm. Update magnitude
is `(lr/sqrt(k))*min(||g||, tau)` for fixed-tau clip and `(lr/sqrt(k))*min(||g||/s_t, M)`
for SN-OMD, so SN-OMD with a constant scale `s0` is exactly fixed-tau clip with
`tau = M*s0`, `lr' = lr/s0`. The family differs in one place only: whether the clip
threshold is constant or tracks a predictable scale. Any comparison between them is a
comparison of scale processes **only** at matched budget over `(lr, threshold)`.

**Defect found and fixed.** `research_windows_replication._grid` gave the baseline a joint
2-D grid and the proposal a 1-D grid with the cap pinned at a value selected in a separate
sweep at a different learning rate. This is a fairness defect in the baseline's favour.
The published SN-OMD ten-window figures are the under-tuned ones.

## Session 2 — direction C10M, the clip-binding mechanism probe (complete)

**Question.** Does the cap act through the effective maximum step `P = lr*M`, or through
how often the clip binds?

**Result: both registered hypotheses INCONCLUSIVE.** `eta2_P = 0.578` per-row against a
0.80 survival threshold (H2); `rho2_b - rho2_logP = -0.011` against a +/-0.05 band (H3).
Neither mechanism established. Full write-up: `results/research/c10m/r_c10m_summary.md`.

**Clip-binding frequency is not supported.** The anchors differ ten-fold in binding rate
(0.0122 published vs 0.1220 matched) but across the grid binding rate is almost a
deterministic function of `M` alone and carries the weakest association with held-out
performance of the four candidates. A single anchor pair could not have separated this
from the concurrent `lr` and `P` differences, which is why the grid was needed.

**Design error, recorded.** `rho2` is a monotone statistic and the surface is single-peaked
in both `lr` and `M`, so the H3 test was under-powered by construction. An unregistered
exact-grouping `eta2` (which does not assume monotonicity) reverses the implied ordering:
`P` 0.578 > `M` 0.443 > `lr` 0.357 per-row. Recorded as post hoc.

**Exploratory, not preregistered:** divergence separates perfectly on `P` per-row -- 20/20
stable at `P <= 8`, 10/10 divergent at `P >= 16`. See ledger C-7.

**Instrumentation gate passed bit-exactly** (worst diff 0.00e+00), so the binding
statistics describe the algorithm the rest of the repository measures.

## Session 3 — direction C10S, locating the stability threshold (complete)

**Question.** Is divergence governed by `P = lr*M` alone, and where exactly is the
threshold?

**Result: H4 INCONCLUSIVE.** Per-row spread across rays = 1.682 against a survival band of
<= 1.25; per-step = 2.378, which would be falsified. Both registered guards clean in both
protocols: 0 censored rays, 0 non-monotone rays, 6/6 usable, brackets resolved to a factor
of 1.044. Write-up: `results/research/c10s/r_c10s_summary.md`. Ledger: C-7 updated,
C-8 added.

**Located.** `P*_hat = 11.49` per-row (range [8.67, 14.58]); `9.80` per-step (range
[7.29, 17.34]), at 150 000 rows per window.

**The substantive finding, stronger than the verdict.** `P` compresses a 32x variation in
`M` and a 23.6x variation in the critical rate into a 1.68x variation in `P*`. The design
was built to make that hard -- at fixed `P` the `M=0.5` ray clips ~57% of steps and `M=16`
clips ~0.1%. `P` is far better than either factor alone while still missing the registered
sufficiency tolerance.

**C-7 partly retired.** The boundary is a transition band, not a cliff: the any-window
criterion marks where the first of ten windows fails, and the median-window threshold sits
1.3-1.7x higher. C10M sampled `P` at factor-2 spacing -- the width of the band -- so the
separation looked perfect at that resolution. Post hoc.

**Dominant threat, recorded.** The any-window criterion is an extreme-value statistic
(minimum over ten windows), so each `P*` is set by the single most fragile window. It was
inherited unchanged for comparability with C-7, which is a design cost accepted rather than
a discovery. The 1.044 bracket is search resolution, not a confidence interval.

## What is now open

1. **Does the *realized* maximum step `lr*min(r_max, M)` explain C-7's residual?**
   (Ledger C-8.) `P` is the nominal maximum, attained only when the clip binds, which for
   large `M` is rare. The realized maximum predicts exactly the per-step pattern of `P*`
   rising with `M`. Post-hoc proposal from the C10S residual, so it must be tested on data
   that did not generate it.
2. **Compare `P*` against `thm:stability`'s constant.** The theorem bounds iterates under a
   capped normalized step and should imply a boundary; whether its constant reproduces
   `P*_hat ~ 11.5` is the one place this empirical line touches the paper's theory. Not
   attempted.
3. **Re-locate the boundary under a non-extreme-value criterion.** The any-window rule makes
   `P*` a minimum over ten windows. A median-window or per-window-survival analysis would
   be more robust and is cheap given the recorded divergent-window fractions.
4. **The mechanism of accuracy among stable configurations remains unexplained.** No
   registered scalar summarized the C10M surface; `eta2_P = 0.578` leaves most
   between-configuration variance unaccounted for.
5. **Rolling-origin selection.** Every transfer claim here rests on one selection window.
   Whether the ordering survives a different choice of selection window is untested and is
   the single most load-bearing threat to the result.
6. **Per-step grid adequacy.** The matched per-step arm selected at two grid edges
   (`lr=8.0`, `M=0.5`); its optimum is unresolved. A widened per-step grid would be a
   separate, explicitly post-hoc run.
7. **Re-run the full ten-window table at matched budget.** Only three arms were re-run.
   Normalized-GD, AdaGrad-Norm, OGD and the uncapped endpoint were not, and their
   published tuning budgets have not been audited.

## Directions not taken

- **T1** (variation-adaptive dynamic-regret bound) and **T4** (formal separation for
  bounded scale-free methods) — both untouched, both still the only routes to a
  non-vacuous theorem.
- **E2** (synthetic phase diagram) — untouched; still the cheapest route to a
  "when does this help" boundary, and data-free, hence reviewer-reproducible.
- **R1c** — not actionable in this repository.
