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
