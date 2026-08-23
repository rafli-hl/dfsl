# Claim ledger

**This file is new as of 2026-08-23.** The Phase-1 `claim_ledger.md` referenced by the
Phase-2 brief is absent from this repository and `git log --all` shows it was never
committed here. This ledger therefore starts from the claims a Phase-2 session has
actually examined, not from an inherited list. Claims not listed here have not been
audited by this process and carry whatever status the manuscript gives them.

Status values: `SUPPORTED` (measured, survives the check applied) ·
`CONFOUNDED` (the evidence offered cannot answer the question) ·
`OPEN` (asked, not answered) · `UNTOUCHED` (not examined this phase).

---

## C-1 — "A constant scale beats a predictable tracked scale on the ten-window benchmark"

**Status: CONFOUNDED → REVERSED at matched budget.**

Evidence as published: `windows_replication.csv`, per-row held-out means, fixed-tau clip
0.2020 vs SN-OMD (M=5) 0.1237, fixed-tau winning 9/9 held-out windows.

What was found (direction C10/Q6, `results/research/c10/r_c10_summary.md`): the two arms
were tuned at unequal budget — 70 joint `(lr x tau)` configurations for the baseline
against 10 `lr` configurations for the proposal with the cap pinned at `M=5`. At matched
budget (70 joint `(lr x M)` configurations) the ordering **reverses**: SN-OMD 0.2270 vs
fixed-tau 0.2020, held-out `delta = -0.0250` [−0.0338, −0.0162], SN-OMD winning 9/9
held-out and 10/10 overall. `fraction_closed = 1.32` against a registered survival
threshold of 0.50.

Scope: per-row primary. Per-step agrees in direction (`-0.0134`, 0/9) but its matched arm
selected at two grid edges, so its magnitude is not resolved.

**Consequence:** the published comparison cannot support a claim about constant vs tracked
scale processes in either direction. It must be re-run at matched budget before any
manuscript use.

## C-2 — "SN-OMD is fragile across windows (held-out sd 0.103, min −0.107)"

**Status: CONFOUNDED.** The fragility is a property of the published configuration
(`M=5, lr=2`), not of the tracked scale. At matched budget the same method has held-out
sd 0.0403 and min +0.1693; the window-7 collapse disappears entirely.

## C-3 — "The ten-window mean is a held-out measurement"

**Status: CONFOUNDED.** The published protocol tunes on window 1 and reports the mean over
all ten windows *including* window 1. Per-row, the published SN-OMD arm wins the selection
window (0.2846) and loses all nine held-out windows — a selection-overfitting signature
the pooled mean conceals. Held-out and in-sample figures should be reported separately.

## C-4 — "Stored research artifacts reproduce"

**Status: SUPPORTED.** The preregistered reproduction gate re-derived the fixed-tau and
published-SN-OMD held-out means from source and matched `windows_replication.csv` to
`diff = 0.0000` in both protocols (tolerance 0.005). The stored numbers are sound; the
defect found is in comparison design, not arithmetic.

## C-5 — "Why does a constant scale beat a tracked one?" (the C10/Q6 question as posed)

**Status: DISSOLVED — false premise.** At matched budget it does not. Replaced by C-6.

## C-6 — Mechanism: why does `M=2` at `lr=3` transfer across windows when `M=5` at `lr=2` does not?

**Status: still OPEN.** Probed in direction C10M
(`results/research/c10m/r_c10m_summary.md`); both registered hypotheses came back
**inconclusive** and neither mechanism was established.

- **Clip-binding frequency is not supported as the mechanism.** The two anchors differ
  ten-fold in binding rate (published 0.0122, matched 0.1220), but across a 30-point
  dyadic grid binding rate is almost a deterministic function of `M` alone and has the
  *weakest* rank association with held-out performance of the four registered candidates
  (`rho2 = 0.007`). Caveat recorded against my own design: `rho2` is a monotone statistic
  and the surface is single-peaked, so the H3 test was under-powered by construction.
- **Product sufficiency (`P = lr·M`) is inconclusive for performance**: `eta2_P = 0.578`
  per-row against a registered survival threshold of 0.80.

## C-7 — `P = lr·M` locates a stability transition band

**Status: PARTIALLY SUPPORTED — the threshold is located; sufficiency is not established,
and the original "perfect separation" wording is retired.**

Originally logged from C10M as perfect separation (20/20 stable at `P ≤ 8`, 10/10 divergent
at `P ≥ 16`). Tested in direction C10S (`results/research/c10s/r_c10s_summary.md`) on new
configurations, along six rays holding `M` fixed with `lr = P/M`.

**Registered verdict: H4 INCONCLUSIVE.** Per-row spread across rays = 1.682 against a
survival band of ≤1.25; per-step = 2.378, which would be falsified. Both guards clean:
0 censored, 0 non-monotone, 6/6 rays usable, brackets resolved to a factor of 1.044.

**Located:** `P*_hat = 11.49` per-row (geometric mean), per-ray range [8.67, 14.58], at
150 000 rows per window. Per-step `P*_hat = 9.80`, range [7.29, 17.34].

**What is genuinely supported.** `P` compresses a **32×** variation in `M` and a **23.6×**
variation in the critical rate `lr*` into a **1.68×** variation in `P*`. The design made
that hard: at fixed `P` the `M=0.5` ray clips ~57% of steps and `M=16` clips ~0.1%. `P` is
far better than either factor alone, but misses the registered sufficiency tolerance.

**What is retired.** The boundary is a **transition band, not a cliff**. The any-window
criterion marks where the first of ten windows fails; the median-window threshold sits
1.3–1.7× higher. C10M sampled `P` at factor-2 spacing — the width of the band — so it could
not resolve the gradient and separation looked perfect. Post hoc.

**Dominant threat.** The any-window criterion is an extreme-value statistic (minimum over
ten windows), so each `P*` is set by the single most fragile window. This is the likeliest
explanation of the per-row non-monotonicity (`P*` peaks at `M=4`, falls at `M=8, 16`), which
no mechanism predicts. The 1.044 bracket is search resolution, **not** a confidence
interval.

**Trap recorded** (carried from C10M and still standing). The registered secondary statistic
`eta2_P` over all 30 C10M configurations with R² floored at −1 is 0.9873 and would read as
overwhelming support for product sufficiency. It is an artifact of `P` predicting
divergence: floored divergent configurations align by `P` by construction.

## C-8 — Does the *realized* maximum step explain C-7's residual?

**Status: OPEN — post-hoc proposal, untested.**

`P = lr·M` is the *nominal* maximum step, attained only when the clip binds, which for large
`M` is rare. The realized maximum `lr·min(r_max, M)` would predict exactly the per-step
pattern of `P*` rising with `M` (7.29 → 17.34 across `M = 0.5 → 16`). Generated from the
C10S residual, so it must be tested on data that did not produce it.

---

## Untouched this phase

`UNTOUCHED` — not examined, status unchanged:

- The stability/divergence partition (OGD 10/10, uncapped endpoint 7/10, bounded
  scale-free 0/10). Those arms were not re-run.
- All theory: `thm:stability`, `thm:regret`, `thm:regretbody`, the Freedman
  measurability argument, `ass:track`.
- The Pass-IV predictable-vs-post-update decomposition (grid accounts for +0.0379 of the
  +0.0378 gap; measurability 0.3%).
- RMSProp/Adam bounded-step finding (`app:adaptive`).
- The tracker bootstrap and Bonferroni analysis (`app:tracker`).
- Every crypto, synthetic, MNIST and GARCH-surrogate result.
