# Independent reviewer audit — *Predictable Scale Dependence Makes Gradient Heavy Tails Removable* (SN-OMD / `dfsl`)

*Area-chair-level, hostile-but-fair. Read-only: no repo/paper edits were made (working tree restored to clean after every regeneration). Ground truth = `paper/icml2026.tex` + independent execution. Labels: VERIFIED / SUPPORTED / UNVERIFIED / FALSE-INCONSISTENT.*

### ⚠️ Auditor conflict disclosure (read first)
Earlier **in this same working session** I (the auditor) authored and committed
`scripts/research_residual_surrogate.py` (local commit `6e3a693` on branch `paper-submission`,
**unpushed**), which reproduces `tab:residual`'s GARCH-surrogate rows. That intersects the
prompt's "Worked Example B." I have deliberately audited against the **reviewer-facing remote
state** (`origin/master` `2ec7d9f` — what a clone of `github.com/rafli-hl/dfsl` yields), where
that file is **absent**, and I flag the reproducibility gap as it exists there rather than
letting my own unpushed fix paper over it. Every "reviewer-facing" statement below was checked
with `git show origin/master:…`, not just my working tree.

---

## Summary
This is a careful **measurement-plus-stability** paper. Its central empirical claim — that the
heavy tail of an online learner's loss gradients on drifting-scale market data is largely a
*predictable-scale (volatility-clustering)* effect that a causal robust normalizer removes — is
well-designed and supported by a coherent battery of controls (shuffle / iid / GARCH-surrogate /
feature-vs-residual). Its theory is **correct under stated assumptions** (I re-derived the lemma
chain and the main regret assembly by hand) but deliberately hedged to a *per-regime* rate under
an *undischarged* tracker assumption. The engineering hygiene is unusually good: a passing
77-test suite, a SHA-pinned headline input, self-contained synthetic experiments that reproduce
to ~14 significant figures, and systematically anti-overclaiming prose ("not an accuracy win").

The problems are concentrated, not diffuse: (1) a **CRITICAL anonymization breach** in the live
repository (not the paper text); (2) a **reviewer-facing reproducibility gap** — `tab:residual`'s
GARCH-surrogate rows have no committed generator on the cloned repo; (3) a **number-vs-table
inconsistency** in the bootstrap-SE prose sourced from a superseded CSV; and (4) a genuinely
**modest novelty / hedged theory** ceiling. None of (2)–(4) invalidates the central thesis; (1)
is procedural and time-sensitive but fixable.

## Main Contribution
*A measurement-plus-stability result: the heavy tail of an online learner's loss gradients on
drifting-scale market data is a predictable-scale volatility-clustering effect that a causal
robust normalizer largely removes, packaged as a scale-free-capped OMD family whose finite cap
gives an unconditional (moment-free) stability guarantee — with the authors candid that the
dynamic-regret theory is per-regime and the accuracy result is a tie, not a win.*

## Strengths
- **Correct, honestly-scoped theory.** Theorem 3.1 (stability) is a clean deterministic
  consequence of the cap; Theorem C.2 (dynamic regret) and its lemma chain (D.1–D.4, Freedman,
  telescope) check out by hand, *including* the non-obvious peak-to-mean-ratio constant in the
  final bound. The paper states its own limits (per-regime rate, fixed-comparator, constant-η
  schedule, informal tracker discharge) rather than hiding them. **[VERIFIED / by-hand]**
- **A real mechanism test, not just an accuracy table.** Shuffle-destroys-lightening,
  tail-preservation on iid known-index streams, and a GARCH surrogate with Gaussian innovations
  form a genuine falsification design; a stationary negative control where SN-OMD *loses* to OGD
  is reported. **[SUPPORTED]**
- **Reproducibility infrastructure.** `pytest` (77 passed, 0 skipped), a SHA256 pin on
  `gradnorm_at_wstar.npy` (the headline α̂ input), a regenerate-and-diff regression test, and a
  self-contained synthetic script that I re-ran to a ~14-sig-fig match. **[VERIFIED]**
- **Discipline against overclaiming.** Every "dominates/best/win" hit is hedged or negative; the
  abstract itself concedes "not an accuracy win." Rare and creditable. **[VERIFIED]**

## Major Concerns
1. **Repository anonymization breach (CRITICAL, procedural).** The live repo is not anonymized;
   `make_anon_release.py` exists but shows no sign of having been run. See Finding 1.
2. **Reviewer-facing reproducibility gap for `tab:residual`'s surrogate rows (MAJOR).** No
   committed generator exists on the cloned repo. See Finding 2.
3. **Bootstrap-SE prose inconsistent with its own table (MODERATE→MAJOR for trust).** Line 496's
   "normalized-GD's (±.024/.021)" comes from a superseded CSV; the displayed table shows
   ±.037/.077. See Finding 3.
4. **Dynamic-regret contribution is thin (MODERATE).** Real but per-regime, globally vacuous at
   p=2, resting on an assumption discharged only by an explicitly "informal" proposition. See
   Finding 5.

## Minor Concerns
- `references.bib` (11 entries) is dead weight, fully superseded by `refs.bib` (23; the one
  `\bibliography` uses). Zero undefined citations — not a dropped citation. **[VERIFIED]**
- `research_synthetic.py` docstring cites a nonexistent "Theorem 3.3" (only 3.1 and C.2 exist).
  Doc-drift. **[VERIFIED]**
- Core class is `ScaleNormalizedOGD` while the paper says "OMD" throughout. Defensible (projected
  GD = OMD with the Euclidean regularizer) but a reviewer may snag on it. **[VERIFIED naming]**
- `tab:jane` is silently assembled from **two** CSVs (`table1_errorbars.csv` for OGD /
  scale-adaptive OGD; `baselines_jane.csv` for NGD / clip / AdaGrad), with two different NGD
  runs (lr=2 vs lr=3). The table is internally consistent, but this is the seam Finding 3 falls
  through. **[VERIFIED]**

## Mathematical Correctness
I restated and hand-checked the load-bearing results. **[VERIFIED, analytical — no symbolic
solver used]**
- **Lemma D.1 (`lem:clip`)** — both case-split bounds correct: `‖v‖≤M` ⇒
  `‖v‖²=‖v‖ᵖ‖v‖²⁻ᵖ≤‖v‖ᵖM²⁻ᵖ`; `‖v‖>M` ⇒ `M²=MᵖM²⁻ᵖ≤‖v‖ᵖM²⁻ᵖ` and
  `‖v‖−M≤‖v‖=‖v‖ᵖ‖v‖¹⁻ᵖ<‖v‖ᵖM¹⁻ᵖ`. Valid for all `p∈(1,2]`, `M>0`.
- **Lemma D.2 (`lem:moment`)** — conditional-expectation step sound; the drifting-`p_t`→`p`
  worst-casing is correctly licensed by `M≥1` (`M^{2−p_t}≤M^{2−p}`, `M^{−(p_t−1)}≤M^{−(p−1)}`
  iff `p_t≥p`).
- **Lemma D.3 (Freedman)** — MDS structure valid *because* `u_t`, `w_t` are predictable; range
  `b=2BD` and variance `V=D²Σ𝔼‖Z‖²` correct.
- **Lemma D.4 (telescope)** — reindex with `s_0=0`, split into comparator-move + scale-change,
  reverse-triangle: `≤ D²W_s + 2D P_T^s`. Correct.
- **Theorem C.2 assembly** — the (A)/(B)/(C) split telescopes to `‖ḡ_t‖`; the curvature sum's
  high-probability promotion via a *second* Freedman application yields a leading multiplier
  `(sup σ/σ̄)·log(1/δ)`. I verified the key cancellation: `√(2V_A log)/(M²⁻ᵖκ'S₁) =
  Θ(√((sup σ/σ̄)log(1/δ)))` because `M^p=Θ(T)` cancels `S₁=Θ(T)`. The `η`/`M` balance gives
  `T^{(2−p)/(2p)}`, and with `√W_s√S₁∼T` the global exponent is `1/p+1/2` (vacuous `T` at p=2),
  `1/p` per regime — exactly as the remark claims.
- **Theorem 3.1 (stability)** — deterministic; `‖w_t‖≤‖w_1‖+M η Σk^{−1/2}≤‖w_1‖+2Mη√t`. Correct.

**Verdict:** no false theorem, no smuggled assumption, no in-expectation/high-probability
conflation. The soft spot is *scope*, not correctness (Finding 5).

## Empirical Validity
- The **headline tail input** `gradnorm_at_wstar.npy` is SHA-pinned and the pin test passes:
  the α̂≈2.43 pooled index rests on a fixed, committed artifact. **[VERIFIED input]**
- `tab:residual`'s **real-data rows** trace to `research_review2_checks.py` (functions read;
  `causal_ema`/`centered_ema`/`hill` consistent with the table). **[SUPPORTED]**
- `tab:jane` rows reconcile exactly to `baselines_jane.csv` + `table1_errorbars.csv`
  **[VERIFIED]**, but see Finding 3 for the prose seam.
- The **10-window divergence dichotomy** (0/10 vs 6/10 vs 9/10) and **R²≈0.28 leakage battery**
  need the 12 GB Jane parquet + long compute; I did **not** re-run them here. The parquet *is*
  present locally (the regenerate-and-diff test for `tracker_a1.csv` passed), but a reviewer
  without it cannot reproduce. **[UNVERIFIED for a reviewer; SUPPORTED from prior spot-checks]**
- Table 3 leakage logic re-derived: the shuffled-label null (`R²≤0`) rules out **label**
  leakage specifically; the forward-transfer collapse (−1.7) and offline-oracle-below-online
  (0.18<0.28) additionally argue against a transferable static fit. It does **not** by itself
  neutralize *tuning* leakage — which the paper concedes and partially addresses via the
  drop-window-1 robustness check (`tracker_bootstrap.csv` has "drop window 1" rows). **[SUPPORTED]**

## Statistical Validity
- Bootstrap method (circular block ≈ one trading day, 4000 resamples) is stated in Table 4's
  caption and used where CIs appear. **Caveat the paper half-owns:** with rank-autocorrelation
  of `‖g_t‖` still ≈0.1–0.2 out to lag 250 (Fig. 1b), a ~1-day block plausibly *understates*
  variance — the SEs may be optimistic. **[SUPPORTED concern, not quantified here]**
- The central comparisons are **pre-specified and paired** (per-window paired differences with
  reported CIs, e.g. block-median vs CM: +0.004, CI [−0.014,+0.023]), so the "tie" is correctly
  framed as *failed to reject*, not proven equivalence — and a heavy multiple-comparisons
  correction is not obviously required. The `≈8×10×2` grid is real, but the load-bearing claims
  ride paired CIs, not a max over an unadjusted family. **[SUPPORTED]**
- One genuinely missing rigor step: the "co-lead"/"no member dominates" language would benefit
  from an explicit equivalence-margin statement rather than a non-significant paired difference.

## Reproducibility
- **What a reviewer CAN reproduce with no data:** the full test suite, the SHA pin, and every
  synthetic script (`research_synthetic.py` re-ran to ~14 sig figs; the null/mechanism/GARCH
  controls in `research_null_normalization.py` and — on my local branch only —
  `research_residual_surrogate.py` are synthetic). **[VERIFIED]**
- **What needs the 12 GB Jane parquet (Kaggle-gated):** all `tab:jane` / `tab:replication` /
  leakage numbers. Honestly disclosed, but a reviewer cannot independently regenerate them.
  **[UNVERIFIED for a reviewer]**
- **The gap:** on `origin/master`, `tab:residual`'s **GARCH-surrogate rows** are produced by no
  committed script; Software-and-Data softens this to "the GARCH-surrogate control." Fixable in
  minutes (a self-contained generator; one exists but is unpushed — see disclosure). **[FALSE-
  INCONSISTENT, reviewer-facing]**
- 34–36 scripts vastly exceed the ~10 named in Software-and-Data; provenance of many is
  discoverable but not spelled out. Judgment: a determined researcher *with* the Jane data could
  regenerate the headline numbers; a data-less reviewer is limited to the synthetic/stability
  scaffolding plus prose-vs-CSV cross-reading.

## Novelty / Related Work
- The paper **correctly self-assesses** that the volatility-clustering mechanism is classical
  (Clark 1973, Engle 1982, Bollerslev 1986) and locates novelty in (a) demonstrating it for an
  online learner's *loss gradients* as a feature×residual interaction, and (b) the cap-interpolation
  family + unconditional stability. That is a fair, modest framing — not overstated. **[SUPPORTED]**
- Distance to the closest baseline (**Cutkosky–Mehta 2021**) is genuinely small: the paper's own
  `cm_normgd_equiv.csv` shows CM at β=0 is *bit-identical* to normalized-GD, and the per-row
  co-leader is CM's normalize-and-clip. The contribution over CM is the *scale-free-cap framing*
  + the empirical mechanism, not an algorithmic leap. Honestly presented, but it caps
  theoretical-significance. **[SUPPORTED]**
- `\cite`↔`refs.bib` is clean (0 undefined). I did **not** have web access to spot-check
  Kesten 1973 / Breiman 1965 / Cutkosky–Mehta 2021 author/venue/year against sources — those
  in-text usages read correctly but are **[UNVERIFIED against external sources]**.

## Strongest Case for Acceptance
A correct, moment-free **stability** theorem paired with a clean 0/10-vs-6/10-vs-9/10 divergence
dichotomy, wrapped around a genuinely well-controlled measurement (shuffle/iid/GARCH) that
reframes "heavy-tailed gradients" as a predictable-scale phenomenon — delivered with rare
candor about what is *not* shown (no accuracy win, per-regime theory, disclosed leakage
self-corrections). It is the kind of honest, mechanism-first empirical paper the field is short
on.

## Strongest Case for Rejection
Strip the procedural anonymization issue and two things remain that a skeptic will press: the
**contribution is incremental** (classical mechanism; algorithm bit-identical to a 2021 baseline
at one endpoint; theory correct but per-regime and resting on an undischarged tracker
assumption), and the **headline empirical numbers are not reviewer-reproducible** (Kaggle-gated
data) while one committed table (`tab:residual` surrogate rows) has no generator at all and a
supporting-SE sentence does not match its own table. "Correct but small, and I can't rerun the
big numbers" is a legitimate borderline-to-reject posture at a top venue.

## Top 10 Findings

**1. CRITICAL — Live repository is not anonymized; anon export never run.**
Location: `LICENSE` ("Copyright (c) 2026 Rafli"), `pyproject.toml`
(`authors=[{name="Rafli", email="rafli@pyhron.com"}]`), git author on every commit
`Rafli Putra Pratama <quantiumintelligence@gmail.com>`, repo `github.com/rafli-hl/dfsl`.
Claim (implicit): submission is properly blinded. Found: the **paper `.tex` is** anonymized
(`\icmlauthor{Anonymous Authors}`, `anon@example.com`) but the **repository is not**;
`scripts/make_anon_release.py` exists yet no anonymized export directory or run artifact is
present. Note the prompt's own claim of `rafli-hl <rafli@pyhron.com>` in git is **inaccurate** —
the committer email is a *different* personal address (`quantiumintelligence@gmail.com`), which
only widens the exposure. Why it matters: if any supplementary zip or in-paper link points at
this live URL, it de-anonymizes the authors — a compliance/desk-reject risk independent of
technical merit. Action: run `make_anon_release.py`, submit only the clean export, and confirm
no reviewer-facing artifact references the live repo. Confidence: **97%** (exposure VERIFIED;
whether a reviewer-facing link points here is **UNVERIFIED** — I cannot see the submission zip).

**2. MAJOR — `tab:residual`'s GARCH-surrogate rows have no committed generator on the cloned repo.**
Location: `paper/icml2026.tex:388–390` (surrogate rows 4.81/4.48/4.08, oracle 10.3/9.05/7.75);
Software-and-Data `:746–747` (origin/master). Claim: "scripts … reproduce every figure and
number, including `tab:residual`'s … GARCH-surrogate control." Found: on `origin/master` no
script emits those three-threshold cells (`research_null_normalization.py` prints only the
headline k=0.01); the wording is softened to "the GARCH-surrogate control," which is honest but
leaves the rows unbacked. (Disclosure: I authored a self-contained generator this session that
reproduces them to ±0.02, but it is **unpushed** and absent from the reviewer's clone.) The
prompt's literal "Worked Example B" — paper *names* `research_residual_surrogate.py` while the
file is missing — is **FALSE against every pushed state** (master names no such file); the real
issue is the repro gap, not a dangling reference. Action: commit+push a synthetic generator (or
keep the softened wording and mark the rows as illustrative). Confidence: **95%** (VERIFIED via
`git show origin/master`).

**3. MAJOR-for-trust / MODERATE-in-substance — Bootstrap-SE prose contradicts its own table.**
Location: `:496`. Claim: "SN-OMD's block-bootstrap standard errors (±.079/.056) run ≈3×
normalized-GD's (±.024/.021)." Found: `.024/.021` = `table1_errorbars.csv` NGD at **lr=2.0**
(.0241 / .0206), a **superseded** run; the *displayed* `tab:jane` NGD row is sourced from
`baselines_jane.csv` at **lr=3.0** (**±.037/.077**, mean 0.220 not 0.197). The "≈3×" holds only
against the stale CSV; against the displayed table the ratio is 2.1× / **0.73×** — SN-OMD's
per-step SE is actually *lower* than NGD's. A reader cross-checking `.024/.021` against Table 1
finds `.037/.077`. This is precisely the "number stops matching its generator" class the repo's
own test docstring says has bitten twice before, uncaught because bootstrap CSVs aren't in the
regression test. Both values reported; I do not assert which the authors *intend*. Action: re-source
the sentence to the displayed table and correct/drop "≈3×." Confidence: **90%** (VERIFIED by CSV grep).

**4. VERIFIED-POSITIVE — Test suite, hash pin, and synthetic reproduction all pass.**
Location: `tests/`, `research_synthetic.py`. Found: 77 tests pass (0 skipped);
`test_input_artifact_hash_pinned[gradnorm_at_wstar.npy]` and
`test_committed_csv_matches_generator[research_tracker]` both **run and pass** (parquet present
locally); `research_synthetic.py` re-ran to a ~14-sig-fig match on `synthetic_regret.csv`. Why
it matters: the headline tail input is immutable-by-hash and the theory's synthetic test is
genuinely reproducible — raising the floor on trust. Action: none (extend the diff test to
bootstrap CSVs to prevent Finding 3 recurring). Confidence: **99%** (VERIFIED, re-run).

**5. MODERATE — Dynamic-regret theorem is real but per-regime and rests on an undischarged assumption.**
Location: `thm:regret` `:898`, remark `:925`, `prop:tracker` `:1385`. Claim: SN-OMD "attains the
per-regime rate `T^{1/p}`." Found (VERIFIED by hand): the proof is correct, but the rate is
**per-regime only** (global `T^{1/p+1/2}`, i.e. vacuous `T` at p=2), holds **per fixed
predictable comparator** (not the per-round minimizer), is proven for the **constant-η**
schedule (not the deployed `1/√t`), and depends on **Assumption C.1** (scale-tracking bracket)
whose discharge (Prop. D.5) the paper itself labels "a sketch, not a theorem." All disclosed.
Why it matters: the theoretical "headline" is weaker than it first reads; the end-to-end
"SN-OMD provably attains `T^{1/p}` on real data" is **SUPPORTED, not established**. Action: none
required (already hedged); strengthening Prop. D.5 to a theorem would materially raise
significance. Confidence: **88%** (analytical).

**6. MODERATE — Headline empirical numbers are not reviewer-reproducible (Kaggle-gated data).**
Location: `sec:experiments`, `tab:jane`, `tab:replication`, `tab:leakage`. Found: every
Jane-data number needs `data/raw/jane/train.parquet` (Kaggle token). Honestly stated, but a
reviewer cannot regenerate the divergence counts, R²s, or SEs; they are **UNVERIFIED** from a
clean clone. Action: ship a small pre-computed gradient artifact + a seeded mini-slice so at
least the stability dichotomy is runnable data-free. Confidence: **85%**.

**7. MINOR — `references.bib` is orphaned dead weight.**
Location: `paper/references.bib` (11 entries) vs `paper/refs.bib` (23, the one used). Found:
zero undefined `\cite` keys; `references.bib` uses a different citekey convention
(`catoni2012challenging` vs cited `catoni2012`) — a superseded file, **not** a dropped citation.
Action: delete it (also removes an anonymization surface). Confidence: **95%** (VERIFIED).

**8. MINOR — Doc-drift: `research_synthetic.py` cites nonexistent "Theorem 3.3."**
Location: `scripts/research_synthetic.py:2`. Found: only Theorems 3.1 and C.2 exist. Harmless
but a symptom of the revision drift behind Findings 2–3. Action: update docstring. Confidence:
**99%**.

**9. MINOR — Class name `ScaleNormalizedOGD` vs "OMD" throughout the paper.**
Location: `src/dfsl/…`, paper title/§3. Found: defensible (Euclidean-regularizer OMD ≡ projected
GD) but an easy reviewer snag; not reconciled in text. Action: one sentence noting the
equivalence. Confidence: **90%**.

**10. MODERATE — Block-bootstrap block length may understate variance.**
Location: Table 4 caption; Fig. 1b. Found: a ~1-day block against rank-autocorrelation ≈0.1–0.2
persisting to lag 250 risks optimistic SEs — which would tighten the very CIs the "tie" claims
lean on. Not quantified here. Action: report SE sensitivity to block length (e.g. 3–5 day
blocks). Confidence: **65%** (SUPPORTED, not measured).

## Reviewer Scorecard
*(scores rest on VERIFIED math/tests/synthetic; empirical/stat scores are partly SUPPORTED/UNVERIFIED as noted)*

| Axis | Score /100 | Basis |
|---|---|---|
| Novelty | 52 | Classical mechanism; algorithm ≡ CM(β=0)/normGD at endpoints. Fair self-assessment. **SUPPORTED** |
| Technical Correctness | 84 | Lemmas + main proof verified by hand; no false result. **VERIFIED (analytical)** |
| Theoretical Significance | 55 | Correct but per-regime + undischarged tracker assumption. **VERIFIED-hedged** |
| Empirical Rigor | 70 | Strong control design; headline numbers not reviewer-reproducible. **SUPPORTED/UNVERIFIED** |
| Statistical Rigor | 66 | Paired CIs, honest "failed-to-reject"; block-length variance caveat. **SUPPORTED** |
| Reproducibility | 62 | Excellent synthetic/test scaffolding; gated headline data + one ungenerated table. **Mixed** |
| Clarity | 78 | Dense but precise and self-critical; minor drift. **VERIFIED** |
| Related Work | 74 | Honest positioning; citations resolve; external spot-check not done. **SUPPORTED** |
| **Overall** | **64** | Correct + honest + incremental, dragged by repro gaps and a procedural breach. |

## Confidence
**Overall confidence in this assessment: 78%.** High (VERIFIED) on the math (hand-derived),
the tests/hash/synthetic reproduction (re-run), the anonymization exposure, the bootstrap-SE
inconsistency, and the bib/doc-drift items. Lower (SUPPORTED/UNVERIFIED) on the Jane-data
headline numbers (not re-run from raw here — Kaggle-gated), the block-length variance caveat
(not quantified), and external citation spot-checks (no web access). I did not symbolically
verify the proofs with a solver; the math checks are careful by-hand derivations.

## Final Recommendation
**BORDERLINE** (leaning **WEAK ACCEPT** on scientific merit, *conditional* on the anonymization
breach being remediated before/at review).

Single strongest reason to accept: the paper does something genuinely valuable and rare — it
*correctly measures* that an online learner's heavy gradient tail is a predictable-scale
volatility-clustering effect, backs it with a real falsification battery and a correct moment-free
stability theorem, and reports the result with unusual honesty (no accuracy win, per-regime
theory, disclosed leakage self-corrections). Single strongest reason to reject: the contribution
is incremental (classical mechanism; endpoint-identical to a 2021 baseline; theory correct but
per-regime and assumption-gated), and its headline numbers are not reviewer-reproducible while
one committed table lacks any generator and a supporting-SE sentence contradicts its own table.
The anonymization breach is not a scientific flaw but is a time-sensitive procedural risk that a
program chair could act on regardless of scores. Minimum change to move from borderline to
accept: (i) run the anonymized export and purge the identity surface; (ii) commit a
self-contained generator for `tab:residual`'s surrogate rows and a data-free stability
mini-reproduction; (iii) fix the bootstrap-SE sentence to match Table 1; (iv) upgrade the
tracker-discharge sketch (Prop. D.5) toward a theorem, or soften the regret claim's phrasing
accordingly.
