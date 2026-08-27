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

