# Paper map — reconstructing the argument before judging it

*Auditor reconstruction (Phase 1). Source of truth: `paper/icml2026.tex` (not the PDF).*

## Problem addressed
Online sequential prediction on streams whose **loss-gradient scale is strongly
nonstationary** (financial data as testbed). Classical distribution-free / heavy-tailed
optimization treats the tail as an intrinsic property of the gradient distribution and
reaches for clipping / robust mean estimation. The paper argues the operative difficulty on
real streams is not an intrinsic heavy tail but a **drifting, predictable scale**.

## Limitation in prior work
Existing distribution-free online-learning guarantees are "either in expectation, on bounded
domains, or against a static comparator" (Zhang 2026; Zhang–Cutkosky 2022). Gradient clipping,
the standard primitive, clips to a threshold that tracks the local scale and therefore still
transmits scale drift into the step size. None target the *drifting-scale × moving-comparator*
regime.

## Central hypothesis
Gradient heavy tails are (largely) a **volatility-clustering artifact of a predictable-but-
drifting scale**, not intrinsic. Concretely: the *pooled* gradient-norm tail is genuinely heavy
(Hill α̂≈2.4), but the *causally scale-normalized* gradient ‖g_t‖/s_t — what a learner acts on —
is much lighter (α̂≈2.9–3.7). The lightening is a property of **serial dependence**, not the
marginal (an order-shuffle destroys it; the same normalization is tail-index-preserving on iid
streams). A bounded ~6× drift cannot move a tail index (Breiman 1965); a predictable
heavy-tailed conditional scale can (Kesten/GARCH); a GARCH surrogate with Gaussian innovations
reproduces both the heavy pooled tail and its removal.

## Proposed method
**SN-OMD**: `ĝ_t = clip(g_t/s_t, M)`, `w_{t+1} = Π_W(w_t − (η/√t)·ĝ_t)`, where `s_t` is a
*predictable* robust scale tracker (winsorized EMA / two-timescale envelope / block median).
Dividing by `s_t` first replaces clipping's scale-*dependent* step bound `M·s_t` with a
scale-*free* bound `M`. SN-OMD is a one-parameter family in `M` interpolating normalized-GD
(`M→0`) and uncapped scale-adaptive OGD (`M→∞`).

## Main theoretical contribution
- **Theorem 3.1 (Stability, unconditional):** `‖ĝ_t‖≤M` deterministically ⇒ iterates bounded
  on bounded `W`, `O(√t)` on `ℝ^d`, for *any* rate/drift/realization, no moment assumption.
  (A *family* property of any scale-free-capped update, not unique to SN-OMD.)
- **Theorem C.2 (Dynamic regret):** under a finite drifting p-th moment (Assumption 2.1) and a
  two-sided scale-tracking bracket (Assumption C.1), SN-OMD with `M=Θ(T^{1/p})` attains the
  per-regime rate `T^{1/p}` w.p. ≥1−δ, with the scale drift entering as an explicit
  `√W_s`≈`√T` factor and a peak-to-mean-ratio·log(1/δ) constant. **Explicitly per-regime**
  (global is the vacuous `T` at p=2). Discharge of Assumption C.1 is a *sketch* (Prop. D.5,
  "informal").

## Main empirical contribution
On the Jane Street dataset (+ a second crypto market, appendix): (1) the pooled gradient tail
is heavy and *conditionally removable*, established by shuffle/iid/GARCH controls; (2) a whole
family of bounded scale-free updates stays bounded (0/10 window divergences) where OGD (9/10
per-step) and scale-dependent clipping / the uncapped endpoint (6/10 per-row) diverge; (3)
within the bounded family no single member dominates both protocols — SN-OMD with a block-median
scale only *ties* the best baseline (Cutkosky–Mehta normalize-and-clip) per-row.

## Actual contribution (one sentence)
*A measurement-plus-stability paper: it shows the heavy tail of an online learner's loss
gradients on drifting-scale market data is a predictable-scale (volatility-clustering) effect
that a causal robust normalizer largely removes, and packages the fix as a scale-free-capped
OMD family whose finite cap gives an unconditional (moment-free) stability guarantee — while
being candid that the dynamic-regret theory is per-regime and the accuracy is a tie, not a win.*

## Single strongest claim
The **stability dichotomy**: every finite-cap bounded scale-free method stays bounded across ten
frozen windows (0/10), while OGD and the uncapped/scale-dependent endpoints diverge. This is
backed by a deterministic theorem (3.1, verified) *and* the 10-window replication, and it does
not depend on an accuracy win.

## Single most vulnerable claim
Two candidates, depending on axis:
- *Scientific:* that the residual normalized tail is "dominated by causal-estimation cost with
  no heavy tail separately resolvable" — this rests on the GARCH-surrogate calibration in
  `tab:residual`, whose surrogate rows have **no committed generator on the reviewer-facing
  remote** (repro gap; honestly hedged in the text).
- *Theoretical:* that SN-OMD "attains `T^{1/p}`" — true only per regime and only under an
  undischarged tracker assumption (both disclosed).

## What must be true, mechanically, for the thesis to hold
1. The pooled gradient tail is genuinely heavy at a fixed `w*` (α̂<2 possible). — hash-pinned input.
2. Dividing by a *predictable* (F_{t−1}-measurable) scale lightens it, and this is causal —
   i.e. survives no look-ahead. — shuffle/iid/centered-vs-trailing controls.
3. The lightening is serial-dependence-driven, so a marginal-preserving shuffle kills it. — shuffle control.
4. A bounded drift alone cannot do it (needs a heavy-tailed *conditional* scale). — Breiman/Kesten + GARCH surrogate.
5. The scale-free cap yields stability a scale-dependent threshold cannot. — Theorem 3.1 + divergence counts.
