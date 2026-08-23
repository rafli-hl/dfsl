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

## Session 4 — direction C10R, testing C-8 on held-out data (complete, but vacuous)

**Question.** Does the realized maximum step `lr*min(r_q, M)` locate the divergence boundary
better than the nominal `P = lr*M`, on a stream that did not generate the hypothesis?

**Registered verdict: H5 FALSIFIED at ratio = 1.0000 -- and the number is an identity, not
evidence.** Stage 1 chose `q* = max`; Jane's `r_max = 49.93` exceeds every `M` on the grid,
so `min(r_max, M) = M` and `R` equals `P` identically. The ratio was fixed before any
held-out data was touched. Write-up: `results/research/c10r/r_c10r_summary.md`.

**Cause: my registration error.** C-8 came from the Jane *per-step* residual; I registered
the stage-1 fit on *per-row*, where the residual is non-monotone and no quantile can help.
A per-step fit would have chosen `q = p99` (ratio 0.656, inside the survival band).

**The held-out data favours C-8, post hoc.** On crypto, `P*` rises monotonically with `M`
across all eight rays spanning 128x in `M` (6.60 -> 37.95). With crypto's own `r_p99` the
spread falls 5.75 -> 2.49 (ratio 0.433). Self-fitted, so suggestive rather than a test.
Having seen it, I cannot repair the test on crypto; a third stream is required.

**Registered primary criterion voided.** Crypto's native rule (peak > 1e3, adopted unchanged
to avoid choosing a threshold after seeing results) right-censors all eight rays -- nothing
diverges even at `P = 128`. Everything reported rests on the registered secondary. See
ledger C-9.

**A registered finding that stands.** `P`'s tightness is stream-dependent: `spread_P` is
1.68x on Jane but 5.75x on crypto, against `spread_lr` of 23.6x and 22.3x. The compression
relative to the rate alone replicates; the tightness does not. C-7 amended accordingly.

## Session 5 — direction C10T, the clean test of C-8 on the synthetic suite (VOID)

**Question.** Does the realized maximum step beat the nominal one on a stream that played no
part in generating C-8?

**Result: H6 VOID, H7 VOID.** All 48 ray x criterion x tail-index combinations censored, in
OPPOSITE directions: the state-based criterion right-censored everything (nothing diverges
even at `P = 128`), Jane's `_diverged` left-censored everything (everything diverges even at
`P = 0.5`). Write-up: `results/research/c10t/r_c10t_summary.md`.

**The streams were fine.** The registered sanity expectation held exactly: reference `r_p99`
= 14.760 / 11.663 / 8.020 for tails 1.3 / 1.5 / 2.0. Instrumentation gate passed bit-exactly.
Both failures are properties of the criteria.

**Why the primary cannot fire -- provable without data, and I should have derived it before
registering.** For a finite cap, `||w_T|| <= sum (lr/sqrt(k))*M <= 2*P*sqrt(T)` = 36 204 at the
top of the bracket, against a registered threshold of 1e8; measured `max||w||` was 59.11. My
justification -- that the criterion "refers to the quantity thm:stability bounds" -- was
backwards: BECAUSE the theorem bounds it, it cannot discriminate.

**Why the secondary fires everywhere.** On Student-t(1.5) the target has infinite variance
(sample var ~3499), so peak rolling loss is ~34 600 for any learner -- including the ZERO
predictor -- against an absolute threshold of 50 calibrated to Jane's standardized targets.

**The finding that outlives the failure.** "Divergence" is not well defined across streams in
this repository. Iterate divergence is impossible for capped SN-OMD, so every divergence
measured in this line of work is a LOSS phenomenon, not instability -- C-7's `P*` is a
loss-degradation threshold, not a stability boundary. Ledger: C-7 amended (b), C-8 closed as
untested, C-9 strengthened, C-10 opened as a prerequisite.

**Direction closed as registered** -- no fourth stream, and no uncontaminated one remains.

## Session 6 — direction C10C, building the C-10 criterion (REJECTED on one test)

**Deliverable.** `scripts/research_divergence.py` -- divergence measured against the best
constant predictor on the same window, so no per-stream constant survives, with the rolling
window a fraction of the stream rather than a fixed 2000 steps.

**Registered verdict: REJECTED.** V1 reference sanity PASS (0/18 flagged; the inherited Jane
rule flags 6/18), V2 blow-up recall PASS (20/20, 0 missed), V3 monotonicity PASS (12 rays, 0
violations), V5 kappa robustness PASS, **V4 non-vacuity FAIL** (synthetic 0/60).

**The evidence indicts V4, not the criterion.** On synthetic nothing capped diverges up to
`P = 256` (`L_ratio` 0.999 to 1.152) while true blow-ups sit at `L_ratio` 2.75e103. V4 asked
for both classes on every stream, which is a property of the stream and grid rather than of
the instrument. Not patched in-session, per the registration.

**Amendment A1** reduced Jane's row cap 150000 -> 40000 on cost grounds, registered before
the re-run after a measured 8x overrun.

**Fell out of it:** capped SN-OMD does not diverge on the synthetic stream at any `P` in the
grid, so C-7's `P*` needs scale drift and is not a property of the algorithm alone (C-11).

**Also fixed this session, outside the research line:** the anonymized-supplement exclusion
`"paper/icml2026."` stopped matching when the ICML files moved into `paper/icml2026/`, so the
exclusion failed open while the identity self-check still reported clean. Fixed, and pinned by
`tests/test_anon_exclusions.py` (suite 84 -> 104, verified by mutation).

## What is now open

1. **Re-validate the C-10 criterion under a corrected V4.** (Ledger C-10.) The candidate
   exists and passes four of five acceptance tests; V4 must be respecified as non-vacuity
   *conditional on a divergent configuration existing in the probe set*. That is a
   registration change, so it needs a new registration rather than an edit to C10C's. Until
   the criterion passes a corrected suite, no cross-stream threshold claim is possible and
   C-8 stays untestable.
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
