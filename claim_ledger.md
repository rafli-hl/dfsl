# Claim ledger

**This file is new as of 2026-08-23.** The Phase-1 `claim_ledger.md` referenced by the
Phase-2 brief is absent from this repository and `git log --all` shows it was never
committed here. This ledger therefore starts from the claims a Phase-2 session has
actually examined, not from an inherited list. Claims not listed here have not been
audited by this process and carry whatever status the manuscript gives them.

Status values: `SUPPORTED` (measured, survives the check applied) ·
`CONFOUNDED` (the evidence offered cannot answer the question) ·
`OPEN` (asked, not answered) · `UNTOUCHED` (not examined this phase).

---

## C-1 — "A constant scale beats a predictable tracked scale on the ten-window benchmark"

**Status: CONFOUNDED → REVERSED at matched budget.**

Evidence as published: `windows_replication.csv`, per-row held-out means, fixed-tau clip
0.2020 vs SN-OMD (M=5) 0.1237, fixed-tau winning 9/9 held-out windows.

What was found (direction C10/Q6, `results/research/c10/r_c10_summary.md`): the two arms
were tuned at unequal budget — 70 joint `(lr x tau)` configurations for the baseline
against 10 `lr` configurations for the proposal with the cap pinned at `M=5`. At matched
budget (70 joint `(lr x M)` configurations) the ordering **reverses**: SN-OMD 0.2270 vs
fixed-tau 0.2020, held-out `delta = -0.0250` [−0.0338, −0.0162], SN-OMD winning 9/9
held-out and 10/10 overall. `fraction_closed = 1.32` against a registered survival
threshold of 0.50.

Scope: per-row primary. Per-step agrees in direction (`-0.0134`, 0/9) but its matched arm
selected at two grid edges, so its magnitude is not resolved.

**Consequence:** the published comparison cannot support a claim about constant vs tracked
scale processes in either direction. It must be re-run at matched budget before any
manuscript use.

## C-2 — "SN-OMD is fragile across windows (held-out sd 0.103, min −0.107)"

**Status: CONFOUNDED.** The fragility is a property of the published configuration
(`M=5, lr=2`), not of the tracked scale. At matched budget the same method has held-out
sd 0.0403 and min +0.1693; the window-7 collapse disappears entirely.

## C-3 — "The ten-window mean is a held-out measurement"

**Status: CONFOUNDED.** The published protocol tunes on window 1 and reports the mean over
all ten windows *including* window 1. Per-row, the published SN-OMD arm wins the selection
window (0.2846) and loses all nine held-out windows — a selection-overfitting signature
the pooled mean conceals. Held-out and in-sample figures should be reported separately.

## C-4 — "Stored research artifacts reproduce"

**Status: SUPPORTED.** The preregistered reproduction gate re-derived the fixed-tau and
published-SN-OMD held-out means from source and matched `windows_replication.csv` to
`diff = 0.0000` in both protocols (tolerance 0.005). The stored numbers are sound; the
defect found is in comparison design, not arithmetic.

## C-5 — "Why does a constant scale beat a tracked one?" (the C10/Q6 question as posed)

**Status: DISSOLVED — false premise.** At matched budget it does not. Replaced by C-6.

## C-6 — Mechanism: why does `M=2` at `lr=3` transfer across windows when `M=5` at `lr=2` does not?

**Status: still OPEN.** Probed in direction C10M
(`results/research/c10m/r_c10m_summary.md`); both registered hypotheses came back
**inconclusive** and neither mechanism was established.

- **Clip-binding frequency is not supported as the mechanism.** The two anchors differ
  ten-fold in binding rate (published 0.0122, matched 0.1220), but across a 30-point
  dyadic grid binding rate is almost a deterministic function of `M` alone and has the
  *weakest* rank association with held-out performance of the four registered candidates
  (`rho2 = 0.007`). Caveat recorded against my own design: `rho2` is a monotone statistic
  and the surface is single-peaked, so the H3 test was under-powered by construction.
- **Product sufficiency (`P = lr·M`) is inconclusive for performance**: `eta2_P = 0.578`
  per-row against a registered survival threshold of 0.80.

## C-7 — `P = lr·M` locates a stability transition band

**Status: PARTIALLY SUPPORTED — the threshold is located; sufficiency is not established,
and the original "perfect separation" wording is retired.**

Originally logged from C10M as perfect separation (20/20 stable at `P ≤ 8`, 10/10 divergent
at `P ≥ 16`). Tested in direction C10S (`results/research/c10s/r_c10s_summary.md`) on new
configurations, along six rays holding `M` fixed with `lr = P/M`.

**Registered verdict: H4 INCONCLUSIVE.** Per-row spread across rays = 1.682 against a
survival band of ≤1.25; per-step = 2.378, which would be falsified. Both guards clean:
0 censored, 0 non-monotone, 6/6 rays usable, brackets resolved to a factor of 1.044.

**Located:** `P*_hat = 11.49` per-row (geometric mean), per-ray range [8.67, 14.58], at
150 000 rows per window. Per-step `P*_hat = 9.80`, range [7.29, 17.34].

**AMENDED TWICE.** (a) By C10R (held-out crypto): the 1.68x tightness is **Jane-specific**.
On BTC/USDT the same eight-ray procedure gives `spread_P = 5.75` against `spread_lr = 22.26`.
`P` stays far better than the rate alone on both streams, but its tightness does not
replicate, and 1.68x must not be quoted as a general property.
(b) By C10T: what `P*` locates is a **loss-degradation** threshold, NOT a stability
boundary. `thm:stability` bounds `||w_T|| <= 2*lr*M*sqrt(T)`, so a finite cap makes iterate
divergence impossible; the iterates were bounded at every point on every grid, including
the ones labelled divergent (measured `max||w||` = 59.11 at `P=128`, against a 1e8
threshold). The word "stability" in this entry should be read as "loss stays bounded".

**What is genuinely supported.** `P` compresses a **32×** variation in `M` and a **23.6×**
variation in the critical rate `lr*` into a **1.68×** variation in `P*`. The design made
that hard: at fixed `P` the `M=0.5` ray clips ~57% of steps and `M=16` clips ~0.1%. `P` is
far better than either factor alone, but misses the registered sufficiency tolerance.

**What is retired.** The boundary is a **transition band, not a cliff**. The any-window
criterion marks where the first of ten windows fails; the median-window threshold sits
1.3–1.7× higher. C10M sampled `P` at factor-2 spacing — the width of the band — so it could
not resolve the gradient and separation looked perfect. Post hoc.

**Dominant threat.** The any-window criterion is an extreme-value statistic (minimum over
ten windows), so each `P*` is set by the single most fragile window. This is the likeliest
explanation of the per-row non-monotonicity (`P*` peaks at `M=4`, falls at `M=8, 16`), which
no mechanism predicts. The 1.044 bracket is search resolution, **not** a confidence
interval.

**Trap recorded** (carried from C10M and still standing). The registered secondary statistic
`eta2_P` over all 30 C10M configurations with R² floored at −1 is 0.9873 and would read as
overwhelming support for product sufficiency. It is an artifact of `P` predicting
divergence: floored divergent configurations align by `P` by construction.

## C-8 — Does the *realized* maximum step explain C-7's residual?

**Status: still OPEN and explicitly UNTESTED. The registered test (C10R) was vacuous.**

`P = lr·M` is the *nominal* maximum step, attained only when the clip binds, which for large
`M` is rare. The realized maximum `lr·min(r_q, M)` predicts `P*` rising with `M`.

**Registered verdict was H5 FALSIFIED at `ratio = 1.0000` — and that number is an identity,
not evidence.** Stage 1 selected `q* = max`, and Jane's `r_max = 49.93` exceeds every `M` on
the grid, so `min(r_max, M) = M` and `R ≡ P` identically. The ratio was 1.0000 before any
held-out data was touched.

**Cause: a registration error of mine.** C-8 came from the Jane *per-step* residual; I
registered the stage-1 fit on *per-row*, where the residual is non-monotone and no quantile
can help. A per-step fit would have chosen `q = p99` (spread 2.378 → 1.561, ratio 0.656).

**Post-hoc held-out evidence points the other way.** On crypto — a stream that did not
generate the hypothesis — `P*` rises monotonically with `M` across all eight rays spanning
128x in `M` (6.60 → 37.95), exactly C-8's prediction. With crypto's own `r_p99 = 7.033` the
spread falls 5.75 → 2.49 (ratio 0.433); even `p90` gives 0.730. Both would have survived.
This is post hoc and self-fitted, so it is suggestive, not a test.

**CLOSED AS UNTESTED (C10T, 2026-08-23).** The third-stream test on the synthetic suite
came back **VOID**: all 48 ray x criterion x tail combinations censored, the state-based
criterion right-censoring everything and Jane's `_diverged` left-censoring everything. Both
failures are properties of the criteria, not of C-8 (see C-10). No uncontaminated stream
remains, so the direction closes as registered. C-8 is neither refuted nor supported and
cannot be tested until C-10 is resolved.

## C-9 — The divergence criterion dominates the threshold

**Status: SUPPORTED (registered output of C10R).**

C10R registered two criteria in advance. Under crypto's native rule (peak > 1e3, adopted
unchanged from prior work) **all eight rays are right-censored** — nothing diverges even at
`P = 128`, and the registered rule voids the statistic. Under Jane's `_diverged` the same
eight rays resolve cleanly with thresholds 6.60 → 37.95.

Any threshold reported anywhere in this line of work is a statement about a specific
`_diverged` definition, not about divergence. The inherited criteria were calibrated for
different questions and are not interchangeable.

**STRENGTHENED by C10T.** It is not merely that criteria disagree. On a Student-t(1.5)
stream Jane's rule fires on the **zero predictor** (peak rolling loss 34 627 against a
threshold of 50, because the target has infinite variance), while crypto's rule never fired
even at `P = 128`. And the obvious principled alternative -- iterate blow-up -- is vacuous
for this algorithm family by construction. No criterion in this repository is comparable
across streams.

## C-10 — A stream-comparable divergence criterion is a prerequisite

**Status: OPEN — one step further along. A candidate exists and is NOT accepted.**

Absolute loss thresholds do not transfer across streams (target scale and tail index both
move them), and the state-based alternative cannot fire for a capped method.

**Candidate built (C10C, `scripts/research_divergence.py`).** Everything is measured against
the best constant predictor on the same window, so no per-stream constant survives:
`diverged ⟺ L_model/L_ref ≥ 2 OR Ppeak_model/Ppeak_ref ≥ κ`, κ = 10, with the rolling window
a *fraction* of the stream rather than a fixed 2000 steps.

**Registered verdict: REJECTED** — V4 (non-vacuity) failed on synthetic. V1 reference sanity,
V2 blow-up recall (20/20, 0 missed), V3 monotonicity and V5 κ-robustness all passed.

**The evidence indicts V4, not the criterion.** On synthetic the capped grid genuinely
contains nothing divergent up to `P = 256` (`L_ratio` 0.999→1.152, `max‖w‖` 160.6) while true
blow-ups register at `L_ratio` 2.75e103 — a hundred orders of magnitude of separation. V4
asked "both classes present on every stream", which is a property of the stream × grid, not
of the instrument; on a stream where nothing diverges a correct criterion must return one
class. That is a defect in a test I wrote, and the registered verdict stands regardless: the
suite is not edited in the session that ran it.

**C10C2 respecified V4 and re-validated. REJECTED again — and V4 turned out to be
unfalsifiable, not merely mis-tuned.** Its applicability condition asked whether the capped
grid contains a run with `max‖w‖ > 1e6`; `thm:stability` bounds `‖w_T‖ ≤ 2·lr·M·√T`, so at the
grid's largest `P = 256` the bound is 102 400 / 72 408 / 39 659 on jane / synthetic / crypto
and observed maxima are 276.6 / 160.6 / 128.3. No capped configuration can ever satisfy it.
This is the same error as C10T's `1e8` state threshold, made a second time.

**The conclusion: for capped methods there is no criterion-independent ground truth of
divergence.** The iterates are provably bounded, so divergence for this family is inherently a
loss judgment — which is what the criterion measures. Non-vacuity within the capped grid
cannot be validated against independent ground truth by any construction. Degeneracy is
already excluded without it: always-divergent fails V1, always-stable fails V2, both anchored
on uncapped/OGD probes where `‖w‖` genuinely is unbounded.

**Standing on evidence rather than verdict:** five of six tests pass, including the one blind
test (V6, truncation stability, comparative against the inherited rule). Blind evidence is now
V1/V2/V3/V5 from C10C plus V6 from C10C2. Honest cost recorded: on Jane the new criterion is
slightly *less* truncation-stable than the inherited rule (0.967 vs 1.000), passing on the
registered 0.05 margin rather than by matching.

The next registration should drop V4 with the argument above and keep V6. Until the criterion
passes a suite that can be passed, it is not accepted and must not be used to locate
thresholds.

---

## C-11 — `P*` requires scale drift; it is not a property of the algorithm alone

**Status: SUPPORTED (registered output of C10C).**

Capped SN-OMD does not diverge at any `P ≤ 256` on the synthetic stream, while it does on
Jane and crypto. The synthetic stream is stationary in scale with a static comparator; Jane
and crypto have drifting gradient scale and a moving target. So whatever C-7's `P*` measures
needs that drift, which the synthetic suite lacks by construction. This also explains C10T's
void from a second direction, independently of the criterion problem.

---

## Untouched this phase

`UNTOUCHED` — not examined, status unchanged:

- The stability/divergence partition (OGD 10/10, uncapped endpoint 7/10, bounded
  scale-free 0/10). Those arms were not re-run.
- All theory: `thm:stability`, `thm:regret`, `thm:regretbody`, the Freedman
  measurability argument, `ass:track`.
- The Pass-IV predictable-vs-post-update decomposition (grid accounts for +0.0379 of the
  +0.0378 gap; measurability 0.3%).
- RMSProp/Adam bounded-step finding (`app:adaptive`).
- The tracker bootstrap and Bonferroni analysis (`app:tracker`).
- Every crypto, synthetic, MNIST and GARCH-surrogate result.
