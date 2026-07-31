# Audit findings (internal — strip before public release)

Rule followed: check the data first, then make the text match the data; never soften a
supported claim; run the script before propagating a number; suspect flattering results.

Verification scripts added: `scripts/research_audit_checks.py` (A3, A7). Run:
`python scripts/research_audit_checks.py --a7`. Output archived reasoning below.

## PART A

### A3 — round count wrong; slope reproduces once fixed  [FIXED]
- **What was wrong:** Table 3 caption + Sec 4.3 say the process is "357k rounds". The
  reproducing array `gradnorm_at_wstar.npy` is **200,000** rounds. Using 357k, W_s/(T/B)
  gives ~0.9 and the "1.7" matches nothing (the reviewer's observation).
- **What the data says (N=200,000):** W_s/(N/B) = 9.14, 1.61, 1.60, 1.62, 1.43 for
  B = 1, 100, 1e3, 3e3, 1e4; linear-fit slope of W_s vs update-count = 9.91, 1.72, 1.74,
  1.74, 1.59 with R² = 0.99, 0.99, 0.99, 0.98, 0.87. So for **B≥100 the slope is ~1.7,
  R²≈0.98–0.99** (claim correct); **B=1 is a ~5.7× jitter outlier** (different mechanism).
- **Fix:** 357k → 200,000 everywhere; state the ~1.7 slope holds for B≥100 (R²>0.98) and
  exclude B=1 as per-round jitter.

### A4 — beta overstated  [FIXED]
- **What was wrong:** text said "β≈1 throughout"; the honest per-block β (log-log fit over
  horizons with ≥50 blocks) is **1.23, 1.03, 1.25, 0.73, n/a** for B = 1, 100, 1e3, 3e3, 1e4.
- **What the data says:** reliable estimates (many blocks: B=100, 1e3) are 1.03 and 1.25;
  B=3e3 (0.73) is on ≤~1 decade of horizon (≤66 blocks) and noisy; **B=1e4 is n/a because
  20 blocks never reach the ≥50-block asymptotic window in a 200k record.** No monotone
  trend (vs the naive full-range fit's spurious decline to 0.17).
- **Fix:** replace "β≈1 throughout" with the honest range (≈1.0–1.25 where reliable) and
  the n/a explanation; keep the robust evidence (linear W_s-vs-update-count) as the primary
  argument, β as corroboration.

### A7 — block tracker does NOT destabilize (and is more accurate)  [FIXED + FLAG]
- **Ran** B=1e4 block-median-tracker SN-OMD (cap=5) vs the default winsorized-EMA across
  lr∈{0.05..2} on the causal continuous stream (150k rows). Peak rolling loss for the block
  tracker: 5.2, 5.2, 5.3, 5.1, 4.7, 3.9 — **bounded throughout, no destabilization.** R²:
  0.046, 0.075, 0.120, 0.211, 0.299, 0.380 (vs EMA 0.034…0.285). At lr=2 the block tracker
  is more accurate AND more stable (peak 3.9 vs EMA's 8.1).
- **Fix:** add the promised sentence connecting the lower-bracket dip to the W_s shrink, and
  report that the regime-timescale tracker stays bounded (in fact improves) in the sweep.
- **FLAG (claims-relevant):** this contradicts Appendix B.8's line that the smoother tracker
  under-fits relative to the EMA. Softened B.8; see Part D.

### A1 — "drift enters as sqrt(W_s), not as a rate" survivor  [FIXED]
- **What was wrong:** Appendix B's final display and surrounding prose still said the drift
  enters "not as a rate," and annotated the W_s = O(1) substitution as if it held. It does
  not: W_s ~ T (A3/A4). This contradicted Remark A.3.
- **What the data says:** W_s is linear in the update count (slope ~1.7, R²>0.98 for
  100≤B≤3000), so sqrt(W_s) ~ sqrt(T) is a genuine rate; T^{1/p} is per-regime only.
- **Fix:** rewrote the B display to drop "not as a rate," and annotated the W_s=O(1) step
  as FAILING on our data (W_s ~ T). Remark A.3 now reads "at p=2 the bound is the vacuous
  T; content is strictly per-regime." Grep confirms no "not as a rate"/"drift is constant"
  survivors remain.

### A2 — Theorem A.2 false second display  [FIXED]
- **What was wrong:** the theorem's second display substituted W_s ≤ sup_t sigma_t as if
  bounded, giving a clean T^{1/p}; at p=2 that is T^{1/2}·(drift), and with W_s~T the honest
  exponent is T (vacuous), not T^{1/2}.
- **Fix:** added an inline annotation that the boundedness assumption "fails on our data,
  where W_s ~ T," and that the clean rate is per-regime. The theorem statement is unchanged
  (it is correct as a conditional statement); the misleading "therefore T^{1/p} globally"
  reading is removed.

### A5 — conclusion "pushes dynamic regret well above sqrt(T)"  [FIXED]
- **What was wrong:** the conclusion asserted the drift "pushes dynamic regret well above
  sqrt(T)", contradicting §2.1, which now treats the super-sqrt-T budget as a *heuristic*
  that collapses after normalization.
- **Fix:** reworded to "motivates why a moving comparator under such drift is hard (we do
  not lean on it: its super-sqrt-T growth is driven by pooled-tail regimes that vanish after
  normalization)." Grep confirms no "well above sqrt"/"pushes dynamic regret" survivors.

### A6 — copy-level fixes  [ALL FIXED]
- Table 1 header: "bounded to lr=2" → "bounded; stable lr per row".
- "Two caveats" → "Three caveats" (§2.1 lists three).
- Limitations "two gaps" → "three gaps".
- Software/Data: rewritten as a whole sentence naming the Jane Street primary data and the
  MNIST second-domain gradient norms (was a mid-sentence fragment omitting MNIST).
- Contribution √T line break: moot after the theory demotion (the bullets no longer carry a
  √T term; rewritten mechanism-first).
- "2.4→3.7" unified to "2.4→2.9–3.7" everywhere (matches the estimator-dependent range).
- §5 "prove" → "show" (we do not prove the mechanism; we demonstrate it).

## PART B — systematic audit

### B1 / B3 — number provenance and claim→evidence map
Every load-bearing number was re-derived from its script this pass (✓ = re-run and matched
this session; commit = last reproduced in that commit, script unchanged):

| Claim (paper) | Value | Script | Status |
|---|---|---|---|
| pooled gradient tail | α̂≈2.4 (2.43) | research_review_checks.py / research_normalize.py | commit dc7b7b9 |
| residual, feature factors | α̂≈4 each | research_review_checks.py | commit dc7b7b9 |
| normalized gradient tail | α̂≈2.9–3.7 (EMA 3.7, median 3.2, trailing 2.9) | research_normalize.py | commit dc7b7b9 |
| exogenous feature-norm control | 2.4→2.9 | research_review2_checks.py / review3 | commit dc7b7b9 |
| gradient scale drift | ~6× | research_nonstationarity.py / research_continuous.py | commit dc7b7b9 |
| Table 1 R² (per-row/per-step) | OGD .018/.139, normGD .197/.316, scale-adaptive .162/.080, SN-OMD .285/.309 | research_batched_check.py | commit 03e1adb |
| uncapped diverges lr≥2 | R²→−63 | research_batched_check.py | commit 03e1adb |
| synthetic cap interior optimum | ~240× vs uncapped, ~10× vs normGD (p=1.5, M≈0.5) | research_synthetic.py | commit dc7b7b9 |
| synthetic exponents 2→1.3 | 0.37→0.70→1.55; dyn-regret exp ≈0.43 | research_synthetic.py | commit dc7b7b9 |
| stationary negative control | 6.6 vs 5.6e-4, 18% gap, 400 seeds; 0.013–0.015 vs 0.02 | research_synthetic.py | commit 3707d5f |
| MNIST | 2814 steps; pooled α̂≈2.6; normalized ≈6; mid-window 6–9 | research_second_domain.py + research_review4_checks.py | ✓ (review4) |
| A3 W_s vs B | 200k rounds; slope 1.72/1.74/1.74/1.59, R² .99/.99/.98/.87; W_s/(T/B) 9.14/1.61/1.60/1.62/1.43 | research_audit_checks.py | ✓ |
| β (≥50 blk) | 1.03/1.25/0.73/n.a. (B=100/1e3/3e3/1e4) | research_review4_checks.py / research_audit_checks.py | ✓ |
| tab:beta W_s(full) | 1.8M/3216/319/108/29 | research_review3_checks.py | ✓ |
| tab:beta lower bracket | 0.72/0.97/0.97/0.92/0.93 | research_review3_checks.py | ✓ |
| tab:tracker | env 6.6× W_s/Vσ⁺ @100% bracket / 4.2k; slow 7.9×/0.99/5.0k; fast 60×/0.93/38.6k | research_tracker.py | ✓ (see B5) |
| A7 block tracker sweep | peak loss ≤5.3; R² up to .38 (> EMA) | research_audit_checks.py --a7 | ✓ |

No number in the body was found without a producing script. (The Kaggle leaderboard number
is deliberately absent — unverifiable; the paper quotes no competition score.)

### B2 — cross-reference integrity
Final compile: **0 undefined citations, 0 undefined references, 0 cref warnings.** The four
new econometrics citations resolve. thmtools sibling numbering intact (Thm 3.1 body, Thm A.2
appendix).

### B4 — stale-framing sweep
Grep for "matching lower bound", "information-theoretic(ally)", "W_s^{1-1/p}", "drift is
constant", "drift enters as a constant", "not as a rate", "357", "β≈1 throughout", "well
above sqrt", "pushes dynamic regret": **no survivors.**

### B5 — tables-vs-text consistency  [2 FIXES]
- **A3 R² range:** text said "for B≥100 ... R²≈0.98–0.99", but B=1e4 (still ≥100) has slope
  1.59, R²=0.87 on only 20 blocks. Tightened to "for 100≤B≤3000 ... R²≈0.98–0.99; the slope
  persists (≈1.6) at B=1e4 but the fit is noisier there (R²≈0.87, 20 blocks)."
- **tab:tracker ratios (stale pre-causal numbers):** the paper's 6.7/8.1/62 matched the
  *committed* tracker_a1.csv (6.73/8.07/62.26), but that CSV was generated **before the
  causal-standardization fix**. The pipeline is deterministic (ridge solve + causal load, no
  RNG; re-ran twice, identical), and under the current causal code research_tracker.py gives
  W_s/V_σ⁺ = 6.644/7.915/60.492 (envelope/slow/fast). So the table numbers were never
  refreshed after the leakage fix. Corrected the table and all five text occurrences to
  6.6/7.9/60 and regenerated tracker_a1.csv + fig4_tracker.png. The W_s values
  (4.2k/5.0k/38.6k) and brackets (1.00/0.99/0.93) round the same either way.
- Table 1 vs text (0.29/0.31, 0.20/0.32, 0.02→0.14, 0.162→0.080, R²≈0.08–0.32): all
  consistent, no change.

## PART C — prior art (scale mixtures / stochastic volatility)
- **References verified to EXIST (not invented):**
  - Clark (1973), Econometrica 41(1):135–155 — mixture-of-distributions / subordinated
    process → finite-variance fat tails. Web-verified.
  - Andersen, Bollerslev, Diebold, Ebens (2001), J. Financial Economics 61:43–76 — returns
    *standardized by realized volatility* are approximately Gaussian. Web-verified; states
    our exact claim for returns.
  - Engle (1982), Econometrica 50(4):987–1007 (ARCH); Bollerslev (1986), J. Econometrics
    31(3):307–327 (GARCH) — canonical time-varying conditional variance. Canonical, details
    from standard bibliography (not separately web-fetched).
  - Added to `paper/refs.bib` as clark1973, engle1982, bollerslev1986, andersen2001.
- **Related Work paragraph added** ("Scale mixtures and volatility models", §5): states the
  drift-manufactures-heavy-tails mechanism is classical **for asset returns**, claims no
  novelty for the mechanism, then states our precise contribution as (i) it holds for the
  loss GRADIENTS of an online learner (governs optimization, not modeling); (ii) it is an
  INTERACTION effect (feature×residual); (iii) the algorithm-design consequence
  (cap-interpolation frontier), which the volatility literature does not address.
- **§1 reframed:** added a sentence conceding the mechanism is classical for returns and
  restating the contribution as (i)/(ii)/(iii). No novelty is claimed for the mechanism
  itself anywhere after this pass.

## Claims-changing list (surface, per Part D — not silently fixed)
1. **A7 revised old Appendix B.8 (now A.8), then the 2nd pass tightened it.** The old A.8
   claimed the EMA was more accurate and the smoother envelope underfit. First pass overturned
   that (block "more accurate"); the **2nd pass walked *that* back too**: block > EMA is *not*
   significant (t≈1.3, 8/10 folds). Net: A.8 no longer asserts EMA superiority OR block
   superiority-over-EMA; it says the trackers are indistinguishable within fold noise, cites
   §4.3, and states the prove-vs-deploy gap explicitly (item 4 below).
2. **Part C narrows the novelty claim.** The paper now explicitly concedes the
   scale-mixture / stochastic-volatility mechanism is classical *for asset returns* and
   claims novelty only for (i) gradients / (ii) the interaction effect / (iii) the
   algorithmic consequence. This is a deliberate reduction in claimed novelty, not a fix to
   an error — surfaced here because it changes what the paper claims as new.
3. **A3 round count 357k→200k** and the tracker-ratio rounding (6.7/8.1/62 → 6.6/7.9/60):
   number corrections, no claim changes (qualitative conclusions unchanged).
4. **Block tracker beats the *baseline* (normalized-GD) per-row, but only per-row.** New,
   claims-relevant (see 2nd-pass section): block > normGD is significant per-row (0.38 vs
   0.197, t=10.6, 10/10) so "ties normalized-GD" is over-generous for that configuration —
   but it **vanishes under the batched per-step protocol** (t=−0.1), and the reported EMA
   default ties normGD on both. The headline "comparable" survives for the reported method;
   §4.3 now carries the per-row/per-step asymmetry rather than the bare per-row number.

## Stress-test of the flattering block-tracker result (A7 follow-up)

The A7 win (block tracker beats EMA, R² 0.38 vs 0.28) is a *flattering* number, so it got
the same discipline as the β rescue and MNIST. Extended
`scripts/research_audit_checks.py --a7` from lr∈{0.05..2} to include **lr=5, 10**, added a
paired 10-fold R² band, and confirmed the lower-bracket/divergence behaviour across the full
sweep. Real Jane stream, 150k rows, dim=79, deterministic (no RNG — the "band" is over
contiguous folds, not seeds).

| lr | block R² | block peak | EMA R² | EMA peak |
|----|----------|-----------|--------|----------|
| 0.5 | 0.211 | 5.1 | 0.169 | 4.7 |
| 1.0 | 0.299 | 4.7 | 0.246 | 4.3 |
| **2.0** | **0.380** | **3.9** | **0.284** | **8.1** |
| 5.0 | 0.364 | 7.9 | −0.101 | 54.3 |
| 10.0 | −0.084 | 30.3 | −2.03 | 229.9 |

Findings, and what changed in the paper:
- **(a) lr=2 is NOT the sweep edge.** Block R² peaks at the *interior* lr=2 (0.380), then
  falls at lr=5 (0.364) and collapses at lr=10. So neither "0.38" nor "peaks at lr=2" is a
  boundary artifact. Claim survives.
- **(b) The block-vs-EMA fold band is NOT significant** (corrected from the first pass's
  over-reading). Paired 10-fold gap at lr=2: mean **+0.159, sd 0.392 (ddof=1), SE 0.124,
  t≈1.28, block>EMA 8/10 (two-sided sign p≈0.11).** The first pass called this "a genuine
  sign"; the statistics don't support that — it is *not distinguishable from the EMA at this
  sample size*. §4.3 and A.8 now say exactly this (t≈1.3, 8/10), not just the point estimate.
- **(c) Caption note REVERSED.** The first-pass caption said "block reaches R²≈0.38, so this
  row is conservative" — that smuggled an unbanded optimistic number into the one line a
  skimming reviewer reads, and (per (b)) block>EMA isn't significant so "conservative" was
  unearned. **Removed it**; the caption now says only that a block-median tracker "changes the
  per-row number but not per-step, and not beyond fold noise against this row." The full banded
  story lives in §4.3/A.8.
- **(d) "Bounded throughout" was a boundary artifact — corrected; and "diverge" was wrong.**
  Old §4.3 said "peak rolling loss ≤5.3 throughout" (true only lr≤2). Past tuning the *loss*
  degrades (lr=10: block peak 30.3, EMA 229.9) but **neither diverges in the sense of
  Thm 3.1** — the O(√t) iterate bound still holds; it is the loss, not the iterate, that
  grows, unlike OGD's genuine 10^100 blow-up. Fixed §4.3, A.8 (and the abstract/intro
  "remain bounded for any lr" → "grow at most O(√t) on ℝᵈ / bounded on bounded 𝒲"). The
  "pick either without risking divergence" line is gone.
- **Narrative-conflict resolution (long-windows-bad vs one-day block tracker best).** §4.3 /
  Fig 2b penalize long windows for lagging regime onsets, yet a one-day block tracker is now
  the most accurate config. Added a paragraph to A.8 distinguishing the two *uses* of the
  scale: as a **divisor** (ĝ=g/s) a lagging s only mis-normalizes magnitude and cancels to
  first order, so a slow block median is tolerable; as a **threshold** (clip ‖g‖ at s, the
  §4.3 lag experiment) a lagging s clips hardest exactly when the scale jumps up, discarding
  the informative post-onset gradients. Long windows are bad for *thresholding*, fine for
  *normalizing*; the block tracker is a normalizer, so no contradiction.

## Second-pass review (block-vs-baseline, statistics, boundedness language)

Prompted by a reviewer catch that the block result might change the paper's central
concession. `scripts/research_audit_checks.py --cmp` — block vs **normalized-GD** (the M→0
baseline the paper concedes it "ties") and vs the EMA default, per-row AND per-step (batched
by (date,time), the "honest" competition-like protocol), each at its tuned lr, paired 10-fold
band with SE/t/sign-test. Numbers reproduce Table 1 exactly (normGD 0.197/0.316, EMA
0.285/0.309), confirming same stream/protocol.

| pairing | per-row gap (t, folds) | per-step gap (t, folds) | verdict |
|---|---|---|---|
| **block − normGD** | **+0.176 (t=10.6, 10/10, p=0.002)** | −0.009 (t=−0.1, 8/10) | sig. per-row, **ties per-step** |
| block − EMA | +0.159 (t=1.3, 8/10) | +0.060 (t=1.2, 6/10) | not sig. either protocol |
| EMA − normGD | +0.017 (t=0.1, 9/10) | −0.069 (t=−0.5, 8/10) | not sig. — "comparable" holds |

- **Item 1 (could-change-a-claim): checked, framing survives — with one honest addition.**
  The reported EMA default *does* tie normalized-GD on both protocols (t=0.1 per-row, −0.5
  per-step), so the paper's "comparable" concession is correct **for the reported method**.
  The block tracker beats normGD **per-row and significantly** (0.38 vs 0.197, t=10.6, all 10
  folds — and block/normGD are tightly coupled fold-to-fold, sd 0.052, so it is robust, not
  one lucky fold), so "ties normalized-GD" is over-generous *for that configuration on the
  per-row protocol*. **But it is protocol-specific**: batched per-step aggregation erases it
  (t=−0.1). So the flattering per-row number does not survive the stricter protocol — the
  headline tie stands where it is measured most conservatively. §4.3 now states (i) block >
  normGD per-row significant, (ii) vanishes per-step, (iii) block ≈ EMA within noise. This is
  claims-relevant and is added to the claims-changing list.
- **Item 4 (A.8 three-way gap):** A.8 now names which proposition covers which tracker —
  `prop:tracker` proves W_s=O(V_σ⁺) **only for the envelope** (s=max{c·m̂,(1−ρ)s}); the EMA
  and the block median are **both uncovered** (only empirical W_s), and the *best-performing*
  tracker (block) is the *least analyzed*. The prove-vs-deploy gap is stated as **wider**, not
  narrower — a clean open problem, not a defect.
- **Item 2 (caption / statistics):** see (b),(c) above — over-reading corrected, caption note
  removed.
- **Item 3 (boundedness language):** see (d) above — "diverge" reserved for OGD's blow-up;
  abstract/intro "bounded for any lr" qualified to O(√t) on ℝᵈ.

## Mechanical staleness guard (new test)

This bug class cost the paper twice (leaky-R² CSV; stale 6.7/8.1/62 tracker ratios left after
the causal fix). Added `tests/test_artifacts_fresh.py`: it re-runs each deterministic
artifact's generator into a temp dir and **fails on numeric diff** against the committed CSV.
Currently guards `results/research/tracker_a1.csv` (via `scripts/research_tracker.py`, ~4 s);
`ARTIFACTS` is a one-line-per-CSV registry for adding more. Skips when the Jane parquet is
absent (no-op in data-less CI). Verified it *fails* when the old 62.26 ratio is re-injected
and *passes* on the current file, and that it never touches the committed artifact. Stochastic
/ expensive outputs (MNIST, 400-seed synthetic) and PNGs are out of scope by design
(seed-pinned in their own scripts; figure numbers live in the guarded CSVs). Suite now 76 tests.
