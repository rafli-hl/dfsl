# The problem: distribution-free sequential learning under heavy-tailed uncertainty

A careful, literature-grounded map of *what the problem actually is*, why it is
hard, what is already known, and where the genuinely open difficulty lies. This
is a research-scoping document, not paper prose. Written 2026-07-29; references
at the bottom are real papers (checked, not invented).

Companion to `FINDINGS.md` (our empirical results on Jane Street), which this
document explains and situates in the theory.

---

## 0. One-paragraph statement

We predict online, one round at a time, and the only thing we are willing to
assume about the noise/gradients is a **low-order moment bound** — a finite
`p`-th moment for some `p ∈ (1,2]` (finite variance is the best case, `p=2`;
`p→1` is "barely more than a mean"). No sub-Gaussianity, no boundedness, no known
noise scale, no known tail index, and — in the setting that matters for markets —
no stationary distribution. The question is: **what regret is achievable, with
what probability, by an algorithm that knows none of these constants?** The word
*distribution-free* is the crux: the guarantee must hold uniformly over the whole
class of distributions meeting the moment bound, and the algorithm may not use
the scale, the tail index, or the comparator norm as inputs.

---

## 1. Precise formulation

**Protocol (online linear/convex).** For `t = 1..T`: play `x_t ∈ 𝒳 ⊆ ℝ^d`;
observe a convex loss `ℓ_t` (for us, weighted squared error
`ω_t(⟨x_t, φ_t⟩ − y_t)²`); receive a stochastic (sub)gradient `g_t` with
`E[g_t | ℱ_{t-1}] ∈ ∂ℓ_t(x_t)` (martingale-difference noise `ε_t = g_t − ∇ℓ_t`).

**Comparator & regret.**
- *Static* regret: `R_T(u) = Σ_t ℓ_t(x_t) − Σ_t ℓ_t(u)` for a fixed `u`.
- *Dynamic* regret: `R_T(u_{1:T}) = Σ_t ℓ_t(x_t) − Σ_t ℓ_t(u_t)` for a moving
  comparator with path length `P_T = Σ_t ‖u_t − u_{t-1}‖`. This is the right
  notion for nonstationary (regime-switching) markets.

**The heavy-tail assumption (the whole game).** `E[‖ε_t‖^p | ℱ_{t-1}] ≤ σ^p`
for some `p ∈ (1,2]`. Equivalently the tail decays polynomially,
`P(‖ε_t‖ > z) ≲ (σ/z)^p`. Finite variance ⇔ `p=2`; infinite variance ⇔ `p<2`.
(Our Jane Street gradients: Hill index `α ≈ 2.43`, i.e. finite variance but
*infinite 4th moment* — see FINDINGS.md Finding 3. In the OCO language this is
`p=2` for the second-moment bound, but the *higher* moments the classical
high-probability analyses want do not exist.)

**Three axes that define the sub-problems.** Almost every result lives at one
corner of this cube; the difficulty is very different corner to corner.
1. **Domain:** bounded/compact (projection `Π_𝒳`, diameter `D` known) vs
   **unbounded** (no projection; comparator norm `‖u‖` unknown).
2. **Guarantee:** in **expectation** `E[R_T]` vs **high-probability**
   `R_T ≤ (...)·log(1/δ)` w.p. `1−δ`.
3. **Knowledge:** constants (`σ, p, G, D, ‖u‖`) **known/tunable** vs
   **unknown** (distribution-free / parameter-free / scale-free).
Add a 4th, usually ignored: **stationary vs nonstationary** (static vs dynamic
regret; `σ_t, p_t` may drift).

---

## 2. The fundamental price of heavy tails: the `T^{1/p}` rate

The achievable regret degrades smoothly with the tail:
`Regret ≍ ‖u‖ · σ · T^{1/p}` (up to logs and dimension). Sanity checks:
- `p = 2` (finite variance) → `T^{1/2} = √T`: the usual OCO rate.
- `p → 1` → `T^{1}`: **linear regret — no learning is possible.**
This exponent is not an artifact of any algorithm; it is a **lower bound** (see
Vural et al. 2022 for OCO; nonsmooth/nonconvex lower bounds in Kornowski &
Zhang 2512.23178 and the ALT-2026 paper). So the heavy tail sets a hard ceiling:
the fewer moments, the closer to un-learnable. Everything else is about *whether
a distribution-free / high-probability / nonstationary algorithm can reach this
ceiling without cheating (knowing the constants)*.

---

## 3. What is actually known (the map)

**Corner A — bounded domain, in expectation: plain OGD is already optimal, no
clipping.** Zhang, Zhang, Zhou (ALT 2026, arXiv:2508.07473) prove
`E[R_T^{OGD}] ≲ GD√T + σD·T^{1/p}` for *unmodified* projected OGD, optimal in all
parameters, **even without knowing `p`**. The mechanism: the bounded domain
forces `‖x_t − x_{t+1}‖ ≤ D`, which tames the noise term directly — no gradient
clipping needed. Their Appendix A explicitly flags that **high-probability bounds
are harder** and left largely open. *Takeaway: in expectation, on a bounded
domain, clipping buys nothing — a result that directly challenges a naive
"clipping is essential" thesis.*

**Corner B — unbounded domain, high-probability, parameter-free: the hard,
on-point corner.** Zhang & Cutkosky (arXiv:2210.14355, "Parameter-free Regret in
High Probability with Heavy Tails") give, over an **unbounded** domain and
**without knowing `‖u‖`, the scale, or `p`**, a high-probability bound
`R_T ≤ Õ(‖u‖ · T^{1/p} · log(1/δ))`. Their central technical obstacle is
*precisely our empirical failure mode*: "straightforward martingale concentration
fails due to **exponentially large iterates** produced by the algorithm." They
fix it with new regularization. *This paper is the closest existing thing to
"distribution-free sequential learning under heavy-tailed uncertainty."*

**Corner C — stochastic optimization (offline convergence), high-probability:
clipping is the tool.** For minimizing a fixed `f` from heavy-tailed gradients,
**clipped-SGD** achieves high-probability, near-time-optimal rates under only a
bounded `p`-th moment: Gorbunov et al. (NeurIPS 2020, accelerated gradient
clipping); Nguyen et al. (arXiv:2302.05437) for convex & nonconvex with minimal
assumptions; refined upper *and lower* bounds in Kornowski et al.
(arXiv:2512.23178, ICLR 2026). Quantile-clipping variants: Jia & Su
(arXiv:2309.17316). *Takeaway: clipping's proven role is **tail control /
high-probability**, not improving the mean.*

**The estimator toolbox (why "distribution-free" is even possible).** The reason
any of this works is that the empirical mean is a **bad** estimator under heavy
tails (only Chebyshev, polynomial concentration), but *robust* mean estimators
achieve sub-Gaussian deviation `σ√(log(1/δ)/n)` assuming only finite variance:
Catoni (2012, M-estimation / soft truncation); median-of-means and trimmed-mean
(Devroye–Lerasle–Lugosi–Oliveira 2016; Lugosi–Mendelson 2019 survey). Clipping is
essentially a streaming, one-coordinate robust mean of the gradient. *Our Finding
5/8: which robust estimator matters less than people think, and soft truncation
(Catoni) has a **narrower stable-step margin** than hard rejection (MoM/trimmed).*

**Bandits (for completeness).** Heavy-tailed reward bandits (Bubeck, Cesa-Bianchi,
Lugosi 2013) established the same theme in a different sequential problem: swap the
empirical mean for a robust estimator and recover near-optimal regret under only
`1+ε` moments.

---

## 4. Why the problem is genuinely hard (the obstructions)

1. **Expectation ≠ high probability.** Under heavy tails the *distribution of the
   regret* is itself heavy-tailed: the mean can be optimal while individual runs
   blow up. This is the exact reconciliation of ALT-2026 ("OGD optimal in
   expectation") with our FINDINGS ("OGD diverges on a run"). The hard object is
   the **upper tail of the regret**, and controlling it costs a `log(1/δ)` and
   real algorithmic work (clipping / robust estimation / regularization).

2. **Unbounded iterates ⇒ concentration breaks.** Without projection or a known
   `D`, a single large gradient at a large step moves the iterate a lot; the
   iterate norm can grow geometrically, and martingale concentration (Freedman)
   no longer applies because the increments are not controlled. This is *the*
   obstacle in Corner B and is exactly our divergence (`R²` → −10⁹). Projection
   or clipping are two different ways to bound the per-step effect; the theory in
   Corner A uses projection, and our experiments (no projection, fixed step) show
   what happens without either.

3. **Distribution-free ⇒ nothing to tune with.** Optimal steps/thresholds depend
   on `σ, p, G, D, ‖u‖` — none of which are known. Guessing the Lipschitz bound
   from the running max gradient couples the algorithm to its own (heavy-tailed)
   history. Parameter-free / scale-free machinery (Cutkosky, Orabona; FreeGrad)
   is required, and combining it with heavy tails and high probability is
   delicate (Corner B).

4. **Nonstationarity × heavy tails (the least-charted, and our empirical wall).**
   If `σ_t` (or `p_t`) drifts, an adaptive threshold `τ_t = c·robust_mean(recent
   ‖g‖)` **rescales with the regime**: it guards against spikes *relative to the
   current scale* but not against a regime-wide scale increase, so under a fixed
   step it diverges much like OGD (FINDINGS Finding 7). The right target is
   **dynamic/adaptive regret**, but the existing dynamic-regret machinery
   (mixability, curved losses, Sword++, fixed-share) assumes *well-behaved*
   gradients, and the heavy-tailed high-probability results are *static*. **The
   intersection — nonstationary + heavy-tailed + high-probability +
   parameter-free — appears genuinely open.**

5. **The heavy tail is emergent, not primitive (our RQ3).** In real regression
   the gradient `g = 2ω(⟨x,w⟩−y)x` is a *product*: residual (`α≈4.5`) × feature
   norm (`α≈4.1`) × weight (`α≈32`). Each factor has a finite 4th moment, yet the
   product has `α≈2.43` — heavier than any factor — because extreme features and
   extreme residuals **co-occur** (tail dependence; FINDINGS Finding 4). So the
   moment index `p` of the gradient is an interaction property of the data, can
   drift, and is not something you can read off any single quantity. This
   under-cuts the convenience of "assume `E‖g‖^p ≤ σ^p" and argues for
   *estimating* the operative tail online.

6. **Conditioning vs tails are different diseases (our RQ5).** Standardization
   fixes ill-conditioning; clipping fixes tails; neither substitutes for the
   other. A full method must address both, and on raw features clipping alone is
   useless (FINDINGS Finding 6).

---

## 5. The open problem worth targeting

> **Distribution-free, high-probability, dynamic online learning under a drifting
> heavy tail.** Design an online algorithm for unbounded domains that, knowing
> none of `σ_t, p_t, G, D`, and without a fixed learning rate, attains
> high-probability **dynamic** regret of the optimal form — roughly
> `Õ((‖u‖ + P_T)·sup_t σ_t · T^{1/p} · log(1/δ))` or a local/adaptive-regret
> analogue — while remaining **provably non-divergent across regime shifts** in
> the tail scale. Equivalently: make adaptive gradient clipping robust to
> nonstationary scale, with guarantees, rather than to spikes relative to the
> current scale.

Why this is the right target:
- **It is open.** Corner A is bounded+expectation; Corner B (Zhang–Cutkosky) is
  unbounded+high-probability+parameter-free but **static**; dynamic-regret theory
  is **light-tailed**. Nobody has the four-way intersection.
- **It is exactly what the data forces.** Our regime-shift fragility (FINDINGS 7)
  is a concrete, reproducible instance of the failure this problem asks to fix.
- **It is honest about clipping.** It reframes clipping not as "the thing that
  beats OGD" (ALT-2026 shows that framing is false in expectation on bounded
  domains) but as *tail/stability control for the unbounded, high-probability,
  nonstationary regime* — where it genuinely earns its keep.

**Empirically grounded (FINDINGS Finding 9).** On a 60-day span the gradient
*scale* drifts 5.9× (up to 3.15× overnight) **and the tail index itself drifts**,
`α_t ∈ [1.17, 3.31]`, dipping **below 2** (intermittent infinite variance) on
several days. So the problem is *doubly* nonstationary: not a fixed `p` with a
drifting `σ`, but a drifting `(σ_t, p_t)` with `p_t` occasionally `< 2`. And we
showed a scalar rolling-scale threshold provably cannot win: track the scale
(small `W`) and the step inherits the 6× swing (diverges); smooth it (large `W`)
and it lags the regime onset (over-clips / under-protects). No window escapes both.

Sub-questions / first steps:
- (a) A clean **lower bound** for dynamic high-probability regret under a finite
  `p`-th moment: how much must `P_T` and `sup_t σ_t` cost? Does drift in `p_t`
  (especially `p_t < 2` spells) add a separate, possibly prohibitive price?
- (b) A **scale-tracking threshold** with a guarantee: an estimator of the *upper*
  tail scale that provably reacts to regime shifts fast enough to prevent
  divergence yet slowly enough not to clip signal — our measurements show a fixed
  window cannot, so this likely needs a data-driven / two-timescale window.
- (c) **Restart / strongly-adaptive** wrappers (à la Cutkosky's strongly-adaptive
  parameter-free OL) analyzed under heavy tails — do they give divergence-free
  dynamic regret without knowing `P_T`?
- (d) Whether **projection to an adaptive, data-driven radius** (a distribution-
  free surrogate for the bounded-domain assumption) recovers Corner-A stability
  in the unbounded case.
- (e) **Normalize instead of clip.** Decouple the step from the tail scale:
  divide by a tracked robust scale (`g_t/s_t`, scale-invariant step) rather than
  clip to `τ_t`. Our Finding 9 shows clipping-to-`τ` transmits the scale drift
  into the step; normalization would not. What are its heavy-tailed,
  high-probability, nonstationary guarantees? (cf. normalized/sign SGD under
  heavy tails, arXiv:2601.20399.)

---

## 6. How our Jane Street findings line up with the theory

| Empirical finding (FINDINGS.md) | Theoretical meaning |
|---|---|
| OGD diverges only at large fixed lr / unprojected | Corner-A stability needs projection or a tuned step; we removed both. |
| OGD fine at small lr, in expectation | Consistent with ALT-2026 optimal-in-expectation OGD. |
| Gradient Hill `α≈2.43` | `p=2` (finite variance) but no finite 4th moment — the hard end of `p∈(1,2]`. |
| Heavy tail = feature×residual interaction | `p` is emergent/data-dependent, not primitive (Obstruction 5). |
| Clipping wins on continuous stream, ~15× larger stable step | Clipping = high-probability/stability control in the unbounded regime (Corner B/C). |
| Fixed-lr clipping diverges on regime shift | Nonstationary scale defeats scale-relative thresholds (Obstruction 4 = the open problem). |
| MoM/trimmed > Catoni at high step | Hard rejection has a wider stable-step margin than soft truncation. |

---

## 7. References (verified)

- Zhang, Zhang, Zhou. *Online Convex Optimization with Heavy Tails: Old
  Algorithms, New Regrets, and Applications.* arXiv:2508.07473 (ALT 2026).
- Zhang, Cutkosky. *Parameter-free Regret in High Probability with Heavy Tails.*
  arXiv:2210.14355 (NeurIPS 2022).
- Nguyen, Ene, Nguyen. *High Probability Convergence of Clipped-SGD Under
  Heavy-tailed Noise.* arXiv:2302.05437.
- Gorbunov, Danilova, Gasnikov. *Stochastic Optimization with Heavy-Tailed Noise
  via Accelerated Gradient Clipping.* NeurIPS 2020.
- Kornowski et al. *Clipped Gradient Methods for Nonsmooth Convex Optimization
  under Heavy-Tailed Noise: A Refined Analysis (with lower bounds).*
  arXiv:2512.23178 (ICLR 2026).
- Jia, Su. *Robust Stochastic Optimization via Gradient Quantile Clipping.*
  arXiv:2309.17316.
- Catoni. *Challenging the empirical mean and empirical variance: a deviation
  study.* Ann. IHP 2012.
- Devroye, Lerasle, Lugosi, Oliveira. *Sub-Gaussian mean estimators.* Ann. Stat.
  2016. / Lugosi, Mendelson. *Mean estimation and regression under heavy tails.*
  2019 (survey).
- Bubeck, Cesa-Bianchi, Lugosi. *Bandits with heavy tail.* IEEE Trans. IT 2013.
- Cutkosky. *Parameter-free, Dynamic, and Strongly-Adaptive Online Learning.*
  ICML 2020. / Vural, Yoon, Cutkosky et al. — heavy-tailed OCO lower bounds.

(URLs are in the session log; arXiv ids above resolve directly.)
