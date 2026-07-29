# Distribution-free sequential learning under a drifting heavy tail — a self-contained theory note

A clean, standalone consolidation of the theory (details/derivations in `THEORY.md`
and `THEORY_SNOGD.md`; experiments in `FINDINGS.md`). Reads top-to-bottom without the
other files. **Rigor tags:** `[R]` proved here (verified), `[E]` established/cited,
`[G]` gap with route identified. Nothing tagged `[R]`/`[E]` is conjectural.

---

## 1. Problem

Online prediction, `t = 1..T`. The learner plays `w_t ∈ 𝒳 ⊆ ℝ^d` (diameter `D`;
`𝒳=ℝ^d` handled in §6), observes a convex loss `ℓ_t` (for us weighted squared error
`ω_t(⟨w_t,φ_t⟩−y_t)²`), and receives a stochastic subgradient `g_t` with
`E[g_t|ℱ_{t-1}] = ḡ_t ∈ ∂ℓ_t(w_t)`. **Only weak, time-varying moment control** is
assumed on the noise `ε_t = g_t − ḡ_t`:
```
    E[ ‖ε_t‖^{p_t} | ℱ_{t-1} ]  ≤  σ_t^{p_t},     p_t ∈ (1,2],
```
with **both `σ_t` and `p_t` drifting** and possibly `p_t < 2` (infinite variance) on
some rounds. Write `p := inf_t p_t` (worst tail). *Distribution-free* = the algorithm
knows none of `σ_t, p_t, D, ‖u‖`. Performance is **dynamic regret** against a moving
comparator `u_{1:T}` with path length `P_T = Σ_t‖u_t − u_{t-1}‖`:
```
    R_T(u_{1:T}) = Σ_t [ℓ_t(w_t) − ℓ_t(u_t)]  ≤  Σ_t ⟨ḡ_t, w_t − u_t⟩.
```
This is the notion nonstationary (regime-switching) streams require. On Jane Street the
gradient scale drifts `5.9×` and the tail index `α_t ∈ [1.5,3.3]` dips below 2 on ~6%
of days (FINDINGS 9) — the problem is real, not assumed.

## 2. The fundamental limit  `[E]`

Under only a finite `p`-th moment the best mean estimator has error
`σ·n^{−(1−1/p)}` (endpoints: `p=2→n^{−1/2}`; `p→1→` constant). Aggregated online this
forces regret `≍ T^{1/p}`, and this is a matching lower bound (interpolates classical
`√T` at `p=2` to trivial linear `T` at `p→1`). Two refinements matter here:
- **Static** regret (fixed `u`) is governed by the worst single regime,
  `≳ max_r σ_r L_r^{1/p_r}`.
- **Dynamic** regret (per-regime `u_r`) has the per-regime costs **add**,
  `≳ Σ_r σ_r L_r^{1/p_r}`  (regimes `r`, lengths `L_r`).

**Measured wall (FINDINGS/THEORY):** on Jane Street the static budget is `0.16×√T`
(no wall — near-`√T` static regret is reachable), but the **dynamic** budget is
`6.8×√T` at both 60-day and full-record scale. **So near-`√T` *dynamic* regret is
information-theoretically out of reach; the achievable dynamic rate is the worst-tail
`T^{1/p}`, `p<2`.** The wall sits exactly at heavy-tails × nonstationarity.

## 3. The algorithm: Scale-Normalized OMD

`s_t > 0` a **predictable** (`ℱ_{t-1}`-measurable) robust scale estimate; `M`, `η`
constants.
```
    v_t = g_t / s_t ;      ĝ_t = v_t·min(1, M/‖v_t‖) ;      w_{t+1} = Π_𝒳(w_t − η ĝ_t).
```
**Why normalize instead of clip.** Clipping to a scale-*dependent* threshold
`τ_t = c·s_t` gives a step `∝ min(‖g_t‖, c s_t)`, which **scales with the drifting
`s_t`** — a turbulent regime produces large steps → divergence (FINDINGS 7). Dividing
by `s_t` first gives a step `∝ min(‖g_t‖/s_t, M)` — **scale-invariant**, bounded by the
constant `M`. That single factor `1/s_t` is the whole idea.

## 4. Main results

**Theorem 1 (Stability — unconditional).**  `[R]`
Because `‖ĝ_t‖ ≤ M` deterministically (every round, every realization, *no moment
assumption*), the iterates are bounded for **any** learning rate: `‖w_t‖ ≤ D` on a
bounded domain, and `≤ ‖w_1‖ + 2Mη√t` on `ℝ^d`. **SN-OMD cannot diverge under any
scale or tail drift.** (This is the theorem behind Finding 10's 100% bounded / never
diverges / graceful degradation, and the sharp contrast with scale-dependent clipping.)

**Theorem 2 (Dynamic regret).**  `[R for the rate, under A1; G for full adaptivity]`
Assume **(A1)** the predictable scale brackets the local scale, `c₁σ_t ≤ s_t ≤ c₂σ_t`.
With `M = Θ(T^{1/p})` and `η` tuned, w.p. `≥ 1−δ`, simultaneously for all `u_{1:T}`:
```
    R_T(u_{1:T})  =  O( D·S_1^{1/p}·W_s^{1−1/p}  +  (scale-weighted path term) )
                  ≤  O( (sup_t σ_t)·(D + √(D·P_T))·T^{1/p}·polylog(T/δ) ),
```
where `S_1 = Σ_t σ_t`, `W_s = s_1 + Σ_t (s_t − s_{t-1})_+` (upward variation of the
scale), and the path enters **scale-weighted** as `P_T^s = Σ_t s_t‖u_t−u_{t-1}‖`.
*Sanity:* `p=2`, `σ_t≡σ` ⇒ `σ(D+√(D P_T))√T` — exactly Zinkevich's dynamic-OGD rate.

**The clean reading of Theorem 2 — the two nonstationarities separate:**
```
    R_T  ≲  (sup_t σ_t) · ( D + √(D P_T) ) · T^{1/p}
             \_________/   \___________/     \_____/
             scale level   dynamics (P_T)    tail p
```
- **tail index `p` → the RATE exponent** `T^{1/p}` (the §2 wall, unavoidable);
- **scale drift → only a constant** `(W_s/σ_max)^{1−1/p}` (measured ≈ `1.5×`);
- **nonstationary comparator → the scale-weighted path** `P_T^s` (a move costs more in a
  turbulent regime — the heavy-tail analogue of Zinkevich's `P_T`).
Dividing by `s_t` does **not** smuggle a `sup σ_t` *rate* penalty; the rate stays optimal
`T^{1/p}` and the scale drift is a constant. This is why SN-OMD is both stable and
accurate (FINDINGS 10: highest `R²` *and* never diverges).

## 5. Proof architecture (how Theorem 2 is built)

Analyze SN-OMD in its **adaptive-step form**: it is OGD with step `η_t = η/s_t` on the
clipped raw gradient `θ_t g_t`, `θ_t = min(1, M s_t/‖g_t‖)`. Then the telescope yields
the *true* (unweighted) regret directly. Four ingredients:

1. **Varying-step telescope + summation by parts** `[R, verified]`:
   `Σ_t s_t(‖w_t−u_t‖² − ‖w_{t+1}−u_t‖²) ≤ D²·W_s + 2D·P_T^s`. (Numerically checked on
   2000 random instances, both static and moving-comparator.) This is where `W_s` and
   `P_T^s` arise, and the only place nonstationarity enters.
2. **Clipped second moment** `[R]`: `‖clip(v,M)‖² ≤ M^{2−p}‖v‖^p` ⇒ curvature term
   `≲ (η/2)M^{2−p}S_1`.
3. **Clipping bias** `[R]`: `‖(1−θ_t)g_t‖`'s conditional mean `≲ σ_t/M^{p−1}` ⇒
   bias term `≲ D·S_1/M^{p−1}`.
4. **High-probability** `[E]`: the martingale `⟨E[·|ℱ]−·, w_t−u_t⟩` (bounded increments)
   via Freedman gives a same-order term with the `log(1/δ)`.

Summing and optimizing `η` then `M = Θ(T^{1/p})` balances curvature against bias and
yields Theorem 2. Endpoint checks pass (`p=2` static → `√T`; dynamic → Zinkevich).

## 6. Distribution-free composition (the remaining known-technique work)  `[G]`

Three unknowns, three standard devices; each composes with the above:
- **unknown `σ_t`** → the scale tracker `s_t` (by construction; the crux novelty vs the
  *static* clip `τ ≍ σ^{1/p}T^{1/p}` of Zhang–Cutkosky, which bakes in one `σ`);
- **unknown `p`** → doubling/adaptive `M` (or the `p`-agnostic clipping of ALT-2026),
  `log` cost;
- **unknown `‖u‖` / unbounded `𝒳`** → the parameter-free coin-betting + self-cancelling
  potential of Zhang–Cutkosky, for which `‖ĝ_t‖ ≤ M` is exactly the required input.

## 7. Honest status and the one remaining sub-result

| piece | status |
|---|---|
| Stability (Thm 1) | `[R]` proved, unconditional |
| Static `T^{1/p}` rate | `[R]` derived + verified (§5 i–iv) |
| Dynamic `P_T^s` term | `[R]` derived + verified (telescope) |
| High-probability (Freedman) | `[E]` standard |
| unknown `p`, `‖u‖` adaptivity | `[G]` established techniques, to compose |
| **Assumption A1 (scale tracking)** | discharged — see below (`A1_TRACKER.md`) |

**A1 is now largely discharged** (`A1_TRACKER.md`, formalized in `THEORY_FORMAL.md §4`).
Key points: (a) only the *lower* bracket `s_t ≥ c₁σ_t` is essential (stability + rate);
over-estimation is benign — so the requirement is **one-sided**. (b) Unavoidable cost
`[R]`: `W_s ≥ (c₁/2)Σ_{regime jumps}σ_t`. (c) A **two-timescale envelope** tracker holds
the lower bracket at 100% on the real scale process. (d) *Formal refinement:* the
envelope's `W_s ≈ sup_t s_t + ρ·Σ_t s_t`, so `W_s = O(V_σ^+)` holds **only if the decay
`ρ ≍ 1/L`** (regime length); too fast a decay churns and gives `W_s = Θ(T)` → linear
regret. Under `ρ ≍ 1/L`, `W_s = O(N σ̄) = O(V_σ^+)` and the rate is dynamic-optimal. The
residual `[G]` is adaptivity of `ρ` to an unknown regime length (experts/doubling) plus
the bounded post-jump lower-bracket lapse — known-technique, not conceptual.

## 8. Takeaway

> **Heavy tails set the rate (`T^{1/p}`, unavoidable); nonstationary scale is only a
> constant; the right algorithm decouples the step from the scale by normalizing, not
> clipping.** SN-OMD provably never diverges (Thm 1) and attains the worst-tail dynamic
> rate up to the scale-drift constant and a scale-weighted path length (Thm 2), matching
> the information-theoretic wall — and the experiments corroborate both halves
> (FINDINGS 10). What clipping-to-a-scale gets wrong is transmitting the scale drift into
> the step; `1/s_t` fixes it.

---

### References
Catoni 2012; Devroye–Lerasle–Lugosi–Oliveira 2016; Lugosi–Mendelson 2019 (robust mean);
Zinkevich 2003 (dynamic OGD); Orabona–Pál 2018 (scale-free); Freedman 1975 (martingale
tails); Zhang & Cutkosky 2022 / arXiv:2210.14355 (parameter-free heavy-tailed,
cancellation potential); Zhang–Zhang–Zhou / arXiv:2508.07473, ALT 2026 (`p`-agnostic
clipping, `T^{1/p}` optimality); Nguyen et al. 2023 / arXiv:2302.05437 (high-prob
clipped-SGD). Full pointers in `THEORY.md` / `THEORY_SNOGD.md`.
