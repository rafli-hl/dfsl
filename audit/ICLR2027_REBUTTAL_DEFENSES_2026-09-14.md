# ICLR 2027 Rebuttal Defenses

**Manuscript:** *Predictable Scale Normalization Lightens Gradient-Tail Diagnostics: Scale-Normalized Sequential Learning*  
**Prepared:** 2026-09-14  
**Use:** concise author-response material; preserve the concessions and do not convert them into broader claims.

## Core response in one paragraph

We agree that the paper should not be read as a universal optimizer win or as a regret guarantee
for the deployed configuration. Its contribution is a narrower, evidence-matched package: a
fixed-reference pooled-tail diagnostic showing that causal scale normalization changes the
observed gradient-tail estimate through serial dependence; an unconditional iterate envelope for
any capped normalized step; a two-axis taxonomy separating stream-uniform boundedness from
degree-zero scale response; and a tune-once, freeze-across-windows experiment. The held-out
windows 2--10 preserve the reported non-dominance conclusion. A common dimensionless loss-failure
criterion is now used on both markets, and it reveals an important exception: fixed-threshold
clipping is bounded but can still fail in loss. The conditional pseudo-regret theorem remains in
the appendix and is explicitly not presented as certification of the deployed schedule or
trackers.

## R1. "The tail result is not a conditional-tail estimate and may not describe online learners."

**Response.** We agree with both limits and revised the terminology accordingly. The measured
object is the pooled gradient norm at a fixed reference predictor. We call the reported Hill
estimate a *causally normalized pooled-tail diagnostic*, not a conditional-tail index, and we state
that it is not the tail along each learner's endogenous trajectory. The order-shuffle, iid-tail,
bounded-drift, and GARCH controls isolate a narrower result: the diagnostic change depends on
serial dependence and is not explained by the marginal distribution or a generic Hill-estimator
artifact. This measurement motivates predictable normalization; it does not by itself prove that
SN-OMD improves every learner trajectory.

**Point to:** abstract; Section 1 footnote; Section 4, "Causal normalization changes the
pooled-tail diagnostic"; Figures 1--2; Appendix A.

## R2. "The transfer theorem does not prove transfer across market windows."

**Response.** Correct. Theorem 3.2 is an exact identity for a globally rescaled *exogenous*
gradient sequence. It says that a degree-zero step map leaves the stable-rate set unchanged under
global rescaling, whereas a degree-one map rescales that set by the inverse scale. The further
claim that no positive fixed rate works uniformly requires the explicitly stated finite-upper-
endpoint condition. Market windows are neither pure global rescalings nor exogenous once gradients
depend on the iterate, so the theorem is used only to motivate a falsifiable tuning-transfer
diagnostic. The ten-window result is empirical evidence, not a corollary.

**Point to:** Theorem 3.2 and its following scope paragraph; Appendix E.7 proof.

## R3. "Bounded iterates do not imply acceptable loss."

**Response.** We agree, and the revised cross-domain criterion makes this distinction directly
observable. Proposition 3.1 controls per-step motion and the iterate envelope; it is not a
convergence or loss guarantee. On crypto, fixed-threshold clipping has a stream-uniform step bound
yet fails the relative-loss criterion on 10/10 windows. In contrast, the capped normalized rows
fail on 0/10. We therefore claim an iterate-stability guarantee and report loss failure as a
separate empirical outcome. The fixed-threshold result is retained as a counterexample, not hidden
as an inconvenient baseline.

**Point to:** Proposition 3.1; Section 4; Appendix A common criterion; Appendix F.2 crypto study.

## R4. "The cross-domain failure counts used inconsistent thresholds."

**Response.** The revised manuscript recomputes both domains with one dimensionless rule. For each
window, relative to its best constant predictor, failure is overall weighted MSE at least 2x or
peak rolling weighted squared error at least 10x, with rolling length
`max(100, floor(T/10))`. The validation suite is exactly invariant to target rescaling and recovers
all 20 independently identified uncapped blow-ups. We also disclose the negative diagnostic: the
peak clause changes none of 109 decisions, so the validated operational boundary is the overall-
loss ratio. Recalculation changes Jane's uncapped count to 6/10 and crypto's uncapped count to
8/10; accordingly, we withdrew the earlier "exactly the Jane partition" language.

**Point to:** Section 4 setup; Table 1; Appendix A common criterion; Appendix F.2.

## R5. "Window 1 is both the tuning window and part of the reported ten-window mean."

**Response.** We now report windows 2--10 separately in the main text and retain the all-ten table
for completeness. The held-out-only conclusion is unchanged: per-row Cutkosky--Mehta
(`0.28 +/- 0.03`) and block-median SN-OMD (`0.27 +/- 0.07`) co-lead, while the remaining rows are
lower; per-step the bounded methods overlap. This is the appropriate evidence for tuning transfer,
and it supports non-dominance rather than a unique SN-OMD win.

**Point to:** Section 4, "Held-out windows preserve non-dominance"; Table 1; Appendix F.3.

## R6. "SN-OMD does not beat the strongest baseline."

**Response.** Correct; dominance is not our claim. At matched tuning budget, block-median SN-OMD
ties Cutkosky--Mehta per-row, and no method dominates both per-row and per-step protocols. The
method-specific contribution is the combination of a predictable tracked scale with an explicit
scale-free cap, together with a transparent interpolation between normalized-GD and the uncapped
endpoint. The broader contribution is the measurement, taxonomy, iterate envelope, and controlled
window study. We state the tie in the abstract and conclusion.

**Point to:** abstract; Section 4; Table 1; Appendix F.3 and F.5.

## R7. "The theorem analyzes a different schedule and tracker from the deployed system."

**Response.** We agree and do not claim otherwise. The unconditional iterate envelope applies to
the deployed decaying schedule and to any positive predictable tracker because it uses only the
cap. The conditional pseudo-regret theorem is different: it analyzes a constant-step variant and
requires a tracker lower bracket and variation control. The proved peak-hold tracker, deployed
winsorized EMA, and empirically strong block median are explicitly separated. The latter two are
not claimed to satisfy the proved tracker bound. For this reason the pseudo-regret theorem is
appendix-only and is not used as the paper's empirical guarantee.

**Point to:** Section 2 final paragraph; Section 3 conditional-theorem paragraph; Appendix D;
Appendix F.3.

## R8. "The positive evidence is confined to finance and the full Jane data are gated."

**Response.** We accept both limitations. "Distribution-free" refers to the absence of a
parametric or sub-Gaussian noise-law assumption, not universal empirical effectiveness. The two
positive streams are financial; MNIST is deliberately reported as a negative stationary boundary
case. The full Jane data require external access, so we provide implementations, frozen artifacts,
synthetic controls, crypto replication, and a distributable mini-slice for code-path verification.
We do not claim that these substitutes reproduce every proprietary-data number from a clean clone.

**Point to:** Section 2 definition of distribution-free; Section 4 negative control; Limitations;
supplementary reproducibility materials.

## R9. "The paired-window significance claims are vulnerable to multiplicity and dependence."

**Response.** The unit of resampling is the window, not individual rows, so within-window serial
dependence is not treated as independent evidence. The remaining assumption is exchangeability of
the ten paired window differences, which we state. We report the Bonferroni sensitivity across the
14 paired comparisons: the block-versus-EMA per-row separation no longer clears zero, while the
Cutkosky--Mehta co-lead remains a tie. Our main claim is therefore non-dominance and a tracker
trade-off, not a statistically unique win.

**Point to:** Appendix F.3, paired-window bootstrap and multiple-comparisons paragraphs.

## R10. "What is the irreducible contribution if practitioners choose another optimizer?"

**Response.** The irreducible contribution is the diagnosis-and-design connection, not exclusive
ownership of the best optimizer: measure how a causally tracked scale changes a pooled-tail
diagnostic; distinguish scale response from boundedness; cap normalized steps when an
unconditional iterate envelope is required; and evaluate tune-once transfer across regimes. A
practitioner may reasonably select AdaGrad-Norm or momentum-normalized SGD for a particular
protocol. That does not invalidate the measurement, taxonomy, or the capped-step guarantee, and
the paper is written to make that choice visible.

## Claims not to make in rebuttal

- Do not say causal normalization identifies the data-generating mechanism.
- Do not call the Hill estimate a conditional-tail index.
- Do not claim Theorem 3.2 predicts or proves the ten-window partition.
- Do not say every bounded method avoids loss failure across domains.
- Do not call Proposition 3.1 a convergence or loss-stability theorem.
- Do not say the appendix pseudo-regret theorem certifies the deployed schedule, EMA, or block
  tracker.
- Do not claim SN-OMD significantly beats Cutkosky--Mehta or the deployed EMA per-row after the
  stated multiplicity correction.
- Do not describe the study as externally preregistered; describe the criterion-development and
  validation history exactly as recorded.
