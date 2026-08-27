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

**RESOLVED (C12, 2026-08-24): the full six-method table has been regenerated at matched
budget** (`results/research/c12/`). Reproduction gate perfect — all ten checks on the five
untouched methods at `max|diff| = 0.000000`, so SN-OMD's grid is the only thing that moved.
Per-row, all ten windows: SN-OMD **0.1398 → 0.2359** (+0.0961), moving from 4th to **1st**;
std 0.1095 → 0.0471; worst window −0.1071 → +0.1693. Every other row unchanged to four
decimals. The divergence partition is unchanged (scale-adaptive 7/10, OGD per-step 9/10,
bounded scale-free 0/10) and robust to the accepted C-10 criterion (scale-adaptive 6/10
there). SN-OMD selected `M = 2`, interior, so it did not collapse onto either endpoint.

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

**Status: DISSOLVED ON JANE — false premise there; UNTESTED IN SYNTHETIC.**
On Jane at matched budget it does not: the constant-threshold advantage was a pinned-cap
artifact, and the premise fails. Replaced by C-6 for the Jane mechanism question.

**Scope limit, added 2026-08-26.** The dissolution is real-data only and does not transfer
by construction. The synthetic instance of the same question sweeps no cap at all, so
"matched budget" has no meaning there and the Jane result cannot dissolve it. Whether the
synthetic instance dissolves the same way is a separate, cheap confirmation and is *open*.
Do not read C-5 as closing the question in general.

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

**RESOLVED (C10C3, 2026-08-23): criterion ACCEPTED**, at
`scripts/research_divergence.py`, with qualifications that are load-bearing rather than
decorative.

V4 was dropped **by user decision, not by evidence** — I argued it unfalsifiable for capped
methods and flagged that this is the argument a motivated author produces. V1/V2/V3/V5/V6/V8
all pass.

**V8, the blind test that validates the premise:** a pure change of units on `(y, preds)`
leaves the new criterion's classification identical on 100% of runs, while the inherited Jane
rule changes its answer on 54%–94% (invariant fraction 0.458 jane / 0.236 crypto / 0.062
synthetic). The inherited criteria demonstrably carry units; this one does not.

**V7, the blind diagnostic that indicts my own construction:** across 109 divergent runs on
three streams the peak clause changed **zero** decisions. The criterion is reducible to
`L_ratio ≥ 2` alone; the peak machinery and `κ` carry no weight; and **V5's pass was vacuous**
— zero movement across `κ` is what an inert parameter looks like.

**What the C-10 fix actually was.** `L_ratio ≥ 2` is exactly `R² ≤ −1` against the best
constant, and that clause was *already* scale-invariant (scaling `y` and `preds` by `c` scales
model and baseline error alike). So the inherited rule's failure to transfer was caused
entirely by its absolute `peak > 50` clause, and the repair is to delete it. The peak-ratio
replacement contributes nothing on any stream tested — the real fix is far smaller than the
machinery built around it.

Follow-up, not started: simplify the criterion to its one working clause, or find a stream
where the peak clause earns its place. That is a change to the criterion and needs its own
registration.

---

## C-11 — `P*` requires scale drift; it is not a property of the algorithm alone

**Status: SUPPORTED (registered output of C10C).**

Capped SN-OMD does not diverge at any `P ≤ 256` on the synthetic stream, while it does on
Jane and crypto. The synthetic stream is stationary in scale with a static comparator; Jane
and crypto have drifting gradient scale and a moving target. So whatever C-7's `P*` measures
needs that drift, which the synthetic suite lacks by construction. This also explains C10T's
void from a second direction, independently of the criterion problem.

---

## C-12 — Predictability's measured performance effect is a null, and is not in the manuscript

**Status: SUPPORTED (committed artifact), NOT REPORTED in the paper.**

`research_predictability_check.py` computes a predictable-vs-post-update contrast on the same
rows with a paired circular block bootstrap:

| contrast | value | 95% CI |
|---|---|---|
| code path @ lr=2 (predictable − post-update) | **+0.0001** | [−0.0017, +0.0018] |
| code path @ lr=1 | +0.0009 | [+0.0007, +0.0012] |
| grid @ predictable (lr=2 − lr=1) | +0.0379 | [−0.0855, +0.1613] |
| TOTAL reported gap | +0.0378 | — |

The manuscript cites this script **once** (§E.13, line 1832) and only for the grid effect:
*"puts the grid effect at +0.038 against a total gap of +0.038."* A grep of `iclr2027.tex` for
`predictability_check`, `measurability`, `post-update` and `code path` returns that line and
nothing else.

So measurability — the property distinguishing SN-OMD from normalized-GD, and the one the
Freedman analysis exists to license — has a measured performance effect of **+0.0001 with a CI
spanning zero**. §3 line 305 claims *"predictability of `s_t` buys a high-probability
dynamic-regret guarantee"*, which is a theory claim and stands. The empirical companion — that
it buys nothing measurable — is computed, committed, and absent. Under the charter a null on
the paper's own distinguishing property is evidence to report, not omit.

## C-13 — The variation-adaptive bound already exists; the open object is a switching bound

**Status: SUPPORTED (D1/T1, `theory_notes.md`). The derivation attempt FAILED by its
registered criteria and is recorded as such.**

`thm:regret` already carries the tracker's upward variation `W_s = s_1 + Σ(s_t − s_{t−1})_+`
and the scale-weighted path `P_T^s` as explicit inputs, and `W_s ≈ 6.6·V_σ⁺` is measured. So
there is no `V_σ⁺`-adaptive bound left to derive — the problem is that `W_s` is measured to be
`Θ(T)`. The paper says it: *"The drift is a genuine rate; the tracker controls only its
constant."*

The genuinely open object is the one `Remark D.3` names: a switching bound in the regime count.
Target rate derived and both limits verified: `R_T = Õ(N^{1−1/p}·T^{1/p})`, recovering `T^{1/p}`
at `N=1` and the vacuous `T` at `N=T`.

**Obstruction, located and marked GAP:** naive segmentation fails because `η_t = η/√t` is global
and never re-expands, so each regime pays the full horizon initialization `D²√T/(2η)`, giving
`O(N√T)` — reintroducing the very `√T` the remark wants to escape. A strongly-adaptive wrapper
would resolve it, with three identified sub-problems. **No theorem is asserted.**

## C-14 — The `p ≤ 2` cap in `ass:moment` is the sharper framing of the theory tension

**Status: SUPPORTED.**

`ass:moment` requires `p_t ∈ (1,2]`. Measured Hill `α̂` is **2.43** raw and **≈3.73** causally
normalized. A finite `α`-th moment implies the assumption at any `p ≤ α`, so the assumption is
satisfiable — but only by taking `p = 2`, its ceiling, which is exactly where `Remark D.3`'s
global `T^{1/p+1/2}` becomes the vacuous `T`.

The measurement does not merely fail to help the theorem; **it pins it to its own worst case**,
because the theory's parameter cannot exceed 2 while the data's index does. This is stronger
and more precise than "the measurement empties the theorem", which overstates: at the measured
indices the global exponent is `T^{0.91}` (raw) or `T^{0.77}` (normalized) — sublinear, not
vacuous. Exponent arithmetic verified for `p ∈ {1.2, 1.5, 2.0, 2.43, 3.73}`.

---

## C-15 — The stability partition is robust to the divergence criterion

**Status: SUPPORTED (C12 secondary).**

Regenerating the table reported divergence counts under both the inherited `_diverged` and the
C-10 relative criterion accepted in C10C3:

| protocol | method | inherited | relative |
|---|---|---|---|
| per-row | Scale-adaptive OGD | 7/10 | 6/10 |
| per-step | OGD | 9/10 | 9/10 |
| — | every bounded scale-free method | 0/10 | 0/10 |

The **partition** — bounded scale-free methods stay bounded, scale-dependent ones do not — does
not depend on which criterion is used, which is the load-bearing claim. The exact **count** does:
scale-adaptive per-row differs by one window. So the paper's stability dichotomy survives C-9's
finding that criteria do not transfer, while any specific `k/10` figure should be understood as
criterion-dependent.

---

## C-16 — Matched budget is not uniformly favourable

**Status: SUPPORTED (C12B).**

Applying the same cap-tuning correction to the block-median SN-OMD row:

| protocol | published (cap pinned 5) | matched | held-out change |
|---|---|---|---|
| per-row | 0.2913 (`lr=3, M=5`) | 0.2817 (`lr=3, M=10`) | **−0.0128** |
| per-step | 0.2012 (`lr=2, M=5`) | 0.2420 (`lr=3, M=2`) | **+0.0401** |

Per-row the wider search picks `M=10`, which **wins window 1** (+0.4255 vs +0.4067) and then
**loses held-out** (+0.2657 vs +0.2785) — selection overfitting, demonstrated rather than
hypothesized. Reproduction gate passed (published arm re-runs to 0.2913 / 0.2012 against the
manuscript's 0.29 / 0.20).

**The correction removes a defect in the comparison; it does not reliably improve the method
it is applied to.** C12 gained +0.0961 per-row for plain SN-OMD; C12B loses 0.0128 for
block-median. This is the single-selection-window threat biting concretely, and it should be
stated whenever the matched-budget result is presented.

**Consequence for `tab:replication`:** adopting consistently leaves the paper's honest headline
intact — block-median 0.28 against Cutkosky–Mehta 0.29 still **ties rather than beats**, which
is what the abstract already claims. Cutkosky–Mehta is untouched: its 216-configuration grid is
`lr(9) × τ(6) × β(4)` over three genuinely free parameters, which is correct treatment, not
favouritism.

---

## C-17 — Adoption makes `M` a tuned parameter, and the per-step selection sits on two grid edges

**Status: SUPPORTED (from C12's own boundary flags; found during adoption, 2026-08-24).**

Adopting the matched-budget `tab:replication` changed the table's tuning protocol, not just
its numbers. Two consequences that the adoption commit did not propagate into the manuscript:

1. **`M` is no longer untuned.** The manuscript asserted in four places that the cap is fixed
   at 5 a priori — Limitations, the `app:grid` cap paragraph, the `tab:grid` caption, and the
   `tab:grid` footnote. All four were false after adoption. The honest restatement makes the
   limitation *stronger*: the deployed method carries two tuned parameters, not one.

2. **The per-step SN-OMD selection pins at both grid edges.** `c12_report.json` flags
   `per-step/SN-OMD (M tuned)` with `lr=8 at edge` and `M=0.5 at edge <-- collapsed toward an
   endpoint method`. The adopted caption said "All *accuracy-relevant* optima are interior",
   which is contradicted by the run's own gate output. Per-step therefore wants a cap *toward*
   the `M→0` normalized-GD endpoint, and how far toward is untested — the same preference the
   window-1 sweep found at the floor of the narrower `[2,20]` range. This is a further reason
   the per-step column separates no member of the bounded family, and it is recorded rather
   than defended. The fact itself was not new — `research_state.md` open item 6 recorded the
   same two-edge selection from C10/Q6. The defect was that the adopted caption asserted the
   opposite, and neither the C12 summary nor the adoption commit caught the contradiction.

**Corroboration found in passing.** The ten-window cap sweep (`research_cap_sweep_jane.py`)
puts the block tracker's cap optimum on a plateau at `M=5–7` (0.29) with `M=10` at 0.28. C12B,
selecting `M=10` from **window 1 alone**, measures 0.2817 across the ten — an independent
reproduction of that sweep to 0.002.

**What this does NOT establish.** Nothing about the stability partition, which is unchanged and
cap-value-independent (`thm:stability` holds for any finite `M`). Nothing about the accuracy
claim: block-median 0.28 still ties Cutkosky–Mehta 0.29, as [C-16](#c-16--matched-budget-is-not-uniformly-favourable) records.

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

## C-18 — The paired tracker contrast, re-run at matched budget: the tie holds, the EMA gap does not

**Status: SUPPORTED (C13, `results/research/c13_matched_bootstrap.csv`, 2026-08-26).**

`tab:replication` adopted the C12/C12B matched-budget rows, but the paired across-window
bootstrap behind `app:tracker` was never re-run, so the appendix asserted a `+0.15`
block-over-EMA gap against a table whose own cells differ by `+0.05`. Re-running the identical
statistic on the adopted rows moves three things, and they do not all move the same way.

1. **The block-over-EMA per-row gap falls by roughly two thirds**, `+0.152 → +0.046`
   (`[+0.016,+0.076]`, 8/10). It still clears zero uncorrected.

2. **It no longer survives Bonferroni.** At `α/14` the interval becomes `[−0.006,+0.098]`.
   This is the *per-row* tracker claim — the one the previous text explicitly called
   load-bearing while dismissing two per-step failures as not. That sentence was inverted in
   the manuscript rather than softened: under correction, the block median is **not shown** to
   beat the deployed EMA per-row.

3. **The Cutkosky–Mehta tie survives, which was the open question.** `+0.004 → −0.005`
   (`[−0.036,+0.025]`, 6/10). The nominal lead flips to CM; the interval still straddles zero,
   so the abstract's tie language stands as written and needed no weakening.

Per-step the comparisons *strengthen* — block now clears zero against both the EMA (`+0.028`)
and the fixed-τ clip (`+0.040`), where the pinned-cap run tied both. Recorded with the caveat
it needs: the per-step SN-OMD row is selected at two grid edges (C-17), so it is a truncated
comparator and the gap over it is a lower bound, not a clean measurement.

**Process note.** The stale numbers were caught by an external review, not by the project's own
guards, because no `PAPER_CLAIMS` entry covered the per-row figures. Three guards now do, and
the one guard that did cover the reworded sentence failed correctly when the text changed.

## C-19 — CM's larger budget was a recorded decision, but an undisclosed one

**Status: SUPPORTED — and narrower than first written (corrected 2026-08-26).**

CM is tuned over `(lr, τ, β)` = `9 × 6 × 4 = 216` configurations on window 1, roughly **three
times** the 70 that C12 equalized SN-OMD and the fixed-τ clip at.

**This was not an oversight, and an earlier draft of this entry wrongly implied it was.**
`research_state.md` Session 11 records the decision at the time — *"CM untouched (its 216-config
grid over three genuinely free parameters is correct treatment)"* — with the same reasoning
given below. The research record made the call deliberately.

The real defect is narrower and lives only in the manuscript: the `tab:replication` caption
enumerated every method's budget — SN-OMD and fixed-τ at two parameters, "the threshold-free
methods over lr alone" — and silently omitted the one row fitting neither category, which
happens to be the co-leader. A reviewer auditing the fairness argument would find the gap in
the caption, not in the research.

The decision stands and is now disclosed rather than reversed:

- tuning each method over its own free parameters is the principle the rest of the table
  follows, and CM genuinely has three; and
- the asymmetry runs *against* this paper. A larger window-1 budget is more opportunity to
  overfit the tuning window, so if it biases anything it flatters CM — the row we report
  ourselves as merely tying. The tie should be read as conservative.

What cannot be said from these runs is where CM would place at 70 configurations. That is not
claimed. This is the same defect class as C10/Q6 pointing the other way, and it is the reason
C-18's tie result should not be over-read in either direction.

## C-20 — The switching bound is unavailable on this data, not merely underived

**Status: SUPPORTED (D1B, `results/research/d1b_regime_count.csv`, 2026-08-26). Closes the
open question C-13 left, in the negative.**

C-13 recorded that the genuinely open theory object is Remark D.3's switching bound in the
regime count, with target rate `Õ(N^{1−1/p}·T^{1/p})` derived and verified. D1B checked that
rate's precondition before attacking its three GAP sub-problems, and the precondition fails.

The rate is non-vacuous only if `N` is **sublinear in `T`**; at `N = Θ(T)` it is `Θ(T)` for every
`p`. Measured on the committed scale process by the paper's own definition of a regime, `N` grows
with exponent **1.155–1.240** across two trackers and five per-regime budgets — at least linear,
with Table 6's `β ≈ 1.0–1.25` for `W_s` agreeing as an internal consistency check (see the correction in point 2).

Three things make this a claim rather than an impression:

1. **The reliability rule is pre-existing.** Table 6 already requires `≳50` blocks for the
   analogous `W_s` fit. Applying it here discards 7 of 15 combinations — and every one it
   discards is a *sublinear* one, i.e. it removes the only evidence that would have licensed
   proceeding to the derivation. The filter cuts against the conclusion it supports.
2. ~~**The coherence check passes.**~~ **Withdrawn as corroboration (D1C, S2).** `N` and `W_s`
   do grow at the same measured rate, but that is close to tautological rather than
   confirmatory: `W_s` sums upward moves and `N` counts boundaries declared when those same
   upward moves accumulate past `c`. It is one measurement viewed twice. Kept as an internal
   consistency check; the claim rests on the `N` measurement alone, which is unaffected.
3. **The escape is blocked.** A tracker coarse enough to report few regimes (block median,
   `B=10⁴`, 1–3 segments) fails Assumption D.1's lower bracket, so coarsening the tracker to
   recover sublinearity is not available.

**Consequence, stated against our own interest.** The residual `√T` making `thm:regret`
per-regime is a property of the measured drift, not a gap in the proof — stronger than "left
open" and less flattering. It also closes the route by which the introduction's nonstationarity
reframe could have been redeemed theoretically, which Limitations now says.

**Not closed:** a bound in a different nonstationarity functional, or a stream with rarer
regimes. D1's three GAP sub-problems remain unproven and are now unmotivated on this data.

## C-21 — Prop F.1's discharge of `ass:track` is empty on this data

**Status: SUPPORTED (D1C, `results/research/d1c_propf1.csv`, 2026-08-26). Extends the
C-13/C-20 cluster from "a route is closed" to "a claimed discharge is unavailable".**

Prop F.1 pays for the lower bracket with `O(D·N·W·sup σ_t)`, dominated only when `NW ≪ T^{1/p}`.
Both factors measured for the first time:

- `N` at least linear (C-20), and now also **tracker-free**: non-causal block medians give a
  constant boundary rate (`0.12–0.21` per block, stable as block length runs 50→1000), so the
  linearity is a property of the process, not of our adaptive filters.
- `W ≳ 2×10⁴`, because the blocking step needs blocks longer than the mixing time and the rank
  autocorrelation is still `0.069` at lag 2000.

Asymptotically `NW/T^{1/p} ~ T^{1−1/p}` diverges at every `p ∈ (1,2]` **taking `N = Θ(T)`
exactly**, so the result does not depend on the fitted exponent exceeding 1. At the paper's own
horizon and at `p = 2` — the only value `ass:moment` admits given the measured index (C-14) —
the ratio is 12–46 at the tracker's own `W`, and 3.8×10³–1.4×10⁴ at the `W` the proof requires.

**Falsified in 2 of 18 measurable cells**, both needing `p=1.3` *and* `W=64` together: a tail
heavier than measured and a window shorter than the proof permits. Recorded rather than buried;
they do not rescue the proposition.

**Consequence.** Prop F.1 is correct and empty here. The paper leans on §B.2's *empirical*
discharge, and three claim sites now say so — §3's "discharge under a mild drift model", §F.2's
"the picture the measured gradient scale fits", and §B.2's "is discharged".

**Bears on emptiness, not correctness**, and not on Prop 3.1 (unconditional) or the divergence
partition. Does not reopen C-20.

## C-22 — the stability partition is a statement about *ceilings*, not about divergence per se

**Status: T4 FAILED against its registered success criteria (`results/research/t4_separation.csv`,
2026-08-27). The direction's own falsification condition was already met by committed data.**

**AMENDED 2026-08-27 after review. The condition C-22 fired on was mis-specified, and it was
mine.** As registered it read *"if scale-dependent clipping can be made stable by a rate
schedule alone, the partition is about tuning, not structure."* That could never fail to fire:
any method is stabilised by `η → 0`, and the paper's own `tab:jane` already printed OGD's stable
ceiling at `10⁻²`. I registered a condition that committed data already satisfied, so its firing
carried less information than the T4 write-up gave it. The claim actually worth testing is the
paper's own, and it is a **conjunction** — for scale-dependent methods, stability and
competitiveness do not overlap: rates small enough to stay bounded underfit, and any rate large
enough to be competitive diverges. T4 did not test that; **T4B** does, on the ten-window frozen
instrument. The classification below is unaffected — it rests on Theorems A and B, not on the
condition — but the *verdict* "T4 as framed is falsified" should be read as "T4 asked a question
whose answer was already in the paper", which is a weaker and more accurate statement.

D3/T4 carried the condition *"if scale-dependent clipping can be made stable by a rate schedule
alone, the partition is about tuning, not structure."* It can. Every scale-dependent method has
a strictly positive stable rate in every artifact that measures it — OGD at `1`–`2×10⁻³`,
AdaptiveClip and RobustOMD up to `3×10⁻²` without diverging at all. So the partition is not
"one family diverges and the other does not, for all rate schedules".

**What survives is a classification, and it is a 2×2 rather than the paper's dichotomy.** Two
*independent* properties govern the update `w_{t+1} = w_t − η_t Φ_t`: whether `‖Φ_t‖` is
bounded by a stream-independent constant, and whether `Φ_t` is degree-0 homogeneous
(`Φ_t(λg)=Φ_t(g)`). Boundedness gives stability (Theorem A, a widened Prop 3.1); degree-0 gives
tuning transfer across scales (Theorem B). They are separable, and the measured ceilings
separate the same way: OGD `[0.01,0.02)`, the uncapped endpoint `[1,2)`, SN-OMD `[3,5)`,
normalized-GD `≥8`.

**One genuine gain.** Corollary C — that a degree-1 method's rate must carry a `1/ŝ_t` factor to
bound its displacement uniformly — explains **AdaGrad-Norm**'s membership in the stable family,
which the paper asserts without derivation: it is a degree-1 `Φ` with a degree-(−1) rate, hence
degree 0 overall and bounded by `η`, and it never clips. The same corollary predicts the
fixed-τ clip's anomaly (bounded, so stable, but *not* degree 0, so its useful rate does not
transfer — which is `fig:mechanism`(b)).

**Two GAPs, and the second is fatal to the direction.** GAP 1: Theorem B is proved for a given
gradient sequence; the experiments have feedback (`g_t` depends on `w_t`) and that case is not
covered. GAP 2: there is **no lower bound**. Nothing proves a degree-1 method *must* diverge,
only that its upper bound is loose. A separation needs both halves and only one was obtained,
so this is a derivation strategy with a located obstruction, which the standing commitment says
is not a result.

**The invariant was under-tested, added on review.** T4 checked `P = η_max·B` only *within* the
bounded scale-free family, where normalized-GD's ceiling is censored. Across tiers the dynamic
range in `B` is ~750× and both endpoints are measured. ~~OGD's `P ∈ [11.5, 23.0)` overlaps
SN-OMD's `[15,25)` and the lower endpoint coincides with C10S's `P* = 11.5`.~~ **Withdrawn the
same day it was written.** That used `sup‖g‖ ≈ 1.1×10³` from `gradnorm_at_wstar.npy`, which
`research_findings.py` builds on date`[0,30)` with 200k rows — not the stream the ceilings come
from. `research_t4b_invariant.py` recomputes the gradient norms at `w*` on date`[0,120)`/150k,
the ceilings' own slice, and gets `sup‖g‖ = 752.6`, a factor `1.53` smaller. The corrected
picture is much weaker:

| method | `η_max` | `B` | `P` |
|---|---|---|---|
| normalized-GD | `≥ 8` | 1 | `≥ 8` (**censored**) |
| SN-OMD | `[3,5)` | 5 | `[15.0, 25.0)` |
| OGD | `[0.01,0.02)` | `752.6` | `[7.5, 15.1)` |

The two measured intervals intersect only in `[15.0, 15.1)` — a sliver of width `0.1` that the
grid quantisation cannot resolve — and **C10S's committed `P* = 11.5` falls outside it**. So the
invariant is not confirmed across tiers either; the apparent agreement was an artifact of mixing
two streams, and the coincidence with `11.5` was the artifact's doing. Recorded as a correction
to my own same-session claim.

**Not falsified, and not confirmed:** the `P = η_max·B` invariant. normalized-GD never diverges
on the committed grid, so its ceiling is right-censored at `lr=8` and every `P` built from it is
a lower bound. Taking the censored value at face value would have printed a `1.88×` spread and
a verdict of FALSIFIED against the registered `1.68×` threshold; that verdict would have been an
artifact of the grid ending and is not recorded. Resolving it needs a wider grid — new compute,
hence a separate registration.

**The under-weighted consequence, added on review.** C-23 below was filed as a provenance
defect. It is more than that, because it changes which *axis* predicts divergence:

| method | scale-dependent? | bounded step? | diverges? |
|---|---|---|---|
| OGD | yes | no | **9/10** (per-step) |
| uncapped scale-adaptive OGD | **no** | no | **7/10** (per-row) |
| AdaptiveClip / RobustOMD | **yes** | yes | **none observed**, `R²` 0.14–0.16 |
| bounded scale-free family | no | yes | 0/10 |

**Scale-dependence does not predict divergence; boundedness of the step map does** — which is
exactly what Theorem A says and Theorem B separates from tuning transfer. The paper frames its
central partition on the other axis. This is a correction to the paper's taxonomy, it is proved,
and it is corroborated by the one clean measurement of the row the paper had wrong — but it
rested on a single window until **T4B** put those methods on the primary instrument.

**Bears on** the *explanation* of the partition, not on the partition itself, which is measured
at frozen hyperparameters and is untouched. Not on Prop 3.1.

## C-23 — `tab:jane`'s AdaptiveClip/RobustOMD row is measured on a different stream than its caption states

**Status: SUPPORTED (found by T4 step 0, 2026-08-27). A provenance defect, not a wrong number.**

`tab:jane`'s caption sources the table to the continuous Jane stream. Every other row matches
`normalize_continuous.csv` (date`[0,120)`, 150k rows) — including OGD's `0.018` and its
`≤10⁻²` ceiling, both of which are correct and on-stream. The AdaptiveClip/RobustOMD row does
not: its `∼0.01` matches `fair_tuning.csv` / `lr_sensitivity.csv`, which are date`[0,30)`
windows.

On the one committed artifact that runs those methods on the date`[0,120)` stream
(`continuous_stream.csv`, 300k rows) they reach `R² = 0.14`–`0.16` and **never diverge**, at any
rate in the sweep, which stops at `3×10⁻²`. So the row's `≤10⁻²` ceiling is not located on the
paper's stream, and §5's "any larger rate diverges when the scale spikes" is untested for the
clippers — though it is correct for OGD, which is the method the sentence's evidence actually
covers.

**Neither the clipper row nor the OGD row is covered by a `PAPER_CLAIMS` guard**, which is how
this persisted — the same gap that let the C-18 drift run for two sessions.

**Consequence, and it reversed under T4B (2026-08-27).** The provenance defect is real — the
number was sourced from date`[0,30)` — but **the number itself is right**. T4B ran those methods
on the instrument's own slice (date`[0,120)`, 150k) and got best per-row `R²` of `0.0129`
(AdaptiveClip) and `0.0143` (RobustOMD), with the ceiling located at `[10⁻², 2×10⁻²)`. `tab:jane`
printed `∼0.01` and `≤10⁻²`. Both confirmed.

So my T4 edits removed correct claims on incomplete evidence, and are **restored**: §5 again
covers the clippers, and the row again carries its ceiling, now with an on-stream measurement
behind it. The dagger stays, but it now records where the ceiling was measured rather than that
it was missing. The `0.14`–`0.16` figure that prompted all this is from `continuous_stream.csv`
at **300k** rows and does not reproduce at the instrument's 150k — a single-window artifact,
exactly as T4B's decision rule anticipated it might be.

## C-24 — the taxonomy correction does NOT survive the primary instrument; the paper's axis holds

**Status: H_T4B FALSIFIED (`results/research/t4b_clipper_windows.csv`, 2026-08-27). The outcome
that vindicates the manuscript as written, and it is reported first.**

T4 argued that scale-dependence does not predict divergence and boundedness does, on the
strength of one single-window run in which AdaptiveClip and RobustOMD reached `R²` 0.14–0.16
without diverging. T4B put those two methods through the ten-window frozen instrument — the one
carrying every other stability claim, which had never run them — at the matched one-dimensional
budget, same windows, same tune-then-freeze protocol, same divergence criterion.

| | per-row | per-step |
|---|---|---|
| AdaptiveClip | `0/10` diverged, mean `R² = −0.010` | **`9/10` diverged** |
| RobustOMD | `0/10` diverged, mean `R² = −0.007` | **`9/10` diverged** |
| OGD (committed) | `0/10`, mean `+0.001` | **`9/10` diverged** |
| bounded scale-free pack | `0/10`, `0.14`–`0.21` | `0/10`, `0.09`–`0.20` |

**The clippers land with OGD, not with the bounded family** — an identical `9/10` per-step
divergence count, and a per-row mean *below* OGD's and an order of magnitude below the pack's.
The paper's partition is on the right axis after all.

**Why the theory already said so, and I misread it.** A scale-dependent threshold is bounded by
`c·ŝ_t`, which is *not* a stream-independent constant, so Theorem A's hypothesis never covered
the clippers. T4's own 2×2 places them in the degree-1 **unbounded** cell with OGD. The claim
that they were "bounded" came from reading a finite `sup_t ŝ_t` on one window as if it were a
constant of the method. It is not: it is a property of that window.

**What T4B does confirm is Theorem B.** Degree-1 homogeneity predicts that a rate tuned on one
window's scale need not survive a window whose scale differs, and that is exactly the per-step
result — the clippers tune to `lr = 5×10⁻³` on window 1 and then diverge on nine of ten. The
bounded scale-free family, degree 0, transfers at `0/10`. That is the prediction being borne
out on the primary instrument, and it is the half of T4 worth keeping.

**Ceilings located, closing C-23's open item.** Per-row `[10⁻², 2×10⁻²)`; per-step
`[5×10⁻³, 10⁻²)`.

**Does not touch** GAP 2 — still no lower bound and still no separation theorem.
