# ICLR 2027 Reviewer Audit — Post-Taxonomy and Transfer-Theorem Repair

**Audit date:** 2026-09-14  
**Manuscript:** *Distribution-Free Sequential Learning under Drifting Heavy-Tailed Gradients*  
**Decision lens:** technical correctness, claim/evidence alignment, novelty, empirical validity, and reproducibility  
**Current recommendation:** **6/10 — Weak Accept**, with a plausible **5/10 — Borderline Reject** from a theory-first reviewer  
**Confidence:** **4/5**

## 1. Reviewer summary

The paper studies online learning under drifting, heavy-tailed gradients and introduces
Scale-Normalized Online Mirror Descent (SN-OMD), which divides gradients by a predictable scale
estimate and caps the normalized update. Its strongest contribution is not a universal regret
improvement or a uniquely superior optimizer. It is a coherent package of:

1. measurement showing that pooled residual-gradient tails can become lighter after causal scale
   normalization on a large financial stream;
2. an unconditional, stream-uniform iterate envelope for capped normalized steps;
3. an exact global-rescaling identity that separates degree-zero scale response from boundedness;
4. carefully controlled experiments showing that the capped normalized family avoids the paper's
   common loss-failure criterion across frozen windows, while bounded fixed-threshold clipping is
   a loss-failure counterexample and no single normalized member dominates in predictive accuracy;
   and
5. a conditional appendix pseudo-regret result whose assumptions and mismatch with the deployed
   schedule are now disclosed.

The revised paper is substantially more defensible than a method-dominance framing. The taxonomy
now distinguishes two independent properties—stream-uniform boundedness and degree-zero scale
invariance—and includes counterexamples in both directions. The repaired transfer theorem states
an exact identity for globally rescaled exogenous gradient sequences and conditions the
“no uniform fixed rate” conclusion on the base stable-rate set having a finite upper endpoint.
These changes close what would otherwise have been a serious mathematical objection.

## 2. Principal strengths

### S1. The central taxonomy is now mathematically coherent

The paper no longer treats “scale-free,” “bounded,” and “stable” as synonyms. It now makes clear
that:

- degree-zero homogeneity is a statement about trajectory response under global gradient
  rescaling;
- a stream-uniform update bound yields the iterate envelope;
- neither property implies the other; and
- empirical loss failure is a separate outcome, not a synonym for an unbounded iterate.

The uncapped scale-adaptive endpoint is the decisive counterexample: it is degree zero yet lacks a
stream-uniform step bound and fails the loss criterion in six of ten per-row windows. Conversely,
fixed-threshold clipping is bounded but not degree zero. This two-axis presentation is clearer and
more accurate than a single “scale-free family” label.

### S2. The transfer theorem is now scoped to what it proves

For a fixed exogenous gradient sequence and a trajectory-defined criterion, the theorem correctly
states the identities

- `H(S_lambda) = H(S_1)` for degree-zero update maps; and
- `H(S_lambda) = H(S_1) / lambda` for degree-one update maps.

The important conclusion about a fixed positive learning rate failing uniformly over scale is now
conditional on `H(S_1)` having a finite upper endpoint. The manuscript also states that market
windows are not global rescalings and that gradients in learning problems feed back through the
iterate. The theorem is therefore used as motivation for a cross-window diagnostic, not as a
proof of the observed window partition.

### S3. The empirical work is unusually candid about negative and non-dominance results

The paper reports that no bounded method wins both protocols, that SN-OMD ties a strong baseline
per-row rather than dominating it, that the block-median tracker improves mean accuracy at the
cost of dispersion, and that the stationary synthetic control removes the claimed advantage.
This is scientifically valuable and reduces the risk that the paper is read as optimizer
marketing.

### S4. The measurement contribution is potentially useful beyond the proposed algorithm

The causal normalization, leakage controls, tracker comparisons, frozen-window evaluation, and
negative control together support a useful empirical thesis: apparent gradient-tail severity can
partly reflect drifting scale, and diagnosing tail behavior after causal scale removal can change
the picture. That point is valuable even if readers ultimately prefer a different bounded
normalizer.

### S5. Reproducibility practice is stronger than average for a large proprietary-style dataset

The repository contains implementations, frozen-window artifacts, synthetic controls, figure
generation, and a small distributable data path. The manuscript explicitly discloses that the
full Jane Street data remain externally gated. This does not eliminate the limitation, but it is
handled more honestly than in many empirical finance submissions.

## 3. Principal weaknesses and remaining alignment risks

### W1. The measurement-to-algorithm bridge remains incomplete

The tail diagnostic is evaluated at a fixed offline reference point rather than along each
algorithm's endogenous online trajectory. That supports a statement about the measured stream and
the effect of causal scale normalization, but it does not establish that every learner encounters
the same tail transformation during training. The paper should keep this distinction prominent.

The terminology is now repaired: the manuscript consistently calls this a **causally normalized
pooled-tail diagnostic**, reserves “conditional” for probabilistic conditioning, and explicitly
states that the fixed-reference measurement is not the tail along an endogenous learner
trajectory. The remaining issue is evidential rather than terminological. If existing logs permit,
an online-trajectory sensitivity check would still strengthen the algorithmic bridge.

### W2. The conditional theorem and deployed algorithm remain deliberately misaligned

The appendix pseudo-regret theorem assumes a constant step, a predictable comparator, bounded
scale/path aggregates, and a tracker condition. The experiments deploy `eta/sqrt(t)`, and the
default EMA and more accurate block median are not the tracker covered by the proved condition.
The peak-hold tracker is the analytically covered object, but it is not the empirical default.

The manuscript now discloses this correctly, so this is no longer a correctness defect. It does,
however, limit the theorem's practical contribution. A theory-first reviewer can reasonably treat
the appendix theorem as an illustrative conditional result rather than a guarantee for the
reported method.

**Recommended repair:** keep dynamic pseudo-regret appendix-only. Add a compact assumption-to-
deployment map naming, for each theorem hypothesis, whether it is implemented, empirically
checked, or currently unmatched. Do not promote the theorem in the abstract.

### W3. Held-out reporting is now separated from the tuning window

The main text now gives windows 2–10 as the primary transfer summary while retaining the all-ten
table for completeness. Per-row, Cutkosky–Mehta (`0.28 +/- 0.03`) and matched-budget block-median
SN-OMD (`0.27 +/- 0.07`) remain co-leaders; per-step, the bounded methods remain overlapping. This
closes the tuning-window presentation concern without changing the scientific conclusion.

### W4. The common criterion exposes a bounded loss-failure exception on crypto

Both domains now use the accepted dimensionless rule: relative to the best constant predictor on
the same window, failure means overall weighted MSE at least `2x` or peak rolling weighted squared
error at least `10x`, with rolling length `max(100, floor(T/10))`. The rule is invariant to target
units; its validation suite recovered every independently identified uncapped blow-up. The peak
clause changed none of 109 validation decisions, a limitation disclosed in the appendix.

This repair changes the crypto result materially. OGD fails `10/10`, the uncapped endpoint `8/10`,
and fixed-threshold clipping `10/10`; SN-OMD and the other bounded normalized methods fail `0/10`.
Thus the old “exactly the Jane partition” claim was false. The new result is more informative:
fixed-threshold clipping has bounded iterates but unacceptable relative loss, directly confirming
that the iterate envelope is not a loss guarantee.

### W5. The positive empirical scope is narrow

The strongest positive result is financial. The non-financial experiment is a negative boundary
case, which is useful but does not show a positive benefit in another application domain. This
limits generality and makes “distribution-free” easy to misread as broad empirical universality
rather than absence of a parametric noise-law assumption.

**Recommended repair:** retain the precise definition of “distribution-free” and avoid claims of
cross-domain effectiveness. A second positive domain would strengthen the work, but it is not
required for the current, narrower measurement-and-stability thesis.

### W6. The method contribution is a family result, not a unique optimizer win

SN-OMD does not uniquely dominate normalized-GD, fixed-threshold clipping, AdaGrad-Norm, or the
Cutkosky–Mehta baseline. The best per-row result is statistically tied, and the best per-step row
depends on the tracker and has substantial variance. This is acceptable if the contribution is
framed as a predictable normalization-and-capping design plus a taxonomy and empirical study.

**Recommended repair:** keep “no bounded member dominates” in the main text and abstract-adjacent
contribution list. Avoid “our method wins” language in talks and rebuttal material.

### W7. Some inferential conclusions are weaker after multiplicity correction

The block-median versus EMA per-step contrast and one scale-adaptive contrast become inconclusive
under the stated multiple-comparison correction. The appendix records this; any main-text wording
should continue to describe these as tendencies or tradeoffs, not statistically separated wins.

### W8. Data access remains a reviewer-reproducibility constraint

The full Jane Street dataset is Kaggle-gated and large. The distributable mini-slice and synthetic
pipeline mitigate code-path verification but cannot independently reproduce every headline
number from a clean clone.

### W9. The global tracker bound can be loose in the finite-variance boundary case

At `p = 2`, the scale-variation term can grow with the horizon, weakening the operational content
of the global bound. The manuscript's regime-local and conditional interpretation is therefore
important and should not be compressed into a broad horizon-free regret claim.

## 4. Questions I would ask the authors

1. Does the reported tail lightening persist when gradients are measured along the endogenous
   trajectories of SN-OMD and at least one non-normalized baseline, rather than only at the fixed
   reference point?
2. What practical rule should select the learning-rate schedule and tracker, given that the
   constant-step theorem, the deployed decaying schedule, the proved peak-hold tracker, and the
   empirically preferred trackers are different objects?
3. Which component is intended as the enduring contribution if a practitioner chooses
   AdaGrad-Norm or the Cutkosky–Mehta baseline instead of SN-OMD: the measurement procedure, the
   two-axis taxonomy, or the capped algorithm itself?

## 5. Claim-to-evidence alignment after the repairs

### Aligned and defensible

- Causal scale normalization can lighten a pooled empirical gradient-tail diagnostic on the
  reported financial stream.
- Capped normalized updates have a deterministic stream-uniform step bound and the stated iterate
  envelope.
- Degree-zero and degree-one update maps obey the exact global-rescaling identities under the
  theorem's fixed exogenous-sequence setup.
- With a finite upper endpoint for the base stable-rate set, degree-one maps admit no fixed
  positive rate that remains stable over all global rescalings.
- The Jane frozen-window experiment supports its reported bounded-family loss-failure partition;
  crypto supports the contrast between bounded normalized and unbounded methods but not the whole family partition, because
  bounded fixed-threshold clipping fails the common relative-loss criterion.
- No member of the bounded family dominates predictive accuracy across protocols.
- The appendix pseudo-regret result is conditional and does not certify the deployed decaying-step
  experiments.

### Claims that would still be misaligned

- “Scale invariance guarantees stability.” It does not; the uncapped degree-zero endpoint is the
  paper's own counterexample.
- “Bounded updates transfer accuracy.” They transfer an iterate envelope, not predictive quality.
- “The transfer theorem explains the ten market windows.” It supplies a rescaling diagnostic; the
  actual windows involve distributional change and learner feedback.
- “The data verify the conditional heavy-tail assumption.” Marginal Hill diagnostics do not do
  this.
- “SN-OMD is the uniquely best optimizer.” The tables show a family-level stability result and
  protocol-dependent accuracy ties.
- “The dynamic-regret theorem covers the deployed method.” It does not cover the deployed schedule
  and empirical default tracker as a package.

## 6. Suggested ICLR scores

- **Technical quality / soundness:** 3/4 — the central boundedness and transfer statements are now
  correctly separated and scoped; the conditional theorem remains operationally narrow.
- **Empirical evaluation:** 3/4 — unusually extensive controls, a held-out transfer summary, and
  an honest cross-domain criterion correction; the fixed-reference tail diagnostic remains.
- **Novelty / significance:** 3/4 — the synthesis of drift measurement, causal normalization,
  taxonomy, and stability evidence is useful, though the optimizer itself is close to existing
  normalized/clipped families.
- **Clarity:** 3/4 — substantially improved; the diagnostic is now named without implying a
  conditional-tail estimate, and the common loss-failure rule is explicit.
- **Reproducibility:** 3/4 — strong code/artifact discipline, limited by gated full data.
- **Overall:** **6/10 — Weak Accept.**
- **Confidence:** **4/5.**

### Decision rationale

I would weakly accept the paper if reviewed as an empirical-and-conceptual study of how drifting
scale confounds heavy-tail diagnosis and how stream-uniformly bounded normalization changes
stability behavior. I would not accept a version claiming a new optimizer that universally
dominates or a theory that certifies the deployed system. The current manuscript has moved toward
the former, defensible thesis.

A theory-first reviewer may remain at 5/10 because the appendix theorem does not cover the deployed
schedule/tracker combination and because the global-rescaling result is an exact but elementary
identity. An empirical sequential-learning reviewer is more likely to assign 6/10 because the
measurement, frozen-window tests, leakage controls, negative control, and explicit non-dominance
result form a credible contribution.

## 7. Ranked pre-submission actions

### Priority 0 — preserve the repaired scope

1. Preserve the repaired two-axis taxonomy, common relative-loss criterion, held-out summary, and
   finite-upper-endpoint condition everywhere,
   including slides, abstract derivatives, and rebuttal notes.

### Priority 1 — inexpensive evidence strengthening

2. If existing trajectory logs suffice, recompute the tail diagnostic along SN-OMD and one
   comparison trajectory. Treat this as sensitivity evidence, not a replacement for the main
   controlled diagnostic.
3. Add a compact theorem-to-deployment assumption map in the appendix.
4. Ensure the main-text tracker comparisons use uncertainty-aware language consistent with the
   multiple-comparison analysis.

### Priority 2 — valuable but not required for this submission thesis

5. Add a positive non-financial domain only if it can be executed without displacing the current
   controls or weakening reproducibility.
6. Add bootstrap block-length sensitivity if runtime permits.
7. Remove minor PDF duplicate-destination warnings from restated theorem environments; these do
    not affect correctness or visible layout but improve submission hygiene.

## 8. Bottom line

The repaired thesis is coherent:

> Drifting scale can make pooled gradients appear more heavy-tailed; causal normalization changes
> that diagnostic. Stream-uniformly bounded normalized updates prevent iterate blow-up, while
> degree-zero scale response supplies a separate global-rescaling transfer identity. Across the
> Jane windows, this yields a family-level relative-loss partition; crypto supports only the
> narrower bounded-normalized versus unbounded contrast. Neither is a universal accuracy win.
> The regret result is conditional and appendix-only.

That is a credible ICLR thesis. The main remaining submission risk is not the repaired theorem;
it is allowing the prose to drift back from this bounded, family-level claim into conditional-tail,
method-dominance, or deployed-theory language that the evidence does not support.

## 9. Final pre-commit review addendum

The final page-by-page review found one literal ambiguity in the abstract: “meets the criterion”
was used once to mean passing a standard and elsewhere to mean triggering a failure. It is now
written uniformly as “avoids” versus “triggers” the common dimensionless loss-failure criterion.
The review also replaced the potentially overbroad “capped-versus-unbounded” shorthand with the
precise contrast between bounded normalized and unbounded methods, since bounded fixed-threshold
clipping is the crypto counterexample. After those repairs, no blocking claim/evidence or rendered-
layout defect remains. The recommendation stays 6/10 weak accept; the residual weaknesses in
Section 3 remain appropriate rebuttal topics rather than correctness defects.
