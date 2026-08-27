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

## Session 7 — direction C10C2, correcting V4 (REJECTED again)

**Registered verdict: REJECTED.** V1, V2, V3, V5 pass; **V6 (new and blind) passes**; V4
fails -- and this time V4 turned out to be unfalsifiable rather than mis-tuned. Write-up:
`results/research/c10c2/r_c10c2_summary.md`.

**The same error twice.** V4's applicability asked for a capped configuration with
`max||w|| > 1e6`. `thm:stability` bounds `||w_T|| <= 2*lr*M*sqrt(T)`, so at the grid's largest
`P = 256` the bound is 102400 / 72408 / 39659 and observed maxima are 276.6 / 160.6 / 128.3.
Unreachable by three to four orders of magnitude -- the same class of error as C10T's `1e8`
state threshold, which I had already diagnosed and written up before repeating it.

**V6, the one blind test:** truncation agreement new vs inherited -- synthetic 1.000/1.000,
crypto 0.983/0.983, jane 0.967/1.000. Passes on the registered 0.05 margin, but on Jane the
new criterion is genuinely *less* stable than the inherited rule, which is a real cost and is
reported as one.

**Conclusion that follows:** for capped methods there is no criterion-independent ground truth
of divergence, because the iterates are provably bounded. V4 should be dropped, not retuned.
Not done here -- the registration forbids patching in the session that ran the test, which is
exactly the rule that matters when I have a clean argument for a change that also makes my
own instrument pass.

## Session 8 — direction C10C3, dropping V4 (ACCEPTED, with qualifications)

**Verdict: criterion ACCEPTED.** V1/V2/V3/V5/V6/V8 pass. Write-up:
`results/research/c10c3/r_c10c3_summary.md`.

**V8 (blind, the property C-10 exists for).** A pure change of units on `(y, preds)` leaves
the new criterion identical on 100% of runs; the inherited Jane rule changes its answer on
54-94% (invariant fraction 0.458 / 0.236 / 0.062). The unit-carrying failure is now measured
rather than argued.

**V7 (blind diagnostic, and it indicts my own construction).** Across 109 divergent runs the
peak clause changed ZERO decisions. The criterion reduces to `L_ratio >= 2` alone, the peak
machinery and `kappa` carry no weight, and V5's pass was VACUOUS -- zero movement across
`kappa` is what an inert parameter looks like.

**What the fix actually was.** `L_ratio >= 2` is exactly `R2 <= -1` against the best constant,
and that clause was already scale-invariant. The inherited rule's failure to transfer came
entirely from its absolute `peak > 50` clause; the repair is to delete it. The peak-ratio
replacement I built contributes nothing.

**Qualifications carried forward:** V4 was removed by user decision rather than evidence; only
V1/V2/V3/V5 (C10C), V6 (C10C2) and V8 (here) were blind when run; V6 is a marginal pass on
Jane (0.967 vs the inherited 1.000); amendment A1's 40000-row Jane cap applies throughout.

## Session 9 — direction D1/T1, variation-adaptive dynamic regret (FAILED, registered)

**Outcome: FAILURE against the registered success criteria** -- criterion (a), a complete
written proof, is not met. Recorded in `theory_notes.md` with the obstruction located, and the
theory contribution demoted rather than defended, per the registered failure path.

**Two findings worth more than the attempt.**

1. *The registered objective was already met.* `thm:regret` already carries `W_s` (tracker
   upward variation, ~6.6 V_sigma+) and `P_T^s` as explicit inputs. There is no
   variation-adaptive bound left to derive; the problem is that `W_s` is measured to be
   `Theta(T)`. The open object is the switching bound `Remark D.3` names.
2. *The `p <= 2` cap in `ass:moment` is the sharper framing.* Measured Hill alpha is 2.43 raw
   and ~3.73 normalized, so the assumption is satisfiable only at `p = 2`, its ceiling -- which
   is exactly the vacuous corner. The measurement pins the theorem to its worst case rather
   than merely failing to help it. Ledger C-14.

**Derived and verified:** target switching rate `N^(1-1/p) T^(1/p)`, both limits correct
(`N=1` gives `T^(1/p)`, `N=T` gives the vacuous `T`), Holder tightness checked over 20000
random splits. **Obstruction:** `eta_t = eta/sqrt(t)` is global and never re-expands, so each
regime pays the full horizon initialization and naive segmentation gives `O(N sqrt(T))` --
reintroducing the `sqrt(T)` the remark wants to escape. Needs a strongly-adaptive wrapper;
three sub-problems identified; marked GAP; no theorem asserted.

**Also settled this session:** the brief's D2 is CLOSED by ledger C-1 (the constant-scale
advantage is a tuning artifact and reverses at matched budget), D3 is partly undercut by C10S,
and D4 is not actionable. The section 2.3 check found a null on predictability that is absent
from the manuscript -- ledger C-12.

## Session 10 — direction C12, tab:replication at matched budget (complete)

**Result: SN-OMD moves from 4th to 1st on the paper's own headline table**, purely by tuning
the cap it already has over the same 70 configurations its comparator already received.
Write-up: `results/research/c12/r_c12_summary.md`.

Per-row, all ten windows: SN-OMD **0.1398 -> 0.2359** (+0.0961), std 0.1095 -> 0.0471, worst
window -0.1071 -> +0.1693. **Every other row unchanged to four decimals**, and the reproduction
gate passed all ten checks at `max|diff| = 0.000000` -- so the only thing that moved is the one
grid that was defective.

**None of the three registered surprises occurred.** SN-OMD selected `M = 2`, interior, so it did
not collapse onto normalized-GD (`M->0`) or scale-adaptive OGD (`M->inf`). The divergence
partition is unchanged (scale-adaptive 7/10, OGD per-step 9/10, bounded scale-free 0/10). The
untouched methods reproduced exactly.

**Secondary, and substantive:** the partition is robust to the accepted C-10 criterion
(scale-adaptive 6/10 there rather than 7/10), so the stability dichotomy is not an artifact of
the inherited absolute threshold -- though the exact count is criterion-dependent. Ledger C-15.

**No manuscript edit.** The paper's `windows_replication*.csv` are untouched, so its current
numbers and the guard pinning them both still hold.

## Session 11 — direction C12B, block-median at matched budget (complete)

**Reproduction gate passed** (published arm re-runs to 0.2913 / 0.2012 against the manuscript's
0.29 / 0.20), so the comparison is sound.

**Matched budget is NOT a free win.** Per-row it makes block-median *worse* on held-out data:
the wider search picks `M=10`, wins window 1 (+0.4255 vs +0.4067) and loses held-out (+0.2657
vs +0.2785). Per-step it helps substantially (+0.2012 -> +0.2420 all-ten). Ledger C-16.

This is the single-selection-window threat biting concretely rather than hypothetically, and it
must be stated whenever the matched-budget result is presented.

**The table can now be adopted consistently.** Both SN-OMD rows at matched budget, CM untouched
(its 216-config grid over three genuinely free parameters is correct treatment). The paper's
honest headline survives: block-median 0.28 vs CM 0.29 still ties rather than beats, exactly as
the abstract says.

## Session 12 — C13, the paired contrast re-run at matched budget (complete)

Prompted by an external revision assessment, not by our own guards. That is the process
finding: `tab:replication` adopted the C12/C12B rows in Session 10/11, but the paired
across-window bootstrap behind `app:tracker` was never re-run, so the appendix asserted a
`+0.15` block-over-EMA gap against a table whose own cells differ by `+0.05`. Three passages
carried stale numbers for two sessions.

**The re-run needed no new compute.** `c12_matched.csv` and `c12b_blockmed.csv` already hold
per-window values for every adopted row, and `windows_cm.csv` holds CM's, on identical window
definitions. `research_c13_matched_bootstrap.py` recomputes
`research_tracker_bootstrap.py`'s statistic on them — same floor, same pairing, same t and
percentile intervals — so only the input changes.

**The tie holds; the tracker claim does not.** Block over CM per-row: `+0.004 → −0.005`,
CI `[−0.036,+0.025]`, 6/10. The nominal lead flips to CM and the interval still straddles zero,
so the abstract's tie language stands as written — this was the open question and it resolved
in the paper's favour. Block over the EMA default per-row: `+0.152 → +0.046`, still clearing
zero uncorrected but **failing the subsection's own Bonferroni correction**
(`[−0.006,+0.098]`). That is the per-row tracker claim, which the previous text called
load-bearing while dismissing two per-step failures as not. Ledger C-18.

**Per-step strengthened**, block now clearing zero against both the EMA and the clip where the
pinned-cap run tied both — recorded with the caveat that the per-step SN-OMD row sits at two
grid edges (C-17), so it is a truncated comparator.

**Two things found while checking, neither in the assessment.** CM's 216-config budget is
undisclosed in the `tab:replication` caption though deliberate in the research record (C-19),
and `research_predictability_check.py`'s measurability arm is a direct measurement of what
predictability costs in accuracy (`+0.0001` to `+0.0009`) — the paper's own framing claim,
until now asserted rather than shown. Both are now in the manuscript.

**Guards.** No `PAPER_CLAIMS` entry covered the per-row figures, which is why the drift went
unnoticed; three now do. The one guard that did cover a reworded sentence failed correctly.

## Session 13 — direction D1B, the switching bound (registered; closed NEGATIVELY)

The external assessment ranked "D1 — variation-adaptive bound" highest. The naming was wrong and
the record already said so: C-13 established that bound already exists inside `thm:regret`. The
open object was Remark D.3's switching bound, so that is what D1B registered.

**Registered a premise check first, and it settled the direction.** The target rate
`Õ(N^{1−1/p}T^{1/p})` is non-vacuous only if the regime count `N` is sublinear in `T`. Measured
on the committed scale process with the paper's own definition of a regime: exponent
**1.155–1.240** over the eight tracker × budget combinations with enough segments to fit one.
At `N = Θ(T)` the switching rate is `Θ(T)` at every `p`.

**So the bound is unavailable, not underived** — no proof of that form can help here. D1's three
GAP sub-problems were not attempted, per the registered decision rule, and are now unmotivated
on this data. Ledger C-20.

**The reliability rule was Table 6's own** (`≳50` blocks), and it discards exactly the
combinations that looked sublinear — it makes the conclusion harder to reach. That is the test
for whether a post-hoc filter is legitimate: this one costs us the outcome that would have let
us keep working.

**Manuscript.** Five places said "left open"; they now say closed, with the measurement in a new
appendix subsection. Limitations concedes that the per-regime restriction is not a gap we expect
to close. Main text 8.907 → 8.942pp.

## Session 14 — direction D1C, propagating D1B into Prop F.1 (registered; H_D1C survives)

D1B closed a route the paper listed as open. D1C asked whether the same measurement voids
something the paper presents as *discharged*, which is the more consequential question, and it
does.

**Prop F.1's domination condition fails.** `NW ≪ T^{1/p}` needs both factors small; neither is.
`N` is at least linear, and `W ≳ 2×10⁴` because the blocking argument needs blocks longer than
the mixing time — the rank autocorrelation is still `0.069` at lag 2000. Asymptotically the ratio
diverges at every `p ∈ (1,2]` **evaluated at `β = 1` exactly**, so it does not lean on the fitted
exponent. At `T = 200 000` and `p = 2` it is 12–46 at the tracker's own window and up to
1.4×10⁴ at the required one. Ledger C-21.

**Falsified in 2 of 18 cells**, both requiring `p=1.3` and `W=64` simultaneously — a heavier tail
than measured and a shorter window than the proof allows. Reported, as registered.

**S1 closed and it strengthens the result.** A tracker-free segmentation (non-causal block
medians) gives a constant boundary rate across block lengths 50→1000, so linear `N` is a property
of the process rather than of our adaptive filters.

**Two corrections to my own D1B write-up.** S2: the `W_s`/`N` agreement was claimed as
independent corroboration and is close to tautological — one measurement twice; withdrawn as
corroboration everywhere, kept as an internal consistency check, and the `N` claim is unaffected.
S3: "a coarse tracker fails the bracket" was overstated as a binary; Table 6 shows the `B=10⁴`
tracker holds it at 0.93, and the honest argument runs through the exceptional-set accounting —
7% of rounds at `O(D sup σ)` is `Θ(T)`, the same wall.

**Manuscript.** Three claim sites revised, none longer than what it replaced (main text
unchanged at 8.942pp), plus the measurement appended to the appendix subsection D1B created.

### Candidate framing, recorded and NOT acted on

Two independent measured obstructions now stand: `W_s = Θ(T)` and `N ≥ Θ(T)`. Together they say
this class of stream has **no macroscopic regime structure at any resolution that preserves the
bracket**. With the central measurement that the tails are removable, the finding would be: *the
difficulty is a scale process with no exploitable structure at any timescale — neither heavy
tails nor regimes.* That is sharper and more falsifiable than Theorem 3.2, and it is reached by
evidence rather than retreat. **Do not rewrite the paper around this yet**; T4 and any further
propagation resolve first. If it is adopted, the page it needs should come from Theorem 3.2's
body presentation, whose per-regime restriction is now conceded as permanent rather than pending.

### T4 is now the last live theory direction

The switching route is closed and Prop F.1's analytical discharge is empty. T4 — conditions on
the scale process under which bounded scale-free methods provably beat scale-dependent ones —
is the one remaining route to a non-vacuous theory contribution, and nothing measured so far
obstructs it. The stability partition it would explain (0/10 vs 9/10 per-row, replicated on
crypto with frozen hyperparameters) is still the sharpest unexplained empirical result here.

## Session 15 — direction T4, the separation theorem (registered; FAILED, and it was pre-falsified)

T4 was the last live theory direction. It is now closed, and the registration is the reason
the closure is trustworthy: it was written to be adversarial to its own direction, with step 0
placed first precisely because I suspected the direction was already dead.

**Step 0 killed it.** D3/T4's own falsification condition — "if scale-dependent clipping can be
made stable by a rate schedule alone, the partition is about tuning, not structure" — was
already met by committed data. Every scale-dependent method has a positive stable rate in every
artifact measuring it. The clippers do not diverge anywhere in the paper's own sweep. Ledger
C-22.

**What survives is a 2×2, not the paper's dichotomy.** Boundedness of the step map and degree-0
homogeneity are *independent* properties: the first gives stability (Theorem A), the second
gives tuning transfer (Theorem B). The successor H_T4' proposed three tiers by degree and was
itself not quite right — the fixed-τ clip is homogeneous of no degree yet bounded, a cell the
registration missed. Correcting it is an improvement, and it is recorded as a correction.

**One real gain.** Corollary C explains AdaGrad-Norm's membership in the stable family, which
the paper asserts without derivation: degree-1 `Φ` with a degree-(−1) rate is degree 0 overall
and bounded, and it never clips. It also predicts the fixed-τ clip's anomaly.

**Two GAPs, the second fatal.** No feedback case, and — decisively — **no lower bound**. Nothing
proves a scale-dependent method must diverge. That is a derivation strategy with a located
obstruction, which is not a result.

**A defect found on the way.** `tab:jane`'s AdaptiveClip/RobustOMD row is measured on
date`[0,30)`, not the continuous stream its caption names; on that stream the same methods reach
`0.14`–`0.16` and never diverge. OGD's row is correct and on-stream. Ledger C-23. Neither row
was guarded.

**An error I made and caught.** My own step-2 code took the largest non-diverged grid point as
`η_max` without checking whether the method diverged *anywhere*. normalized-GD does not, so its
ceiling is right-censored, and the uncorrected code would have reported a `1.88×` spread and a
FALSIFIED verdict that was an artifact of the grid ending. Fixed before the result was recorded;
the invariant is INCONCLUSIVE, not falsified.

### There is now no live theory direction

D1/T1 failed. D1B closed the switching bound negatively. D1C emptied Prop F.1's analytical
discharge. T4 is pre-falsified and yields a classification, not a separation. Every route to a
non-vacuous *theorem* that this repository has registered is now closed or incomplete, and the
honest reading is that the contribution here is measurement-first. That is precisely the
condition Session 14 recorded as the gate on the **Structure C** reframe, and the gate is now
open — it is the author's call whether to take it, not a decision this session should make
unilaterally.

## What is now open

1. **Simplify the criterion to its one working clause**, or find a stream where the peak
   clause earns its place. V7 showed it inert across 109 divergent runs. That is a change to
   the criterion, so it needs its own registration rather than an edit in the session that
   found the redundancy.
2. **Relocate `P*` under the accepted criterion** (ledger C-7). This is what C-10 was built
   to unblock, and it is now unblocked. Given the pattern of the last three registrations,
   state explicitly BEFORE choosing any threshold whether the quantity it applies to is one
   `thm:stability` already bounds.
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
7. ~~**Re-run the full ten-window table at matched budget.**~~ **Closed 2026-08-26 on
   inspection, not by a re-run.** The premise was wrong: `c12_matched.csv` carries all six
   non-CM methods, each with the `n_configs` it was tuned over (OGD 5, AdaGrad-Norm 8,
   normalized-GD and the uncapped endpoint 10, fixed-τ and SN-OMD 70). The smaller budgets
   are each method's whole parameter space, so there is nothing to equalize. CM's 216 is the
   one genuine asymmetry and is now disclosed in the paper (ledger C-19).

## Directions not taken

- **T1** (variation-adaptive dynamic-regret bound) and **T4** (formal separation for
  bounded scale-free methods) — both untouched, both still the only routes to a
  non-vacuous theorem.
- **E2** (synthetic phase diagram) — untouched; still the cheapest route to a
  "when does this help" boundary, and data-free, hence reviewer-reproducible.
- **R1c** — not actionable in this repository.
