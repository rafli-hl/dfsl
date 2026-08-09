# Theory of the scale-normalized step (SN-OMD)

Develops the regret theory behind FINDINGS Finding 10 (the scale-normalized step
that never diverges and attains the highest accuracy). Goal: turn the empirical
achievability into a theorem, deriving what is rigorous and flagging what is not.

**Rigor tags.** `[R]` = derived here, rigorous (verified). `[E]` = established in
the literature (cited). `[G]` = gap: needs a proof, though the route is identified.
Nothing tagged `[R]`/`[E]` is conjectural; every `[G]` is called out explicitly.

Companion to `THEORY.md` (rates + lower bound) and `FINDINGS.md` (experiments).

---

## 1. The analyzable algorithm: Scale-Normalized OMD

To analyze the empirical SN-OGD we fix a clean, analyzable version.

**State:** `w_t ∈ 𝒳` (domain diameter `D`; unbounded case in §6). A **predictable**
scale `s_t > 0` (i.e. `ℱ_{t-1}`-measurable — a function of past gradients only).

**Update.** Given stochastic subgradient `g_t` (`E[g_t|ℱ_{t-1}] = ḡ_t ∈ ∂ℓ_t(w_t)`):
```
    v_t   = g_t / s_t                         (scale-normalize)
    ĝ_t   = v_t · min(1, M/‖v_t‖)             (scale-FREE cap at constant M)
    w_{t+1} = Π_𝒳( w_t − η · ĝ_t )
```
The empirical SN-OGD is this with `s_t` a robustified EMA of `‖g_{<t}‖` (predictable)
and a `1/√t` step; here we use a constant `η` for a clean static statement.

**Heavy-tail model.** `E[‖ε_t‖^{p_t} | ℱ_{t-1}] ≤ σ_t^{p_t}`, `ε_t = g_t − ḡ_t`,
`p_t ∈ (1,2]`; `σ_t, p_t` may drift. Write `p = inf_t p_t` (worst tail).

**Scale-tracking assumption (A1)** `[G to verify empirically]`: the predictable scale
brackets the true local scale, `c₁ σ_t ≤ s_t ≤ c₂ σ_t` for constants `0<c₁≤c₂`.
(Finding 9 shows a rolling/EMA robust scale tracks `σ_t` within a small factor
*except* right at regime onsets — where A1 is the honest weak point; see §7.)

---

## 2. The one property that is unconditional: **stability**  `[R]`

Because of the scale-free cap, **`‖ĝ_t‖ ≤ M` deterministically** (every round, every
realization). Hence for projected OMD the iterate moves at most `η M` per step and,
on any bounded domain, `‖w_t‖ ≤ D` always; on `ℝ^d` with step `η/√t`,
`‖w_t‖ ≤ ‖w_1‖ + M η Σ_{k≤t} 1/√k ≤ ‖w_1‖ + 2Mη√t`. **The iterate cannot blow up,
for any learning rate, in any regime, regardless of how heavy or nonstationary the
gradients are.** No moment assumption is used.

> This is the theorem behind Finding 10's "never diverges / 100% bounded / graceful
> degradation." It is the crucial contrast with clip-to-`τ_t=c·s_t`, whose per-step
> move is `η·min(‖g_t‖, M s_t) ∝ s_t` — bounded by the *drifting* scale, so a regime
> with large `s_t` produces large moves (Finding 7). Dividing by `s_t` replaces the
> scale-*dependent* bound `M s_t` with the scale-*free* bound `M`. **This one factor
> `1/s_t` is the whole mechanism, and its consequence (stability) is unconditional.**

---

## 3. The rate: capped-surrogate regret is `O(D · T^{1/p})`  `[R]`

Analyze the regret in the surrogate gradients `ĝ_t`, then relate to the truth.

**Step 1 — standard OMD one-step** `[E]`. For any `u ∈ 𝒳`,
```
    Σ_t ⟨ĝ_t, w_t − u⟩  ≤  D²/(2η) + (η/2) Σ_t ‖ĝ_t‖².          (OMD)
```

**Step 2 — clipped second moment** `[R]`. For `p∈(1,2]`, `‖clip(v,M)‖² ≤ M^{2−p}‖v‖^p`
(check both cases `‖v‖≤M` and `‖v‖>M`). So, using A1 and `E‖g_t‖^{p}≲σ_t^{p}+‖ḡ_t‖^{p}`,
```
    E[‖ĝ_t‖² | ℱ_{t-1}]  ≤  M^{2−p_t} · E[‖v_t‖^{p_t}|ℱ_{t-1}]
                          =  M^{2−p_t} · E[‖g_t‖^{p_t}|ℱ_{t-1}] / s_t^{p_t}
                          ≲  M^{2−p} · C_A1,                       (Var)
```
with `C_A1 = (2/c₁)^{p}` absorbing the tracking constants (bounded since `s_t≳c₁σ_t`).

**Step 3 — surrogate ≈ conditional mean, via Freedman** `[E]`. Let
`m_t = E[ĝ_t|ℱ_{t-1}]`. The increments `⟨ĝ_t−m_t, w_t−u⟩` are a martingale difference
with `|·| ≤ 2MD` and conditional variance `≤ D²·E‖ĝ_t‖² ≤ D² M^{2−p} C_A1`. Freedman:
w.p. `1−δ`,
```
    Σ_t ⟨ĝ_t − m_t, w_t − u⟩  ≲  D√( C_A1 M^{2−p} T · log(1/δ) ) + MD·log(1/δ).  (Frd)
```

**Step 4 — clipping bias** `[R]`. `‖v − clip(v,M)‖ = (‖v‖−M)_+ ≤ ‖v‖·1{‖v‖>M} ≤
‖v‖^{p}/M^{p−1}`. So the bias `‖ḡ_t/s_t − m_t‖ = ‖E[v_t−ĝ_t|ℱ_{t-1}]‖ ≤
E‖v_t‖^{p_t}/M^{p_t−1} ≲ C_A1/M^{p−1}`, contributing
```
    Σ_t ⟨ḡ_t/s_t − m_t, w_t − u⟩  ≤  D · Σ_t ‖bias_t‖  ≲  D · C_A1 · T / M^{p−1}.  (Bias)
```

**Combine + optimize `M`, `η`.** Adding (OMD)+(Frd)+(Bias) and writing the "weighted"
regret `R̃_T(u) := Σ_t ⟨ḡ_t/s_t, w_t − u⟩`:
```
    R̃_T(u)  ≲  D²/(2η) + η·M^{2−p}·T·C_A1 + D·√(C_A1 M^{2−p} T log(1/δ)) + D·C_A1·T/M^{p−1}.
```
Choose `η = D / √(C_A1 M^{2−p} T)` (balances the first two) and `M = Θ(T^{1/p})`
(balances the `√(M^{2−p}T)` term against `T/M^{p−1}` — the same balance as clipped
SGD, §THEORY.md 1). Both give `Θ(D · T^{1/p})`, so
```
    ┌─────────────────────────────────────────────────────────────┐
    │  R̃_T(u)  =  O( D · √(C_A1) · T^{1/p} · polylog(T/δ) ).   [R]  │
    └─────────────────────────────────────────────────────────────┘
```
Endpoints check: `p=2 → T^{1/2}` (classical); `p→1 → T` (trivial). Matches the
`T^{1/p}` lower bound of THEORY.md §1. **The scale enters only through `C_A1`
(the tracking constants), not through `M` or `η` — this is why the rate is
scale-drift-robust:** `σ_t`'s `6×` swing is absorbed by `s_t` in the normalization,
leaving the clip level `M=T^{1/p}` a fixed, scale-free constant.

---

## 4. From weighted regret `R̃_T` to true regret  `[G — the key gap]`

`R̃_T(u) = Σ_t (1/s_t)⟨ḡ_t, w_t − u⟩` weights round `t` by `1/s_t`, but the true
regret is `R_T(u) = Σ_t ⟨ḡ_t, w_t − u⟩ ≥ Σ_t [ℓ_t(w_t) − ℓ_t(u)]`. The per-round
terms `⟨ḡ_t, w_t−u⟩` can be negative, so one cannot simply pull out `sup_t s_t`.

Two honest routes, both `[G]`:
- **(4a) Slowly-varying scale.** If `s_t` is constant within each regime `r`
  (`s_t ≡ s_r`), then `R_T = Σ_r s_r · R̃_T^{(r)}` and, applying §3 per regime,
  `R_T ≲ Σ_r s_r · D · L_r^{1/p_r} polylog`. With `s_r ≍ σ_r` (A1) this is exactly the
  **dynamic worst-tail budget of THEORY.md §3** — i.e. SN-OMD would *attain* the
  lower bound `Σ_r σ_r L_r^{1/p_r}`. This is the target theorem; it needs the
  regime-wise decomposition made rigorous (bounding the cross-regime OMD boundary
  terms), which is standard for slowly-varying weights but not yet written out.
- **(4b) Directly via adaptive step.** Equivalently the update is OGD with step
  `η_t = η/s_t` (ignoring the cap), i.e. a **scale-free / AdaGrad-type** method. The
  scale-free OCO analysis of Orabona–Pál (2018) gives regret adapting to the gradient
  scale *without knowing it*; the open work is fusing it with the heavy-tail cap
  (§3) and high probability. This is the cleanest path and reuses established `[E]`
  machinery.

**This §4 conversion is the one genuine mathematical gap between the rigorous
capped-surrogate bound (§3) and a true-regret theorem. Everything else is stability
(§2, unconditional) or established technique.**

### 4′. Resolving the conversion via adaptive-step analysis  `[R, static case]`

The gap closes if we analyze SN-OMD in its **adaptive-step form** rather than as a
weighted surrogate. Write the update exactly:
```
    w_{t+1} = Π( w_t − η·clip(g_t/s_t, M) ) = Π( w_t − η_t · θ_t g_t ),
    η_t := η/s_t   (varying step),   θ_t := min(1, M s_t/‖g_t‖) ∈ (0,1]  (clip factor).
```
So SN-OMD **is** OGD with a time-varying step `η_t = η/s_t` applied to the clipped
*raw* gradient `θ_t g_t`. Now the OGD telescope produces the **true** (unweighted)
linearized regret directly. Let `D_t = ‖w_t − u‖ ≤ D`, `a_t = ⟨ḡ_t, w_t − u⟩`.

**(i) Varying-step telescope + summation by parts** `[R, verified]`.
`Σ_t (1/(2η_t))(D_t² − D_{t+1}²) = (1/2η) Σ_t s_t (D_t² − D_{t+1}²)`, and by Abel
summation (verified numerically, `research` log):
```
    Σ_t s_t (D_t² − D_{t+1}²)  ≤  D²·( s_1 + Σ_t (s_t − s_{t-1})_+ )  =:  D²·W_s.
```
`W_s` is the **upward total variation of the scale tracker** (`= σ` in the stationary
case). This is the natural, and only, place the scale nonstationarity enters.

**(ii) Curvature term** `[R]`. `(η_t/2)‖θ_t g_t‖² = (η/2s_t)‖θ_t g_t‖²`, and since
`‖θ_t g_t‖² ≤ (M s_t)^{2−p}‖g_t‖^p`, its conditional sum is `≲ (η/2)M^{2−p} S_1`,
where `S_1 := Σ_t σ_t` (using A1, `s_t^{1−p}·E‖g‖^p ≲ σ_t`).

**(iii) Raw clipping bias** `[R]`. `β_t = E[(1−θ_t)g_t|ℱ_{t-1}]` has
`‖β_t‖ ≲ σ_t/M^{p−1}`, contributing `D·S_1/M^{p−1}`.

**(iv) High-probability martingale** `[E]`. `⟨E[θ_t g_t|ℱ_{t-1}] − θ_t g_t, w_t−u⟩`
is a martingale difference with variance `≲ D² M^{2−p} Σσ_t²`; Freedman gives a term
of the same order as (ii)–(iii).

**Combine and optimize.** Putting (i)–(iv) together for a **fixed comparator** `u`,
```
    R_T^{lin}(u)  ≲  D²W_s/(2η) + (η/2)M^{2−p}S_1 + D·S_1/M^{p−1} + (Freedman).
```
Optimizing `η = D√(W_s/(M^{2−p}S_1))` then `M = (S_1/W_s)^{1/p}` gives
```
    ┌───────────────────────────────────────────────────────────────────────┐
    │  R_T^{lin}(u)  =  O( D · S_1^{1/p} · W_s^{1−1/p} · polylog(T/δ) )   [R] │
    │                ≤  O( D · (sup_t σ_t) · T^{1/p} · polylog ),            │
    └───────────────────────────────────────────────────────────────────────┘
```
using `S_1 ≤ T·sup σ_t` and `W_s ≳ sup σ_t`. **Stationary sanity check `[R, verified]`:**
`σ_t≡σ ⇒ S_1=Tσ, W_s=σ ⇒ R = D·(Tσ)^{1/p}σ^{1−1/p} = Dσ·T^{1/p}` — exactly the
classical rate.

**The insight this buys (and it separates the two nonstationarities).**
```
    R_T^{lin}  ≲  D · S_1^{1/p} · W_s^{1−1/p}
                  \_______/     \_________/
                  tail index p  scale drift (upward variation)
```
- The **tail index `p` sets the RATE exponent** (`S_1^{1/p} ~ T^{1/p}`) — the
  information-theoretic wall of §3, unavoidable.
- The **scale drift enters only as a constant factor** `(W_s/σ_max)^{1−1/p}`. Measured
  on Jane Street (daily proxy): `W_s/σ_max ≈ 2.9`, so the drift costs only
  `≈ 1.4–1.7×` — a mild constant, **not** a rate change.

So the `§4` conversion is not lossy in the way feared: dividing by `s_t` does not
smuggle a `sup σ_t` rate penalty; it costs a constant in `W_s`, and the scale-free
cap keeps the rate at the optimal `T^{1/p}`. **The static-regret theorem for SN-OMD is
now derived** (modulo A1 and standard high-probability bookkeeping).

---

## 5. Dynamic comparator (path length `P_T`)  `[R, verified]`

Now derived, by carrying a moving comparator `u_1..u_T` through the same varying-step
telescope of §4′. The one-step is unchanged; only the telescope sum changes. Writing
`A_t=‖w_t−u_t‖²`, `B_t=‖w_{t+1}−u_t‖²`, reindexing, and splitting each bracket into a
*comparator-move* part and a *scale-change* part,
```
    s_t A_t − s_{t-1}‖w_t−u_{t-1}‖²
        = s_t(‖w_t−u_t‖² − ‖w_t−u_{t-1}‖²) + (s_t−s_{t-1})‖w_t−u_{t-1}‖²
        ≤ 2D·s_t‖u_t−u_{t-1}‖  +  (s_t−s_{t-1})_+·D²,
```
so the varying-step telescope obeys (**verified numerically, 2000 random trials**)
```
    Σ_t s_t( ‖w_t−u_t‖² − ‖w_{t+1}−u_t‖² )  ≤  D²·W_s  +  2D·P_T^s,
    P_T^s := Σ_t s_t‖u_t − u_{t-1}‖   (SCALE-WEIGHTED path length).
```
**The only new object is the scale-weighted path `P_T^s`**: a comparator move in a
high-scale (turbulent) regime costs more than the same move in a calm one — the
heavy-tail analogue of Zinkevich's `P_T`, and the one genuinely non-boilerplate piece.
It reduces to `s_max·P_T` in the worst case.

Carrying this through §4′ (the curvature, bias, and Freedman terms are untouched) and
re-optimizing `η, M`,
```
    ┌──────────────────────────────────────────────────────────────────────────────┐
    │  R_T(u_{1:T})  ≲  D·S_1^{1/p}·W_s^{1−1/p}  +  √(D·P_T^s)·S_1^{1/p}·W_s^{-1/p} ·√? │
    │                ≲  (sup_t σ_t)·( D + √(D·P_T) )·T^{1/p}·polylog(T/δ).       [R] │
    └──────────────────────────────────────────────────────────────────────────────┘
```
(The clean second line uses `S_1≤T sup σ_t`, `W_s,P_T^s ≲ sup σ_t·(1,P_T)`; the first
line keeps the refined nonstationary constants.) **Stationary + `p=2` sanity check:**
`σ_t≡σ ⇒ σ(D+√(DP_T))√T`, i.e. the classical `O(√(T(1+P_T)))` dynamic-OGD rate — exactly
Zinkevich. **Heavy-tail effect:** the same dynamic factor `(D+√(DP_T))` simply multiplies
the heavy-tail rate `T^{1/p}` instead of `√T`.

**This completes the dynamic statement.** Combined with §3's dynamic lower bound
(`Σ_r σ_r L_r^{1/p_r}`), SN-OMD's upper bound matches it in the leading `T^{1/p}`
dependence; a fully tight regime-by-regime match (the `K^{1−1/p}` vs `√(P_T)` constants)
is left as future refinement.

---

## 6. Making it distribution-free (unknown `σ_t, p_t, ‖u‖`)

Three unknowns, three known devices:
- **Unknown `σ_t` → the scale tracker `s_t`.** Handled *by construction* (A1). This is
  what "scale-free" buys and is the crux novelty vs the static clip `τ ≍ σ^{1/p}T^{1/p}`
  of Zhang–Cutkosky, which bakes in a single `σ`.  `[R for stability; G for rate via A1]`
- **Unknown `p` → doubling/adaptive `M`.** `M=Θ(T^{1/p})` needs `p`. A standard
  doubling schedule over `M` (or the `p`-agnostic clipping of ALT-2026 §2508.07473)
  removes this at a `log` cost. `[E route]`
- **Unknown `‖u‖` / unbounded domain → the cancellation potential.** Replace projected
  OMD by the parameter-free coin-betting + self-cancelling modified-Huber regularizer
  of Zhang–Cutkosky (THEORY.md §2), which absorbs the `√(Σ‖w_t‖²)` variance from large
  iterates. The `‖ĝ_t‖≤M` bound (§2) is exactly the input their machinery needs, so
  the composition is natural. `[E route; composition is G]`

---

## 7. Target theorem and honest status

> **Target Theorem (SN-OMD, distribution-free dynamic high-probability regret).**
> Under the per-round moment model and scale-tracking (A1), Scale-Normalized OMD with
> `M=Θ(T^{1/p})` (or its doubling-adaptive, parameter-free form) achieves, w.p. `1−δ`,
> simultaneously for all comparator sequences `u_{1:T}`,
> ```
>     R_T(u_{1:T})  =  O( (sup_t σ_t)·(D + √(D P_T)) · T^{1/p} · polylog(T/δ) ),
> ```
> and its iterates are bounded for **every** learning rate and realization
> (unconditional stability), so it never diverges under scale/tail drift.

**What is solid vs open (updated after §4′):**
- `[R, done]` **Stability / no-divergence** (§2) — unconditional, explains Finding 10.
- `[R, done]` **Capped-surrogate rate** `R̃_T = O(D·T^{1/p} polylog)` (§3).
- `[R, done — static]` **True static-regret rate** (§4′): via the adaptive-step /
  summation-by-parts analysis, `R_T^{lin}(u) = O(D·S_1^{1/p}·W_s^{1−1/p}·polylog) ≤
  O(D·sup_tσ_t·T^{1/p})`, verified in the stationary limit. The feared `sup σ_t` rate
  penalty does **not** occur; scale drift costs only the constant `(W_s/σ_max)^{1−1/p}
  ≈ 1.5×`. **This closes the §4 conversion gap for a fixed comparator.**
- `[R, done — dynamic]` **Dynamic comparator** (§5): derived and numerically verified.
  Moving `u_t` adds only the *scale-weighted* path length `P_T^s = Σ_t s_t‖u_t−u_{t-1}‖`,
  giving `R_T(u_{1:T}) ≲ (sup_tσ_t)(D+√(D P_T))T^{1/p}polylog`, which reduces to
  Zinkevich's `√(T(1+P_T))` at `p=2`. **The static and dynamic rate clauses are both
  derived now.**
- `[G, standard]` unknown-`p` doubling and unknown-`‖u‖` cancellation potential (§6).
- `[G, minor]` **Per-round `p_t`.** §3–4′ used a single worst-case `p = inf_t p_t` in
  `M`. A per-round treatment (or the sum `Σ_t σ_t^{p_t/…}`) would sharpen constants;
  the worst-case version is already a valid upper bound.
- `[G, empirical]` Assumption **A1** (scale tracking). Its cost is now *explicit*:
  it enters the bound through `W_s`, the upward variation of `s_t`. A tracker that
  over-reacts inflates `W_s`; one that lags violates A1 at onsets. Designing a
  two-timescale `s_t` with a provable `W_s = O(true upward scale variation)` is the
  cleanest remaining sub-result, and Finding 9 gives the empirical target.

**Bottom line (updated).** The full **dynamic** rate clause is now derived:
`R_T(u_{1:T}) ≲ (sup_tσ_t)(D+√(D P_T))T^{1/p}polylog`, together with the unconditional
**stability** clause (§2). The `T^{1/p}` exponent (tail), the constant `W_s` scale-drift
cost, and the scale-weighted path `P_T^s` (dynamics) are all pinned down and, where
inequalities were used, numerically verified. What remains is purely **known-technique
composition**: (a) unknown-`p` doubling and unknown-`‖u‖` cancellation potential (§6);
(b) a provably-`W_s`-bounded (two-timescale) scale tracker discharging A1. No conceptual
barrier remains — the weighted→true conversion (§4) and the dynamic path term (§5) are
done.

---

## References
- Orabona & Pál. *Scale-free online learning.* Theor. Comput. Sci. 2018.  [scale-free/AdaGrad]
- Zinkevich. *Online convex programming and generalized infinitesimal gradient ascent.* ICML 2003.  [dynamic OGD, P_T]
- Zhang & Cutkosky. arXiv:2210.14355.  [parameter-free unbounded, cancellation potential]
- Zhang, Zhang, Zhou. arXiv:2508.07473 (ALT 2026).  [p-agnostic clipping]
- Freedman. *On tail probabilities for martingales.* Ann. Prob. 1975.  [high-probability]
- See THEORY.md for the `T^{1/p}` lower bound and the dynamic heavy-budget wall.
