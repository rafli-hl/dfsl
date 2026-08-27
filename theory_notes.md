# Theory notes — D1/T1, variation-adaptive dynamic regret

Direction D1/T1, registered in `experiment_matrix.yaml` (tenth document) at `5546e0f`, kind
`THEORY`, **before** any derivation. 2026-08-24.

**Outcome: FAILURE against the registered success criteria.** Criterion (a) — a complete
written proof — is not met. The obstruction is located precisely below and the theory
contribution is demoted rather than defended, per the registered failure path. Two findings
came out of the attempt that are worth more than the attempt was.

---

## Step 0 — the premise check, and a sharpening of it

The reframe rests on the causally normalized gradient having tail index above 2. Measured,
from committed artifacts:

| quantity | Hill `α̂` |
|---|---|
| raw gradient norm @ `w*` | **2.43** |
| raw gradient norm @ `0` | 2.40 |
| causally normalized (winsorized-EMA `s_t`) | **≈3.73** (2.9–3.7 across trackers) |

**The premise holds, and the situation is sharper than "the measurement empties the theorem".**
`ass:moment` assumes `E[‖g_t‖^{p_t} | F_{t-1}] ≤ σ_t^{p_t}` with **`p_t ∈ (1,2]`** and
`p := inf_t p_t`. The range is capped at 2 by the assumption itself.

A finite `α`-th moment implies the assumption at any `p ≤ α`. Since the measured raw index is
2.43 > 2, the assumption *is* satisfiable — but only by taking `p = 2`, its ceiling. And `p = 2`
is exactly the corner where `Remark D.3` reports the global bound `T^{1/p+1/2}` becomes the
vacuous `T`.

So the measurement does not merely fail to help the theorem. **It pins the theorem to its own
worst case**, because the theory's parameter cannot exceed 2 while the data's index does. The
paper states the consequence in passing — *"with `p > 2` the cap is for stability alone"* (§5)
— without connecting it to `Remark D.3`.

*Correction to the brief's §2.2:* it says the headline finding "empties the headline theorem of
content in the regime it measures." Directionally right, but the exponent is only literally
vacuous **at** `p = 2`. Taking the measured raw 2.43 at face value would give `T^{0.91}`, and the
normalized 3.73 would give `T^{0.77}` — sublinear, not vacuous. The vacuity is a consequence of
`ass:moment`'s `p ≤ 2` cap, not of the measurement alone. That is a stronger and more precise
statement than the brief's, and it survives a reviewer who checks the exponent arithmetic.

Verified numerically: with `W_s ~ T` and `S_1 ~ T`, the first line of `eq:mainbound` has
exponent `½ + ½ + (2−p)/(2p) = 1/p + ½` exactly, for every `p` tested (1.2, 1.5, 2.0, 2.43, 3.73).
The paper's stated exponent is correct.

---

## Finding A — the registered objective is already met by the existing theorem

D1's target, as the brief and my own registration state it, is *"a bound whose nonstationarity
cost is explicit and measurable in `V_σ⁺`."*

**`thm:regret` already is that bound.**

```
R_T = O( (D√W_s + √(D·P_T^s))·√S_1·T^{(2−p)/(2p)}·(sup σ/σ̄)·log(1/δ)
         + (sup σ)·D·T^{1/p}·log(1/δ) )
```

with `W_s = s_1 + Σ(s_t − s_{t−1})_+` — the tracker's upward variation — and
`P_T^s = Σ s_t‖u_t − u_{t−1}‖`. §3 says so explicitly: the scale-path quantities
*"`W_s`, `P_T^s`, `S_1` enter as honest inputs rather than known constants."* And `W_s ≈ 6.6·V_σ⁺`
is measured (§ tracker).

So there is no variation-adaptive bound to go and derive; one exists. **The problem is not that
the bound lacks a variation term — it is that the variation is measured to be `Θ(T)`.** The paper
says this itself: *"The drift is a genuine rate; the tracker controls only its constant."*

**Consequence: D1 as scoped in the brief is not available as new work.** Re-deriving a `V_σ⁺`
bound would re-derive `thm:regret`. This is a finding about the brief's §3, not about the paper.

---

## Finding B — the genuinely open object, and the rate it would give

`Remark D.3` names it: *"Escaping the `√T` would need a switching bound in the regime count,
left open."*

**Target rate.** Suppose the horizon decomposes into `N` regimes of lengths `T_1..T_N`,
`ΣT_i = T`, each a horizon on which `W_s = O(1)` (the paper's own definition of a regime).
Applying the per-regime `T_i^{1/p}` guarantee on each and summing, Hölder gives

```
Σ_i T_i^{1/p}  ≤  N^{1−1/p} · T^{1/p}        (equality at equal lengths)

⇒   R_T  =  Õ( N^{1−1/p} · T^{1/p} )
```

Verified numerically over 20 000 random length-splits at `p ∈ {1.5, 2, 3.73}`: the ratio
`Σ T_i^{1/p} / (N^{1−1/p}T^{1/p})` never exceeds `1.000000`, with equality at equal lengths, as
Hölder requires.

**Both limits are correct**, which is the sanity check that makes the rate believable:

- `N = 1` (stationary scale) → `T^{1/p}`, recovering the per-regime theorem.
- `N = T` (every round its own regime) → `T^{1−1/p}·T^{1/p} = T`, recovering the known vacuous case.

The rate therefore interpolates exactly between the two endpoints the paper already
establishes, and would be a strict improvement over `T^{1/p+1/2}` whenever `N = o(T^{p/(2(p−1))})`.

---

## The obstruction — GAP, and why naive segmentation does not work

**Summing per-regime bounds is not valid for SN-OMD as deployed.**

The step schedule is `η_t = η/√t`, **global and never re-expanded**. On a segment starting at
`t_i`, the OMD initialization term is

```
D² / (2·η_{t_i+T_i})  =  D²·√(t_i + T_i) / (2η)  ≈  D²√T / (2η)   for late segments,
```

**not** `D²√T_i/(2η)`. The algorithm's step has already decayed to its horizon value and does not
grow back after a regime change, so each new regime pays the *full* horizon initialization cost.
Summing over segments gives

```
R_T = O( N·D²√T/η + … )   —   i.e. O(N√T),
```

which is worse than the target `N^{1−1/p}T^{1/p}` for large `N`, and in particular does not beat
the existing `T^{1/p+1/2}` in the regime where it matters. **The `√T` the remark wants to escape
is re-introduced by the schedule, once per regime.**

**What would resolve it, and what I have not done.** The standard route is a strongly-adaptive
wrapper — Hazan–Seshadhri adaptive regret, Daniely–Gonen–Shalev-Shwartz SAOL, or
Follow-the-Leading-History — which supplies per-interval guarantees from arbitrary entry states
and so removes the dependence on a single global schedule. Wrapping SN-OMD would require:

1. showing the per-regime SN-OMD bound holds on an **arbitrary interval from an arbitrary entry
   state** (plausible: the domain has diameter `D`, so the entry iterate is within `D` of any
   comparator — but the Freedman step's predictability structure needs re-checking per interval);
2. a **union bound over the `O(T log T)` intervals** the wrapper maintains, turning `log(1/δ)`
   into `log(T/δ)` in the high-probability step;
3. re-deriving the clipping-bias term `D·Σ(‖g_t‖ − M·s_{t−1})_+` under the wrapper, since `M`
   is tuned to the horizon and each interval has its own effective horizon.

**I have not written this proof.** Steps 1–3 are marked **GAP**. I am not asserting the theorem.
Per the registered anti-fabrication commitment, a derivation strategy with a located obstruction
is *not* a result, and the manuscript already carries one sketched assumption that §E.8 honestly
calls *"a sketch, not a theorem"* — a second one dressed as a theorem would be the worst
available outcome.

---

## Verdict against the registered success criteria

| criterion | status |
|---|---|
| (a) complete proof, not a sketch | **NOT MET** — steps 1–3 are GAP |
| (b) sublinear in `T` at `p = 2` | target rate is, for `N = o(T)`; **unproven for the deployed algorithm** |
| (c) every quantity measurable | `N` is measurable in principle from `s_t` (regime = interval with `W_s = O(1)`); untested |
| (d) reduces to the known bound under stationary scale | **MET** — `N = 1` gives `T^{1/p}` |

**Registered outcome: failure.** Per the brief's decision rule, this means **Structure C**
(measurement-first), with `Theorem 3.2` moving to a supporting role rather than carrying the
contribution.

---

## What this changes

1. **D1 is not a one-session direction, and not for the reason the brief gives.** The
   variation-adaptive bound already exists; the open object is the switching bound, and it needs
   a strongly-adaptive wrapper, which is a substantial piece of work with three identified
   sub-problems.
2. **The `p ≤ 2` cap in `ass:moment` is the sharper framing of the §2.2 tension** and should
   replace the "vacuous theorem" phrasing, which overstates at the measured indices and would
   lose an argument with a reviewer who checks the arithmetic.
3. **`N^{1−1/p}T^{1/p}` is a concrete, checkable target** with both limits verified. It gives a
   future attempt something specific to aim at, and something a reviewer can falsify.

---

# D1B — the switching bound is unavailable, not merely underived (2026-08-26)

D1 ended by naming the open object: Remark D.3's switching bound in the regime count, target
rate `R_T = Õ(N^{1−1/p}·T^{1/p})`, obstruction located in the global step schedule, three
sub-problems marked GAP. D1B registered a premise check *before* attacking those, and the check
settles the question without needing them.

## The precondition

`N^{1−1/p}·T^{1/p}` beats the current `T^{1/p+1/2}` only when `N = o(T^{p/(2(p−1))})`, and it
beats the vacuous `T` only when **N is sublinear in T**. At `N = Θ(T)` the switching rate is
`T^{1−1/p}·T^{1/p} = T` for every `p` — the exact bound the direction exists to escape. So the
whole route has a measurable precondition, and it is one the paper had never checked even though
it measures the closely related `W_s = Θ(T)`.

## The measurement

`research_d1b_regime_count.py`, on the committed 200 000-round scale process, using the paper's
own definition of a regime — a horizon over which the tracker's upward variation is `O(1)`.
Greedy partition: accumulate upward variation, close a segment when the budget `c` would be
exceeded, so a single step larger than `c` forms its own segment. That is exactly Appendix E.8's
"piecewise-slow variation plus arbitrary jumps at N change points".

| tracker | exponent of `N(T)` | measurable? |
|---|---|---|
| winsorized EMA (deployed) | 1.20 – 1.24 | yes, up to 1 825 segments |
| two-timescale envelope (proven) | 1.16 – 1.21 | yes at `c ≤ 2` |
| block median (`B=10⁴`) | 0.00 – 0.37 | **no** — 1 to 3 segments over the whole record |

`c` swept over `{0.5, 1, 2, 5, 10}` median scales.

**The reliability rule is Table 6's, not one invented here.** Table 6 already restricts the
corresponding `W_s ~ T^β` fit to horizons with `≳50` blocks and calls the large-`B` decline "a
finite-horizon artifact — `B=10⁴` has only ~20 blocks". Applying the same rule discards 7 of 15
combinations. **Note which way it cuts:** every discarded combination is one whose exponent
looked *sublinear*, so the rule removes the only evidence that would have licensed proceeding to
the derivation. A filter that makes the conclusion harder to reach is not a filter chosen to
reach it.

Over the 8 surviving combinations the exponent is **1.155 – 1.240**, never below 1.15. An
exponent above 1 cannot persist asymptotically (`N ≤ T`), so the honest reading is *at least
linear*. Table 6's `β ≈ 1.0–1.25` for `W_s` agrees — recorded as an internal consistency check,
**not** as corroboration. Corrected in D1C: `W_s` counts upward moves and `N` counts the
boundaries those same moves induce, so they are close to one measurement twice, not two views of
one process. The claim rests on the `N` measurement alone.

## Verdict

**Success under registered criterion (a): the negative result is established.** The derivation
was not attempted, per the registered decision rule.

The switching bound is not an open lemma on this data. It is unavailable: no proof of that form
can be non-vacuous at `N = Θ(T)`, whoever writes it. The residual `√T` that makes `thm:regret`
per-regime is therefore a property of the measured drift, not a gap in our proof — which is a
*stronger* and less flattering statement than "left open", and it is now what the manuscript
says in Remark D.3, the Table 6 caption, Section B.2, Limitations, and a new appendix
subsection.

## What this does not close

A bound in some other nonstationarity functional, and a stream on which regimes are rarer. The
measurement is one process, and `N` is defined against a tracker; a tracker coarse enough to see
one regime also fails Assumption D.1's lower bracket, so "make the tracker coarser" is not an
escape. Three GAP sub-problems from D1 remain unproven and are now also unmotivated on this
data.

---

# D1C — the same count empties Prop F.1's discharge (2026-08-26)

D1B closed the switching route. D1C asks whether the same measurement voids something the paper
still presents as *discharged* rather than open. It does.

## The condition, and both of its factors

Prop F.1 buys the lower bracket at one added term `O(D·N·W·sup_t σ_t)`, "dominated whenever
`NW ≪ T^{1/p}`". Both factors are measurable and neither had been measured.

**`N`** is at least linear (D1B), and — closing seam S1 — that is not an artifact of our
adaptive filters. A tracker-free segmentation over non-causal block medians gives boundaries per
block of `0.193 → 0.210` (`c=0.5`) and `0.121 → 0.135` (`c=1`) as the block length runs
`50 → 1000`: a roughly constant *rate*, i.e. `N ∝ T` with nothing adaptive in the loop.

**`W`** is not free either, which the paper's own proof sketch says: the blocking step needs
`≍W/ℓ` near-independent blocks of length `ℓ ≳` the mixing time. The scale process's rank
autocorrelation is `0.180` at lag 1 and still `0.069` at lag 2000 — it never reaches 0.05 in the
range tested — so `ℓ ≳ 2000` and `W ≳ 2×10⁴`.

## (a) asymptotic — unfavourable at every admissible p

`NW/T^{1/p}` grows like `T^{β−1/p}`. Evaluated at **`β = 1` exactly**, not the fitted 1.16–1.24,
so the conclusion cannot be attacked through the finite-horizon artifact:

| p | 1/p | β − 1/p | |
|---|---|---|---|
| 1.3 | 0.769 | +0.231 | diverges |
| 1.5 | 0.667 | +0.333 | diverges |
| 2.0 | 0.500 | +0.500 | diverges |

`β − 1/p = 1 − 1/p > 0` for every `p > 1`. There is no admissible `p` at which the term is
asymptotically dominated.

## (b) at the measured horizon — unfavourable where it counts

`T = 200 000`, envelope tracker, measurable `c` only:

| W | p=1.3 | p=1.5 | p=2.0 |
|---|---|---|---|
| 64 (tracker's own; ignores the blocking requirement) | 0.46 – 1.7 | 1.6 – 6.0 | **12 – 46** |
| 2×10⁴ (what the proof needs) | 144 – 537 | 503 – 1877 | **3846 – 14356** |

**H_D1C is falsified in exactly two of eighteen measurable cells** — `c=1, W=64, p=1.3` (0.89)
and `c=2, W=64, p=1.3` (0.46). Reported because the registration required reporting them, and
they do not rescue the proposition: each needs `p = 1.3`, a heavier tail than the measured
normalized index admits (`ass:moment` caps `p ≤ 2` and C-14 records that the measurement pins it
*at* 2), **and simultaneously** `W = 64`, shorter than the proposition's own blocking argument
permits. Domination requires both a tail we do not have and a window the proof does not allow.

## S3 — the coarsening defence, costed

D1B asserted that a tracker coarse enough to see few regimes fails the lower bracket. Overstated
as a binary: Table 6's `B=10⁴` tracker holds the bracket at **0.93**, not 0. The accounting
reaches the same place — 7% of rounds violating, charged trivially at `O(D sup σ)` per round, is
`0.07·T = Θ(T)`. Coarsening trades an `O(NW)` lapse set for an `O(T)` violation set. Same wall,
different route, and now checkable rather than asserted.

## Verdict

**H_D1C survives in the operative regime.** Prop F.1 is not wrong — D1C says nothing about its
correctness — it is *empty here*. Its guarantee is real for a process with macroscopic regimes;
this process does not have them. What the paper actually leans on is §B.2's empirical discharge
(100% lower-bracket coverage, measured), and the manuscript now says that rather than implying
the analytical route is available.

## What this does not establish

Nothing about Prop F.1's correctness. Nothing about Prop 3.1, which is unconditional and uses no
drift model. Nothing about the divergence partition. And it does not reopen D1B, whose closure
rests on its own measurement.

---

# T4 — the separation theorem: falsified as framed, and what survives (2026-08-27)

Registered in `experiment_matrix.yaml` (fourteenth document) at `c84a766`, kind `THEORY`,
before any of this was run. The registration was written to be adversarial to its own
direction, and step 0 duly killed it.

**Outcome: FAILURE against the registered success criteria.** Criterion (a) — a complete proof —
is met only for the easy half. The half a *separation* needs, a lower bound forcing
scale-dependent methods to fail, is a GAP. Reported as incomplete, as D1/T1 was.

## Step 0 — the direction's own falsification condition was already met

D3/T4 carried this from its original registration: *"if scale-dependent clipping can be made
stable ... by a rate schedule alone, the partition is about tuning, not structure."*

Every scale-dependent method has a strictly positive stable rate, in **every** committed
artifact that measures it:

| method | `lr_sensitivity` | `fair_tuning` | `continuous_stream` |
|---|---|---|---|
| OGD | 1e-3 | 2e-3 | 2e-3 |
| AdaptiveClip | 1e-2 | 2e-3 | **3e-2, top of grid, never diverges** |
| RobustOMD (catoni) | 5e-3 | 2e-3 | **3e-2, top of grid, never diverges** |
| RobustOMD (mom / trimmed) | — | 2e-3 | **3e-2, top of grid, never diverges** |

So the partition is **not** "one family diverges and the other does not, for all rate
schedules". A scale-oblivious constant rate stabilises the scale-dependent methods. **T4 as
framed is falsified.** No redefinition of "stable" is applied to rescue it.

## What replaces the two-way contrast: two independent properties, not one

The successor H_T4' (registered at the same time, so it could not be tuned to step 0's
result) proposed three tiers by homogeneity degree. Working the algebra out, **that was not
quite right either, and the correction is an improvement.** Write the update
`w_{t+1} = w_t − η_t h_t`, `η_t = η/√t`, `h_t = Φ_t(g_1,…,g_t)`. Two *independent* properties
matter, not one:

- **bounded**: `‖Φ_t‖ ≤ B` for a constant `B` independent of the stream;
- **degree-0 (scale-invariant)**: `Φ_t(λg) = Φ_t(g)` for every `λ>0`.

|  | bounded | unbounded |
|---|---|---|
| **degree 0** | SN-OMD (`B=M`), normalized-GD (`B=1`), **AdaGrad-Norm** (`B=1`) | the uncapped `M→∞` endpoint |
| **degree 1** | impossible unless `Φ≡0` | OGD, AdaptiveClip, RobustOMD |
| **neither** | **the fixed-τ clip** (`B=τ`) | — |

The fixed-τ clip is the cell H_T4' missed: `Φ_t(λg) = g_t·min{λ, τ/‖g_t‖}`, which is degree 1
below the threshold and degree 0 above, so it is homogeneous of **no** degree — yet bounded.
Verified numerically: the degree-1 methods return `B(2g)/B(g) = 2.0000` and
`B(10g)/B(g) = 10.0000` exactly.

## Theorem A (stability) — proved, and it is Prop 3.1 with the hypothesis widened

*If `‖Φ_t‖ ≤ B` for every stream, then `‖w_t‖ ≤ ‖w_1‖ + 2ηB√t` on `ℝ^d`, and `‖w_t‖ ≤ D` on a
bounded domain.*

**Proof.** `‖w_{t+1}−w_t‖ = η_t‖Φ_t‖ ≤ ηB/√t`. Summing,
`‖w_t−w_1‖ ≤ ηB Σ_{k<t} k^{−1/2} ≤ 2ηB√t`, since `Σ_{k=1}^{n} k^{−1/2} ≤ 2√n`. The projection
step is a contraction, giving the bounded-domain case. No moment assumption is used. ∎

This is exactly Prop 3.1's argument; the only gain is that the hypothesis is now *boundedness
of the step map* rather than *the cap in SN-OMD's update*, so it visibly covers the fixed-τ
clip and AdaGrad-Norm, which the paper asserts belong to the family without deriving it.

## Theorem B (tuning transfer) — proved

*Let `S_λ` be the stream with every gradient scaled by `λ>0`, in the adversarial setting where
`g_{1:T}` is given. If `Φ` is degree 1, the trajectory under `(η, S_λ)` is identical to the
trajectory under `(λη, S_1)`. If `Φ` is degree 0, the trajectory under `(η, S_λ)` is identical
to that under `(η, S_1)`.*

**Proof.** Degree 1: `h_t(λg_{1:t}) = λ h_t(g_{1:t})`, so
`w_{t+1} = w_t − η_t·λ h_t(g_{1:t})`, which is the `λη` trajectory on `S_1`; induct on `t` from
`w_1`, which is `λ`-independent. Degree 0: `h_t(λg) = h_t(g)` and the same induction. ∎

**Corollary B.1.** The stable-rate set of a degree-1 method satisfies `H(S_λ) = H(S_1)/λ`, and
of a degree-0 method `H(S_λ) = H(S_1)`. So no fixed rate is stable uniformly over
`{S_λ : λ>0}` for a degree-1 method, while every degree-0 method's tuning transfers unchanged.

## Corollary C — the `1/s_t` factor is *forced*, not chosen

*If a degree-1 method is to have per-round displacement bounded by a constant `C` uniformly in
`λ`, its rate must satisfy `η_t ≤ C/(c\,ŝ_t)` — that is, `η_t ∈ O(1/ŝ_t)`.*

**Proof.** For the clippers, when the threshold binds (`‖g_t‖ ≥ c ŝ_t`) the step is exactly
`‖Φ_t‖ = c ŝ_t`, so displacement is `η_t c ŝ_t`; requiring `≤ C` gives the bound. The
non-binding branch has `‖Φ_t‖ = ‖g_t‖ < c ŝ_t` and is slack, so the binding branch is the
active constraint. ∎

Applying the forced rate `η/(√t\,ŝ_t)` to a degree-1 `Φ` *is* SN-OMD's update, up to the cap.
The manuscript says the two families "differ by the factor `1/s_t`"; Corollary C says that
factor is the **only** available repair, which is a stronger statement than the paper makes.

**This is the one place T4 earns something.** It explains a membership the paper asserts
without derivation: **AdaGrad-Norm**. Its step is `η g_t/√(Σ_{k≤t}‖g_k‖²)` — a degree-1 `Φ`
combined with a degree-**(−1)** rate, hence degree 0 overall, and bounded by `η` because
`‖g_t‖/√(Σ_{k≤t}‖g_k‖²) ≤ 1`. So AdaGrad-Norm is in the stable family *for the reason
Corollary C names*, not because it clips — it never clips. Symmetrically the corollary
predicts the fixed-τ clip's anomaly: bounded, so stable by Theorem A, but not degree 0, so its
useful rate does **not** transfer across scales — which is `fig:mechanism`(b), "a fixed clip
threshold cannot win", derived rather than observed.

## GAP 1 — the feedback case is not covered

Theorem B is stated for a **given** gradient sequence. In the experiments `g_t = 2(⟨w_t,x_t⟩ −
y_t)x_t` depends on `w_t`, so "rescale the stream" is not independent of the trajectory, and
the induction in Theorem B does not go through unchanged. Everything measured lives in the
feedback case. I have not closed this and do not claim it.

## GAP 2 — there is no lower bound, so there is no separation

This is the one that matters. Theorem A upper-bounds the bounded family. Nothing here proves
that an unbounded or degree-1 method **must** diverge — only that its upper bound is loose and
its tuning does not transfer. A separation needs a construction on which the scale-dependent
method provably fails while the bounded one provably succeeds, and I did not obtain one. The
plausible mechanism is that `ŝ_t` is a statistic of past gradient norms, which for a linear
model grow with `‖w_t‖`, so the threshold inflates as the iterate diverges and the
multiplicative feedback is never broken — but that is a *derivation strategy with a located
obstruction*, which the standing commitment says is **not a result**.

## What was measured, since the theorem is incomplete

- **Ceilings are ordered three ways** on one stream (`normalize_continuous.csv`, date[0,120),
  150k): OGD `[0.01,0.02)`, uncapped endpoint `[1,2)`, SN-OMD `[3,5)`, normalized-GD `≥8`.
  Tier 2 sits `100×` above tier 1 and at least `3×` below tier 3's floor. **Scale-invariance
  buys part of the gap and boundedness buys the rest**; they are separable, and the paper's
  two-way contrast does not express this.
- **The `P = η_max·B` invariant is INCONCLUSIVE, not falsified.** normalized-GD never diverges
  anywhere on the committed grid, so its ceiling is right-censored at `lr=8` and `P ≥ 8` is a
  lower bound, not a value. Taking the censored number at face value would have printed a
  `1.88×` spread and a verdict of FALSIFIED against the registered `1.68×` threshold — an
  artifact of the grid ending, so it is not recorded. Deciding it needs a wider grid, which is
  new compute and a separate registration.
- **The horizon effect is real but too slow to carry the weight.** `sup‖g‖` over prefixes of
  one fixed stream grows with fitted exponent `0.220`, against `1/α = 0.412` predicted from the
  committed Hill index `α=2.43`; a doubling of `T` costs a factor `1.17`, not the `5×` seen
  between two artifacts, so that `5×` cannot be attributed to horizon.

## What this does not establish

Nothing about Prop 3.1, which is correct and untouched. Nothing about the ten-window
divergence partition, which is measured at **frozen** hyperparameters and is a different claim
from a tuned ceiling. And no separation theorem — see GAP 2.

---

# T4B — the taxonomy correction, tested and rejected (2026-08-27)

Registered before execution (fifteenth document), with amendment 1 to the grid recorded before
any across-window result was seen.

**H_T4B is falsified, and that is the outcome favourable to the manuscript.** AdaptiveClip and
RobustOMD on the ten-window frozen instrument diverge **9/10 per-step**, precisely OGD's count,
and per-row are bounded but at mean `R²` of `−0.010` and `−0.007` — below OGD and an order of
magnitude below the bounded scale-free pack's `0.14`–`0.21`.

## Where T4's argument went wrong

Theorem A's hypothesis is `‖Φ_t‖ ≤ B` for a constant **independent of the stream**. A clipper's
bound is `c·ŝ_t`. On one window `sup_t ŝ_t` is a finite number, and I read that finite number as
if it were a constant of the method. It is a property of the window. T4's own 2×2 had already
placed the clippers in the degree-1 *unbounded* cell alongside OGD; the taxonomy correction
contradicted the classification it claimed to rest on.

## What survives, and it is the more interesting half

Theorem B predicts that a degree-1 method's stable-rate set moves with the stream, so a rate
tuned on one window need not survive another. Measured: the clippers tune to `lr = 5×10⁻³` on
window 1 and diverge on nine of the remaining windows, while every degree-0 method transfers at
`0/10`. **Theorem B's transfer prediction is confirmed on the paper's primary instrument.**
That is a proved statement making a falsifiable prediction that then held — which is what T4 was
supposed to produce and, in this narrower form, did.

## The invariant, corrected downward

`research_t4b_invariant.py` recomputes `sup‖g‖` at `w*` on the ceilings' own slice
(date`[0,120)`, 150k) rather than on `gradnorm_at_wstar.npy`'s date`[0,30)`/200k: `752.6`
against `1149.2`, a factor `1.53`. `P = η_max·B` then gives OGD `[7.5, 15.1)` and SN-OMD
`[15.0, 25.0)` — intersecting only in a `0.1`-wide sliver the grid cannot resolve, with C10S's
committed `P* = 11.5` **outside** it. The earlier cross-tier agreement was an artifact of mixing
two streams. Not confirmed.

## Scope, sharpened by an objection that looked like a counterexample

`app:grid` reports normalized-GD and Cutkosky--Mehta collapsing to `0.09 ± 0.21` per-step at
their frozen window-1 rates, attributed to overfitting. Both are **degree-0**, so if Theorem B
says degree-0 tuning transfers, this looks like the one place prediction and data disagree.

Checked against `windows_replication.csv`. Per-step, frozen at `lr = 5`, normalized-GD is
**0/10 diverged**, with `R²` running `0.371` down to `−0.202`. So **stability transferred
perfectly and accuracy did not**, and those are different properties:

| | divergences | accuracy |
|---|---|---|
| degree 1 (clippers, per-step) | **9/10** | n/a — diverged |
| degree 0 (normalized-GD, per-step) | **0/10** | collapses, mean `0.094` |

Theorem B claims only the first: degree-0 homogeneity makes the *set of rates at which the
iterate stays bounded* invariant to rescaling the stream. It says nothing about which rate
inside that set is most accurate. So there is no conflict, `app:grid`'s attribution is right,
and **degree separates the two failure modes** — degree one loses stability, degree zero keeps
it and can still lose accuracy. Stated in the appendix where the objection would be raised.

This is a scope statement, not a new prediction, and it is recorded as such: it makes Theorem B
narrower and therefore more falsifiable, not broader.

## Unchanged

GAP 1 and GAP 2 both stand. No lower bound, no separation theorem, and nothing here bears on
Prop 3.1.

