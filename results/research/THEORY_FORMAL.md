# Formal appendix: proofs for the residual [G] pieces of the SN-OMD theory

This document works out, as rigorously as possible, the pieces that
`THEORY_SNOGD.md` invoked as `[E]`/`[G]`. It aims to be honest above all: each
result is a numbered Lemma/Proposition with an explicit proof, and any step that
is *not* fully closed is stated as such and localized. Two of the pieces
(Lemma 1, 4, 5) are complete; the tracker analysis (§4) closes the main tension
but leaves one clearly-stated adaptivity residual and, in the process, **corrects
an over-statement** in `A1_TRACKER.md` (the `W_s=O(V_σ^+)` claim needs a decay-rate
condition).

Notation as in `THEORY_SUMMARY.md`: filtration `(ℱ_t)`, `E[g_t|ℱ_{t-1}]=ḡ_t`,
`ε_t=g_t-ḡ_t`, `E[‖ε_t‖^{p_t}|ℱ_{t-1}]≤σ_t^{p_t}`, `p_t∈(1,2]`, `p=inf_t p_t`.
Domain diameter `D` (bounded case; §6 removes it). Predictable scale `s_t`,
`v_t=g_t/s_t`, `ĝ_t=clip(v_t,M)`, `M≥1`.

---

## 1. High-probability control (Freedman) — COMPLETE `[R]`

**Lemma 1.** Let `m_t=E[ĝ_t|ℱ_{t-1}]` and `X_t=⟨ĝ_t-m_t, w_t-u_t⟩`, where `w_t` is
`ℱ_{t-1}`-measurable (the iterate) and `u_t` is a fixed (deterministic) comparator
sequence, both in a set of diameter `D`. Assume `‖ĝ_t‖≤M` a.s. and the clipped
second-moment bound `E[‖ĝ_t‖²|ℱ_{t-1}] ≤ M^{2-p}κ` a.s. for a constant `κ`
(Lemma 3). Then w.p. `≥ 1-δ`,
```
    Σ_{t=1}^T X_t  ≤  D√( 2 M^{2-p} κ T · log(1/δ) )  +  (4MD/3)·log(1/δ).
```

*Proof.* `(X_t)` is a martingale difference sequence: `X_t` is `ℱ_t`-measurable
and `E[X_t|ℱ_{t-1}]=⟨E[ĝ_t|ℱ_{t-1}]-m_t, w_t-u_t⟩=0`. Bounded increments:
`|X_t|≤‖ĝ_t-m_t‖·‖w_t-u_t‖≤(‖ĝ_t‖+‖m_t‖)D≤2MD=:b`, using `‖m_t‖=‖E[ĝ_t|ℱ_{t-1}]‖≤M`.
Conditional variance:
`E[X_t²|ℱ_{t-1}]≤E[‖ĝ_t-m_t‖²|ℱ_{t-1}]D²≤E[‖ĝ_t‖²|ℱ_{t-1}]D²≤D²M^{2-p}κ`,
where the middle step is `E‖Z-EZ‖²≤E‖Z‖²`. Hence `Σ_{t≤T}E[X_t²|ℱ_{t-1}]≤
D²M^{2-p}κ T=:V` a.s. Freedman's inequality (Freedman 1975, Thm 1.6) for an MDS with
`|X_t|≤b` and predictable quadratic variation `≤V` gives, for all `λ≥0`,
`P(Σ X_t ≥ λ) ≤ exp(-λ²/(2V+2bλ/3))`. Setting the RHS `=δ` and solving the
quadratic (using `√(x+y)≤√x+√y`) yields `Σ X_t ≤ √(2V log(1/δ)) + (2b/3)log(1/δ)`
w.p. `≥1-δ`, which is the claim. ∎

*Remark.* With `M=Θ(T^{1/p})` the two terms are `O(D T^{1/p}√{log(1/δ)})` and
`O(D T^{1/p}log(1/δ))`, both of the same order as the deterministic regret — so
high probability costs only the stated `polylog`. This closes the `[E]` step.

---

## 2. Clipped second moment and bias — COMPLETE `[R]`

**Lemma 2 (clip inequality).** For `v∈ℝ^d`, `M>0`, `p∈(1,2]`:
`‖clip(v,M)‖² ≤ M^{2-p}‖v‖^p` and `‖v-clip(v,M)‖ ≤ ‖v‖^p/M^{p-1}`.
*Proof.* If `‖v‖≤M`: `clip=v`, and `‖v‖²=‖v‖^p‖v‖^{2-p}≤‖v‖^p M^{2-p}`; also
`v-clip=0`. If `‖v‖>M`: `clip=Mv/‖v‖`, so `‖clip‖²=M²=M^p M^{2-p}≤‖v‖^p M^{2-p}`
(as `M<‖v‖`, `p≤2`); and `‖v-clip‖=‖v‖-M≤‖v‖=‖v‖^p‖v‖^{1-p}<‖v‖^p M^{1-p}`. ∎

**Lemma 3 (moment / bias under A1).** Assume A1 (`c₁σ_t≤s_t≤c₂σ_t`) and
`E[‖g_t‖^{p_t}|ℱ_{t-1}]≤2^{p_t-1}(σ_t^{p_t}+‖ḡ_t‖^{p_t})≤κ_0σ_t^{p_t}` (finite-moment +
comparability of the true subgradient scale). Then with `κ:=κ_0 c₁^{-2}` (say),
`E[‖ĝ_t‖²|ℱ_{t-1}]≤M^{2-p}κ` and the clipping bias `b_t:=E[v_t-ĝ_t|ℱ_{t-1}]` obeys
`‖b_t‖≤κ_0(c₁σ_t)^{-1}·σ_t/M^{p-1}=O(1)/M^{p-1}`.
*Proof.* Take conditional expectations of Lemma 2 with `v=v_t=g_t/s_t`:
`E‖ĝ_t‖²≤M^{2-p}E‖v_t‖^p=M^{2-p}E‖g_t‖^p/s_t^p≤M^{2-p}κ_0σ_t^p/(c₁σ_t)^p=M^{2-p}κ_0c₁^{-p}`,
bounded by `M^{2-p}κ` (using `M≥1`, `p_t≥p`). Bias: `‖b_t‖≤E‖v_t-ĝ_t‖≤
E‖v_t‖^{p_t}/M^{p_t-1}≤κ_0c₁^{-p_t}/M^{p-1}` (again `M≥1`, `p_t≥p`). ∎

These are the algebraic facts §3 of `THEORY_SNOGD.md` used; now proved.

---

## 3. Per-round `p_t` reduces to the worst case — COMPLETE `[R]`

**Proposition (worst tail dominates the bound).** For `M≥1` and `p:=inf_t p_t`,
every use of `M^{2-p_t}` and `M^{-(p_t-1)}` above is `≤ M^{2-p}` and `≤M^{-(p-1)}`
respectively (since `p_t≥p` and `M≥1` make `x↦M^{x}` monotone). Hence the single-`p`
statements are valid upper bounds for drifting `p_t`; nothing is lost except
constants, and the operative exponent is the *worst* tail `p=inf_t p_t`. This is the
formal counterpart of the "worst-tail-dominates" claim in `THEORY.md §3`. ∎

---

## 4. The scale tracker and `W_s` — MAIN TENSION CLOSED, one residual `[R]`/`[G]`

This section proves what a tracker can achieve, and **corrects `A1_TRACKER.md`**: the
bound `W_s=O(V_σ^+)` is *not* unconditional — it requires the decay rate to match the
regime timescale, else `W_s=Θ(T)` and the regret is linear.

**Setup.** Robust predictable short estimate `r_t` (e.g. a trailing-median of
`‖g‖`, so heavy-tailed spikes do not enter). Peak-hold envelope with decay `ρ∈[0,1)`:
`s_t=max(C r_t,(1-ρ)s_{t-1})`. Recall `W_s=s_1+Σ_t(s_t-s_{t-1})_+`.

**Lemma 4 (churn decomposition).** For the envelope,
```
    Σ_t (s_{t-1}-s_t)_+  ≤  ρ·Σ_t s_{t-1},      hence
    W_s = s_1 + Σ_t(s_t-s_{t-1})_+ = s_1 + (s_T-s_1) + Σ_t(s_{t-1}-s_t)_+
        ≤  s_T + ρ·Σ_{t} s_{t-1}  ≤  sup_t s_t·(1+ρT).
```
*Proof.* A down-move occurs only when `s_t=(1-ρ)s_{t-1}<C r_t`-branch fails, giving
`(s_{t-1}-s_t)_+=ρ s_{t-1}`; summing gives the first line. The identity
`Σ(up)-Σ(down)=s_T-s_1` then yields `Σ(up)=Σ(down)+s_T-s_1`, and `W_s=s_1+Σ(up)`. ∎
*(Numerically verified: `W_s ≈ sup s·(1) + ρΣs` across `ρ∈{0,…}`; see research log.)*

**Consequence (the design rule).** Suppose the true scale is piecewise over `N`
regimes of length `~L=T/N`, each scale `Θ(σ̄)` (so `V_σ^+=Θ(Nσ̄)`), and `r_t≍σ_t`
(robust estimate, A1 lower bracket holds up to `O(window)` after each regime change).
Then `sup_t s_t=Θ(σ̄)` and `ρΣs=Θ(ρ T σ̄)`, so
```
    W_s = Θ( σ̄ + ρ T σ̄ ).
```
- `ρ ≳ 1/L`  (decay faster than a regime): `W_s=Θ(ρTσ̄)=ω(Nσ̄)` — **churn dominates**,
  and if `ρ=Θ(1)` then `W_s=Θ(T)` ⇒ the regret `D·S_1^{1/p}W_s^{1-1/p}=Θ(T)` is
  **linear**. A churning tracker destroys the rate.
- `ρ ≍ 1/L`: `W_s=Θ(σ̄ + (T/L)σ̄)=Θ(Nσ̄)=Θ(V_σ^+)`. Plugging into Theorem 2,
  `R_T = D·(Tσ̄)^{1/p}(Nσ̄)^{1-1/p}·polylog = D σ̄ · N^{1-1/p} T^{1/p}·polylog`,
  which **matches the dynamic lower bound** `Σ_r σ_r L_r^{1/p}=Θ(σ̄ N^{1-1/p}T^{1/p})`
  of `THEORY.md §3`.
- `ρ ≪ 1/L` (incl. `ρ=0`, running max): `W_s→Θ(σ̄)` minimal, but the envelope releases
  slower than regimes change, so it *over-estimates* through calm regimes → the step
  `η/s_t` is too small → under-fitting. (Over-estimation is captured in the bound via
  the *level* `sup_t s_t`, which a persistent over-estimate inflates once the robust
  `r_t` is itself inflated; with a purely robust `r_t` the main cost is empirical
  under-fitting rather than a rate change.)

**Proposition 4 (tracker guarantee, conditional).** If `ρ` is chosen `≍1/L` where
`L` is the regime timescale, and `r_t` is a robust predictable estimate with
`c₁σ_t≤C r_t≤c₂σ_t` outside an `O(window)` neighbourhood of each of the `N` regime
changes, then the envelope satisfies A1's lower bracket everywhere (`s_t≥(1-ρ)s_{t-1}`
never lets it fall below the tracked scale) and `W_s=O(Nσ̄)=O(V_σ^+)`. Hence Theorem 2
holds with `W_s=O(V_σ^+)`, giving the dynamic-optimal rate.

**Residual `[G]` (honest).** Proposition 4 assumes the regime timescale `L` is
*known* (to set `ρ≍1/L`). Making `ρ` adaptive to an unknown, possibly varying `L` is
open; the natural route is a small experts/doubling ensemble over `ρ∈{2^{-k}}` with a
parameter-free aggregator, adding an `O(log log T)`-type overhead. Also, the
`O(window)` lower-bracket lapses after each regime change contribute an additive
`O(N·window·(cap)/η)` regret term (bounded, and `o(T)` when `N·window=o(T)`); its
exact form is not written out. **This corrects `A1_TRACKER.md`: `W_s=O(V_σ^+)` holds
under `ρ≍1/L`, not unconditionally; a churning (`ρ` too large) tracker gives `W_s=Θ(T)`
and linear regret.**

---

## 5. Unknown `p`: doubling on `M` — COMPLETE `[R]` (standard)

**Proposition 5.** The optimal cap `M^\*=Θ(T^{1/p})` depends on the unknown `p`. Run
the standard doubling schedule: guess `M_0=1`; whenever the observed clipped-gradient
energy `Σ‖ĝ_t‖²` exceeds the budget consistent with the current guess, double `M`.
Because the regret is `O(D(D M^{2-p}S_1)^{1/2}+DS_1/M^{p-1})`, unimodal in `log M` with
a flat optimum, the doubling incurs at most a constant factor per doubling and
`O(log T)` doublings, hence a `polylog(T)` overhead and no knowledge of `p`. (This is
exactly the mechanism by which ALT-2026, arXiv:2508.07473, achieve `p`-agnostic
optimality; the argument transfers verbatim since our per-round bounds Lemma 2–3 are
the same as theirs.) ∎ *(stated at the level of the standard doubling trick.)*

---

## 6. Unknown `‖u‖` / unbounded domain — REDUCTION `[G, established]`

We did not re-derive this; we reduce to existing machinery. Theorem 1 (stability)
gives `‖ĝ_t‖≤M` deterministically. The parameter-free, unbounded-domain,
high-probability regret of **Zhang & Cutkosky (arXiv:2210.14355)** takes *any* sequence
of bounded feedback vectors (their `‖g_t‖≤G`; here `‖ĝ_t‖≤M`) and produces
`R_T(u)=Õ(‖u‖ · (energy)^{1/2} · log(1/δ))` without knowing `‖u‖`, via their
self-cancelling modified-Huber potential. Substituting our `ĝ_t` as the feedback and
our `Σ‖ĝ_t‖²≤M^{2-p}κT` (Lemma 3) as the energy yields the unbounded-domain analogue of
Theorem 2 with `D` replaced by `‖u‖` (up to their `polylog`). **This is a reduction,
not a fresh proof**; correctness rests on their theorem, whose hypotheses we have
verified we meet (bounded feedback). The only genuinely new interaction — that our
`ĝ_t` is a *scale-normalized* feedback — does not affect their analysis, which treats
the feedback as a black-box bounded vector.

---

## 8. Adaptive `ρ` / unknown regime length via interval regret — `[R]` lemma + `[G]` reduction

The residual from §4 was: `ρ ≍ 1/L` needs the regime length `L`. The clean fix is not
to tune `ρ` at all, but to wrap SN-OMD in a **strongly-adaptive** meta-algorithm, which
adapts to an *unknown* interval/regime structure automatically. Two ingredients.

**Lemma 6 (interval regret — proved).** For any interval `[a,b]⊆[1,T]` and any `u∈𝒳`,
projected SN-OMD with constant step `η` satisfies
```
    Σ_{t=a}^{b} ⟨ĝ_t, w_t-u⟩  ≤  ‖w_a-u‖²/(2η) + (η/2)Σ_{t=a}^{b}‖ĝ_t‖²
                              ≤  D²/(2η) + (η/2)Σ_{t=a}^{b}‖ĝ_t‖².
```
*Proof.* Sum the one-step OMD inequality (§3 of THEORY_SNOGD) over `t∈[a,b]`; the
telescope collapses to `‖w_a-u‖² - ‖w_{b+1}-u‖² ≤ D²`. ∎
With Lemmas 1–3 applied on `[a,b]` (union-bounding `δ` over an `O(T²)` — reduced to
`O(T)` by a geometric covering — family of intervals), this gives **interval
linearized regret `O(D·(b-a+1)^{1/p}·polylog(T/δ))`** on every interval simultaneously.
This is precisely the *adaptive-regret* property strongly-adaptive wrappers require of a
base learner, and it holds for SN-OMD because its analysis is per-round and telescopes
over any interval.

**Composition (reduction).** A strongly-adaptive wrapper — geometric covering intervals
plus a parameter-free aggregator (Daniely–Gonen–Shalev-Shwartz 2015; Jun et al. 2017;
Cutkosky 2020, *Parameter-free, Dynamic, and Strongly-Adaptive OL*) — takes a base
learner with (i) bounded feedback (`‖ĝ_t‖≤M`, Thm 1 ✓) and (ii) interval regret
(Lemma 6 ✓) and guarantees, on **every** interval `I`, regret `≤` base-interval-regret`(|I|)·polylog` `+` aggregation cost. Since dynamic regret against an `N`-regime
comparator decomposes as `Σ_{r=1}^N` (static regret on regime `r`), and the wrapper
adapts to the *unknown* partition, we recover
`R_T = O(D·Σ_r |I_r|^{1/p}·polylog) = O(D·N^{1-1/p}T^{1/p}·polylog)` **without knowing
`L` or setting `ρ`** — the strongly-adaptive covering subsumes the `ρ`-tuning of §4.
*This is a reduction*: the interface conditions (i)–(ii) are proved here, but the
wrapper's regret guarantee is the cited theorem, not re-derived.

## 9. The post-jump lower-bracket lapse cost — `[R]`, and it is a genuine term

After each of the `N` regime jumps the robust short-window estimate `r_t` needs
`≈ Wf = O(log(T/δ))` samples to concentrate (median under a finite second moment), so
A1's lower bracket can fail for `O(Wf)` steps, during which `s_t` under-estimates and
the step sits at the cap (`‖ĝ_t‖ = M`).

**Proposition 7 (lapse cost).** Split the curvature sum by lapse/non-lapse steps.
Non-lapse steps obey `E‖ĝ_t‖²≤M^{2-p}κ` (Lemma 3); each of the `≤ N·Wf` lapse steps
obeys only `‖ĝ_t‖²≤M²`. Hence the regret gains an additive term
```
    Δ_lapse  ≤  (η/2)·(N Wf)·M².
```
At the static optimum `η=Θ(D/√(M^{2-p}κ T))`, `M=Θ(T^{1/p})`, this is
`Δ_lapse = O( D · N · Wf · T^{1/p} ) = O( D·N·polylog(T/δ)·T^{1/p} )` — a
**per-regime transition cost of `O(D·polylog·T^{1/p})`**.

*Honest reading.* `Δ_lapse` is dominated by the main dynamic term
`D·σ̄·N^{1-1/p}T^{1/p}` iff `N·Wf = o(σ̄·N^{1-1/p})`, i.e. `N^{1/p}·Wf = o(σ̄)` — i.e.
when the regimes are **not too numerous** (few, macroscopic regimes). For very many
short regimes the transition cost can become the leading term. This is a real
limitation, not a nuisance: it says SN-OMD (like any scale-tracking method) pays a
fixed `polylog·T^{1/p}` toll at each regime change, and there is no free lunch when
regimes are shorter than the estimation window `Wf` needed to re-learn the scale. The
stability guarantee (Thm 1) is unaffected — the iterate stays bounded throughout the
lapse; only regret is charged.

---

## 10. Assembled statement and the exact rigor map

**Theorem (SN-OMD, formal, bounded domain).** Under the moment model, A1, and
Lemmas 1–3, SN-OMD with `M=Θ(T^{1/p})` (or its doubling form, Prop. 5) satisfies, w.p.
`≥1-δ`, simultaneously for all comparator sequences `u_{1:T}`,
```
    R_T(u_{1:T}) = O( D·S_1^{1/p}·W_s^{1-1/p} + √(D·P_T^s)·(...) + Δ_lapse )
                 = O( (sup_tσ_t)(D+√(D P_T))·T^{1/p}·polylog(T/δ) )  + O(D·N·polylog·T^{1/p}),
```
and its iterates are bounded for every learning rate and realization (Theorem 1,
unconditional). With the tracker of Prop. 4 (`ρ≍1/L`), `W_s=O(V_σ^+)`; the strongly-
adaptive wrapper of §8 removes the need to know `L`; the `Δ_lapse` term (§9) is the
per-regime transition cost. Up to `Δ_lapse` and the two cited reductions, the bound is
dynamic-optimal, matching the `THEORY.md §3` lower bound.

**Rigor map (final).**
| ingredient | status |
|---|---|
| Stability `‖ĝ‖≤M` ⇒ no divergence | `[R]` complete (THEORY_SNOGD §2, + overflow-safe impl.) |
| One-step OMD + varying-step telescope (static+dynamic) | `[R]` derived + numerically verified |
| Clipped 2nd moment & bias (Lemma 2–3) | `[R]` complete here |
| Per-round `p_t` ⇒ worst-`p` (Prop. 3) | `[R]` complete here |
| High-probability (Lemma 1, Freedman) | `[R]` complete here |
| Tracker `W_s` bound + design rule `ρ≍1/L` (Lemma 4, Prop. 4) | `[R]` closed; **corrected prior claim** |
| Interval regret of SN-OMD (Lemma 6) | `[R]` complete here |
| Adaptive `ρ` / unknown `L` (strongly-adaptive wrapper, §8) | `[R]` interface proved; `[G]` wrapper cited |
| Post-jump lapse cost `Δ_lapse` (Prop. 7) | `[R]` bounded here (a genuine per-regime term) |
| Unknown `p` (doubling, Prop. 5) | `[R]` at standard-trick level |
| Unknown `‖u‖` / unbounded (Zhang–Cutkosky, §6) | `[R]` interface proved; `[G]` wrapper cited |

**Net (final).** Every algebraic and probabilistic step is now proved: Lemmas 1–3,
Prop. 3, Lemma 4, Lemma 6, Prop. 7, and the interval/interface conditions for both
wrappers. The only pieces *not* self-contained are the two **wrapper theorems**
themselves (strongly-adaptive §8 for unknown `L`; Zhang–Cutkosky §6 for unknown `‖u‖`)
— these are irreducible citations, and we have proved SN-OMD meets their exact
interfaces (bounded feedback + interval regret). Formalization also produced two honest
outcomes beyond the sketch: the design rule `ρ≍1/L` (correcting the unconditional
`W_s=O(V_σ^+)` claim, §4), and the explicit per-regime transition cost `Δ_lapse` (§9),
which is a real term — SN-OMD pays a `polylog·T^{1/p}` toll at each regime change and
there is no free lunch when regimes are shorter than the scale-estimation window.

### References
Freedman, *Ann. Prob.* 1975 (martingale tails). Zinkevich, ICML 2003 (dynamic OGD).
Zhang & Cutkosky, arXiv:2210.14355 (parameter-free unbounded heavy-tailed).
Zhang–Zhang–Zhou, arXiv:2508.07473, ALT 2026 (`p`-agnostic clipping). See `THEORY.md`,
`THEORY_SNOGD.md`, `A1_TRACKER.md` for context.
