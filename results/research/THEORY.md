# Theory notes: the rates, the mechanism, and the price of a drifting tail

Companion to `PROBLEM.md` (the map) and `FINDINGS.md` (the measurements). This
document works through the *why* behind the rates, grounded in the literature,
and then reasons carefully about the piece nobody has done — a **drifting** tail
index. Throughout I mark **[established]** (a cited result) vs **[reasoning]** (my
own derivation/conjecture, to be proved or refuted). Written 2026-07-29.

---

## 1. Where the `T^{1/p}` rate comes from  [established]

**The atom: robust mean estimation under a finite `p`-th moment.** For i.i.d.
`X_1..X_n` with mean `μ` and `E|X−μ|^p ≤ σ^p`, `p ∈ (1,2]`, there is an estimator
(median-of-means, trimmed mean, or a `p`-Catoni) with, w.p. `≥ 1−δ`,

    |μ̂ − μ|  ≲  σ · (1/n)^{1 − 1/p}      (up to log(1/δ) factors).

Endpoints sanity-check the exponent `1−1/p`:
- `p = 2`  → `n^{−1/2}`  (the sub-Gaussian / finite-variance rate).
- `p → 1⁺` → `n^{0}` = constant → **no concentration, estimation impossible.**
The empirical mean does *not* achieve this — under heavy tails it is only
`n^{−1/2}` in probability via Chebyshev with a `δ^{−1/2}` (not `log 1/δ`) tail;
that polynomial confidence dependence is the whole reason robust estimators exist.
[Lugosi–Mendelson 2019 survey; Devroye–Lerasle–Lugosi–Oliveira 2016; Bubeck–
Cesa-Bianchi–Lugosi 2013.]

**From per-round estimation to regret.** In online learning round `t` effectively
averages `~t` gradients, so the per-round error is `t^{−(1−1/p)}` and

    Σ_{t=1}^{T} t^{−(1−1/p)}  ≍  T^{1/p}      ⇒   R_T ≍ ‖u‖ · σ · T^{1/p}.

**Same rate via the clipping bias–variance balance** (this is how Zhang–Cutkosky
and clipped-SGD get it). Clip gradients at threshold `τ`:
- *bias* (clipped mass, finite `p`-th moment):   `≲ T · σ^p · ‖u‖ / τ^{p−1}`.
- *post-clip std* (bounded 2nd moment `E ĝ² ≤ τ^{2−p}(σ^p+G^p)`):
  `≲ ‖u‖ · √( T · τ^{2−p} · σ^p )`.
Balancing bias vs std gives the optimal threshold and rate

    τ*  ≍  σ^{1/p} · T^{1/p},        R_T ≍ ‖u‖ · σ · T^{1/p}.

Both terms equal `‖u‖ σ T^{1/p}` at `τ*` (checked algebraically). This exposes the
key structural fact used later: **the optimal clip threshold `τ* ≍ σ^{1/p}T^{1/p}`
depends on a single global scale `σ` and index `p`.**

**Lower bound.** `T^{1/p}` is unimprovable: it interpolates the classical `√T`
(`p=2`) and the trivial linear `T` (`p→1`). [ALT 2026 arXiv:2508.07473 cites
matching lower bounds; Vural et al. 2022; and the "infinite variance" minimax line,
e.g. arXiv:2603.06851.]

---

## 2. The unbounded-domain obstruction and the "cancellation" fix  [established]

Why the unbounded, high-probability, parameter-free corner is hard, and how
Zhang–Cutkosky (arXiv:2210.14355) solve it:

1. **Parameter-free ⇒ exponentially large candidate iterates.** To compete with an
   unknown comparator norm `‖u‖` without being told its scale, the learner must
   "bet" on geometrically growing `‖w_t‖`. This is intrinsic, not a bug.
2. **Concentration then fails.** The noise term in the regret is
   `σ·√(Σ_t w_t² · log(1/δ)) + b·max_t|w_t|·log(1/δ)`. On a bounded domain
   `w_t² ≤ D²` tames it; with exponential `w_t` the conditional variance is
   `~4^t` and Freedman/Bernstein union bounds go vacuous.
3. **The fix — a self-cancelling potential.** They add a modified-Huber regularizer
   `ψ_t` with `Σ r_t(w_t) ≥ c√(Σ w_t²) − α`, so the regularization the algorithm
   pays *absorbs its own variance term* `√(Σ w_t²)`, while charging the comparator
   only `Õ(‖u‖√T)`. The `max_t|w_t|` term is killed with a `‖·‖_{log T}` norm.
4. **They still clip**, at the *static* `τ ≍ σ^{1/p}T^{1/p}` from §1, plus a bias
   offset `φ(w) ∝ (σ^p+G^p)|w|/τ^{p−1}`. Result: w.p. `1−δ`,
   `R_T(u) ≤ Õ(‖u‖ · T^{1/p} · log(1/δ))`.

**The load-bearing observation for us:** their clip threshold is calibrated to a
**single global `(σ,p)` and the horizon `T`**. It is *not* scale-tracking and it
assumes `p` is fixed. Both assumptions are exactly what our data breaks (Finding 9).

---

## 3. The price of a *drifting* tail index  [reasoning — to prove/refute]

Our measurement (FINDINGS 9): over 60 days `σ_t` drifts `5.9×` and the tail index
drifts, `α_t ∈ [1.17, 3.31]`, dipping **below 2** intermittently. So the honest
model is a *sequence* of moment bounds `E_t[‖ε_t‖^{p_t}] ≤ σ_t^{p_t}` with both
`σ_t` and `p_t` time-varying, and `p_t < 2` on some rounds.

**Claim (worst-tail-dominates).** Partition `[T]` into regimes `r` of length `L_r`,
each with local index `p_r` and scale `σ_r`. Apply the §1 lower bound *within* each
regime. Two cases, and the distinction matters:

- **Static regret** (one fixed `u`): dominated by the worst single regime,
      `R_T^{stat}  ≳  max_r  ‖u‖ · σ_r · L_r^{1/p_r}.`
- **Dynamic regret** (comparator `u_r` may change per regime — the right notion for
  regime-switching markets): the per-regime lower bounds **add**, so
      `R_T^{dyn}  ≳  Σ_r  σ_r · L_r^{1/p_r}.`
  This makes the "heavy budget" below a genuine dynamic-regret lower bound, not a
  heuristic.

Heavy-tail cost is **superadditive in badness**: it cannot be averaged away, because
`L^{1/p}` is convex-increasing as `p` shrinks. Consequences (static case):
- A single macroscopic heavy regime (`p_r ≈ 1.2`, `L_r ≈ cT`) forces
  `R_T ≳ T^{1/1.2} = T^{0.83} ≫ √T`. With our measured `α_min ≈ 1.17`, the worst-
  case exponent is `1/1.17 ≈ 0.85`.
- Even a *sublinear* heavy spell hurts: `L_r = T^{β}` at `p_r` contributes
  `T^{β/p_r}`, which exceeds `√T` whenever `β > p_r/2`.

**Corollary (a checkable survivability condition).** To retain a near-`√T` rate the
"heavy budget" must be controlled:

    Σ_{r : p_r < 2}  σ_r · L_r^{1/p_r}   ≲   σ̄ · √T.

i.e. infinite-variance spells must be **short**, `L_r ≪ T^{p_r/2}`.

**Measured on Jane Street (60-day span, `T ≈ 540k` rounds) — the condition FAILS.**
Taking a day as a regime (`nonstationarity_daily.csv`):
- **20% of days (12/61) are infinite-variance (`α_day < 2`)**, with `α_min = 1.17`
  (worst-case exponent `1/α_min ≈ 0.856`).
- The spells are **short but frequent**: the longest run of consecutive `α<2` days
  is only **2 days**, but they recur throughout the span.
- The heavy budget `Σ_{α<2} L_day^{1/α_day} ≈ 4{,}983`, which is **≈ 6.8× `√T`**
  (`√T ≈ 735`). Even the single worst day contributes `~9000^{1/1.2} ≈ 2100 ≈ 3√T`.

**Full-record check (131 days strided across all 1{,}699, `heavybudget_daily.csv`,
`fig_fullrecord_tail.png`) — refines the claim and splits it static vs dynamic.**
The first 60 days were *atypically heavy*; across the whole record:
- **6% of days are infinite-variance** (`α<2`), `α_min = 1.49`, **median `α = 2.69`**
  (finite variance, moderate heavy tail). So most days are `α∈(2,3)`, a minority heavy.
- **STATIC heavy budget** `max_r L_r^{1/p_r} = 1{,}075 = 0.16× √T_full` (`√T_full ≈
  6{,}865`). The worst single regime does **not** dominate `√T` at full scale.
- **DYNAMIC heavy budget** `Σ_r L_r^{1/p_r} ≈ 46{,}769 = 6.8× √T_full` — the same
  `~6.8×` as the 60-day span, and well above `√T`.

**Conclusion [reasoning, from measurement] — the wall is specifically DYNAMIC:**
- **Static regret** (one fixed comparator): a near-`√T` rate is *plausibly reachable*
  on the full record — no single regime's heavy tail is large enough to dominate
  (`0.16× √T`). Static heavy-tailed OL is essentially the solved Zhang–Cutkosky corner.
- **Dynamic regret** (comparator drifts with the ~daily regimes — the notion markets
  require): near-`√T` is *out of reach*. Summed across regimes the heavy budget is
  `~6.8× √T_full`, so the achievable dynamic rate is governed by the heavy tail, not
  by `√T`. **This is an information-theoretic wall, independent of the algorithm, and
  it sits exactly at the heavy-tail × nonstationarity intersection** — the same corner
  §2/§4 identify as open.

*Caveats:* daily Hill `α̂` is noisy (`k=500`); "regime = day" is a modeling choice
(coarser regimes lower the budget, finer raise it); the strided sample and the
`σ_r:=1` (scale-free) budget isolate the tail-index effect from scale drift. But `α`
dips to `1.49` genuinely, and the dynamic budget exceeds `√T` by ~7× at *both* the
60-day and full-record scales, so the static-vs-dynamic split is robust.

**Why the static-`τ` design (§2) is provably inadequate here** [reasoning]:
`τ ≍ σ^{1/p}T^{1/p}` set for a global `(σ,p)` is, under drift, either
- too small during high-`σ_t` regimes → clips almost everything → bias term
  `T σ_t^{p}/τ^{p−1}` blows up; or
- set for the worst case `(sup σ_t, inf p_t)` → far too loose in calm regimes →
  no protection and a huge post-clip variance budget.
There is no single `τ` that is simultaneously right for a `6×` scale range and a
`p_t` crossing 2. And Finding 9 shows a *scalar rolling* `τ_t = c·scale_t` can't fix
it either (track ⇒ step inherits the swing; smooth ⇒ lags). So adaptivity must be
in a *different variable* than a clip magnitude — see §4.

---

## 4. Synthesis: the achievable rate and the design constraint

**Conjectured achievable dynamic regret** for the four-way-open corner
(unbounded, high-probability, parameter-free, nonstationary) [reasoning]:

    R_T(u_{1:T})  ≍  (‖u‖ + P_T) · sup_t σ_t · T^{1/p_min},   p_min = inf_t p_t,

when the heavy budget above is *not* controlled; and the better
`(‖u‖+P_T)·σ̄·√T`-type rate only when it *is*. The two genuinely open theory
targets:
- **(T-i) Lower bound.** A matching lower bound for dynamic, high-probability regret
  under drifting `(σ_t,p_t)` — formalize "worst-tail-dominates" and the heavy-budget
  threshold. Does drift in `p_t` add a cost *separate* from drift in `σ_t`?
- **(T-ii) Algorithm.** Achieve it without knowing `σ_t, p_t, P_T`. §2's cancellation
  machinery handles the unbounded/parameter-free part; the missing piece is a
  *tail-adaptive, scale-decoupled* update.

**The design constraint the theory hands us** [reasoning, matches Finding 9(e)]:
do not put the adaptivity in the clip *magnitude* (a scale-dependent `τ_t`), because
the clipped step is `∝ τ_t` and so inherits the scale drift. Put it in a
**scale-normalized step** — divide by a tracked robust scale `s_t` so the update is
*scale-invariant* (`g_t/s_t`), optionally with a **constant, scale-free** safeguard
cap. Then `σ_t`'s `6×` swing does not reach the step at all; only the *shape* of the
tail (the `p_t` piece) remains to be handled. This cleanly separates the two drifts:
`s_t` absorbs `σ_t`; a scale-free cap / the cancellation potential handles `p_t`.

**Status of the two testable next steps (both now done):**
- Heavy-budget measurement → §3 above: the dynamic wall is real (`~6.8× √T`), the
  static one is not (`0.16× √T`).
- **Scale-normalized OGD → CONFIRMED (FINDINGS Finding 10).** SN-OGD (`g_t/s_t` +
  scale-free cap) never diverges across `lr ∈ [2e-3, 2.0]` and all per-window
  restarts (100% vs clipping's 70%), and at its own lr reaches `R² = 0.24` > the
  best clipper's `0.155`. Scale-invariance removes the drift transmission exactly as
  predicted. **The remaining open piece is purely theoretical (T-ii): a proven
  high-probability dynamic-regret bound for the scale-normalized step under drifting
  `(σ_t, p_t)`.** The empirical achievability is now in hand; the matching upper-bound
  proof is the paper-worthy theorem.

---

## References (verified; ids resolve on arXiv)

- Zhang & Cutkosky. *Parameter-free Regret in High Probability with Heavy Tails.*
  arXiv:2210.14355 (NeurIPS 2022). — exploding-iterate fix, static clip `τ`.
- Zhang, Zhang, Zhou. *OCO with Heavy Tails: Old Algorithms, New Regrets.*
  arXiv:2508.07473 (ALT 2026). — bounded-domain expectation optimality; `T^{1/p}`.
- Lugosi & Mendelson. *Mean estimation and regression under heavy tails.* 2019.
- Devroye, Lerasle, Lugosi, Oliveira. *Sub-Gaussian mean estimators.* Ann. Stat. 2016.
- Bubeck, Cesa-Bianchi, Lugosi. *Bandits with heavy tail.* IEEE-IT 2013.
- Nguyen et al. *High-Probability Convergence of Clipped-SGD under Heavy Tails.*
  arXiv:2302.05437. — high-prob clipped rate under bounded `p`-th moment.
- Minimax regret under infinite variance (`p<2`): arXiv:2603.06851 (2026).
