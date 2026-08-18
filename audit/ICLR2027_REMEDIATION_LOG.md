# ICLR 2027 — remediation log (Pass III fix pass)

Running record of what each audit pass changed in `paper/iclr2027/iclr2027.tex` and the
supplement. Separates **FIXED** (applied and verified) from **FLAGGED** (needs an author
decision, or needs compute/data not run). Companion to the read-only ICML-round
`AUDIT_REPORT.md`; that file is not updated.

---

## Pass III fix pass (2026-08-18)

Input: a re-audit of the post-remediation manuscript. It scored the paper 5.5/10 (up from
5.0 — framing fixes landed; the novelty ceiling is unchanged and is not editable), and
found three regressions that the *previous* remediation pass had itself introduced.

### FIXED — MUST-FIX regressions

| # | Finding | Change | Verified by |
|---|---|---|---|
| 1 | **Abstract asserted an assumption-free regret bound.** "…at the per-regime rate `T^{1/p}` **under only this finite moment**" is false: Theorem D.2 also needs Assumption D.1 (predictable scale bracketing, discharged only heuristically by Prop. E.5) and Assumption 2.1's deterministic a.s. bounds on `S_1`, `sup σ_t`. | Now "…under a finite `p`-th moment **and a predictable scale-tracking condition**." | reads against `thm:regret`'s own hypotheses |
| 2 | **Theorem 3.2 used "per regime" before the term was defined** anywhere in the main text (formal definition is §E.13's drift model). | Statement now reads "…on any horizon over which the tracker's upward variation is `O(1)` — a *regime*, formalized in §E.13". | `\cref{app:bracket}` resolves; 0 undefined refs |
| 3 | **`tab:replication`'s caption contradicted §E.12.** Caption claimed "all optima interior"; `grid_adequacy.csv` has 4 `status=boundary` rows and §E.12's own caption concedes them. | Caption now claims "all *accuracy-relevant* optima interior", pointing at §E.12 for the flags. | `grid_adequacy.csv` re-read: per-row OGD `lr*=0.001@floor`, per-row CM `tau*=600@ceiling`, per-step CM `beta*=0.0@floor`, per-step SN-OMD M-sweep `M*=2@floor` |

### FIXED — SHOULD/OPTIONAL

| # | Finding | Change | Verified by |
|---|---|---|---|
| 5 | Per-step SN-OMD `M`-sweep optimum sits at the sweep floor (`M=2`, range `[2,20]`) and was undisclosed — §E.12's notes covered only the OGD/CM flags. | Added to `tab:grid`'s notes, stating plainly that the per-step cap below 2 is untested and that the "interior cap optimum" claim is a per-row one. | `grid_adequacy.csv` |
| 6 | Four supplement docstrings cited theorem numbers that no longer exist. | `research_synthetic.py` "Theorem 3.3"→"Theorem 3.2 (D.2 in the appendix)"; `research_review2_checks.py` "Theorem 3.3"→"Theorem D.2"; `research_review3_checks.py` "Theorem 3.3 / Remark 3.5"→"Theorem D.2 / the tracker-design remark"; `research_baselines.py` "Theorem 3.1"→"Proposition 3.1". | `grep` returns no stale numbers |
| 7 | Theorem 3.2's title said "informal", inviting dismissal. | Retitled "Dynamic regret; restated from §D, where Theorem D.2 gives the unsimplified constants and §E the proof." | rebuild |
| 9 | Negative control's SN-OMD optimum sat at its grid floor (`η=0.05`), leaving a grid-edge objection open. | Grid widened down to `η=0.01`; optimum **stays at `η=0.05`, now strictly interior**. New §E.12 paragraph records this. | `research_review3_checks.py` re-run |
| 10 | `check_b` advanced a single RNG across all ten tuning runs, so the arms were unpaired *and* the reported numbers depended on grid order. | Each `(kind, η)` now re-seeds, so the comparison is paired and order-independent. | re-run |
| 11 | Legibility of the two body figures after the `0.9\textwidth` resize. | **No change needed** — page rendered at 130 dpi and inspected: legend, tick labels, and the "bounded (<10)" annotation are all clearly readable. Effective 389/351 dpi. | `pdftoppm` render |

**Reported numbers that moved (item 9/10).** Making the control paired and widening the grid
changed the negative-control figures: steady excess loss **6.4 vs 5.5 ×10⁻⁴, a 16% gap**
(was 6.6 vs 5.6 ×10⁻⁴, 18%). Direction, magnitude, and conclusion are unchanged — SN-OMD is
worse once the scale is constant — but §4's sentence was updated to match the code, since a
number that shifts when a grid point is added is not a number worth defending.

### FIXED — item 4 (RMSProp / Adam head-to-head)

New script **`scripts/research_rmsprop_adam.py`**: RMSProp (`ρ=0.9`) and Adam
(`β=(0.9,0.999)`) on the reported Jane window, same harness, protocols, grid discipline, and
circular block bootstrap as `research_baselines.py`. Outputs
`results/research/rmsprop_adam_jane.csv`, `rmsprop_adam_stability.csv`,
`schedule_control_jane.csv`.

**The result contradicted §5 and the claim has been corrected.** Two findings:

**(a) §5's divergence argument was false — FIXED.** The paper claimed that because numerator and
denominator share the round, "a single extreme gradient still yields an unbounded step — the
divergence of §4". The opposite is true, and for the reason SN-OMD itself is stable: sharing the
round *cancels*. With `v_t = ρ v_{t-1} + (1-ρ) g_t² ≥ (1-ρ) g_t²`, the ratio
`|g_{t,i}|/(√v_{t,i}+ε) ≤ (1-ρ)^{-1/2}` pointwise, so the per-coordinate move is bounded by
`η(1-ρ)^{-1/2}` for any gradient; likewise for Adam whenever `β₁² ≤ β₂`, as at the defaults.
Measured per-row peak rolling loss (`rmsprop_adam_stability.csv`) confirms it — RMSProp/Adam grow
like `η²` and stay finite over a 10,000× rate range where OGD reaches `10³⁰⁰`:

| η | 1e-3 | 1e-2 | 0.03 | 0.1 | 0.3 | 1 |
|---|---|---|---|---|---|---|
| RMSProp | 4.9 | 3.0 | 5.8 | 43 | 363 | 4.0e3 |
| Adam | 3.8 | 2.4 | 8.2 | 84 | 787 | 9.2e3 |
| SN-OMD (M=5) | 5.0 | 4.9 | 5.0 | 5.0 | 4.8 | 4.3 |
| plain OGD | 4.9 | 21 | 3.4e10 | 3.6e76 | 7.5e297 | >1e300 |

§5's paragraph was rewritten to say this, the Limitations clause "RMSProp/Adam are argued to
diverge but not run head-to-head" was deleted, and a new appendix subsection **§E.13
(`app:adaptive`)** carries the derivation and both tables. The cap still buys something the EMA
denominator does not — SN-OMD's peak is *flat* in η where theirs grows quadratically.

**(b) Their apparent accuracy edge is the step schedule, not the preconditioner — RESOLVED.** In
their standard deployed form (constant η) Adam scores **0.509 ± .013** and RMSProp
**0.444 ± .017** per-row, far above every method in `tab:jane` (best 0.329). That looked like a
submission-threatening omission. It is not: every method in the paper uses the anytime `η/√t`.
Crossing schedule × method (`schedule_control_jane.csv`) isolates it —

| schedule | SN-OMD (M=5) | Adam | RMSProp | AdaGrad-Norm |
|---|---|---|---|---|
| constant η | **0.521 ± .019** | 0.509 ± .013 | 0.444 ± .017 | 0.329 ± .029 (grid ceiling) |
| η/√t (deployed) | 0.247 ± .026 | **0.261 ± .069** | 0.098 ± .031 | −0.00 (double-decayed) |

— within each schedule SN-OMD and Adam sit inside each other's error bars and SN-OMD leads
RMSProp. The fourfold gap is the schedule. Recorded in §E.13.

### FLAGGED — needs an author decision

| # | Finding | Why it is the author's call |
|---|---|---|
| A | **The deployed `η/√t` schedule costs the paper ~0.27 R² on window 1** (SN-OMD 0.52 at constant η vs 0.25 at `η/√t` on the common sweep). Theorem D.2 is *proven for constant η* (Remark D.5); it is Proposition 3.1's `O(√t)` envelope that wants the anytime schedule. So the paper deploys the schedule its *weaker* result needs while its main theorem assumes the other one. | **PARTLY CLOSED** — switching schedules is still out of scope (would mean re-running `tab:jane`, `tab:replication`, the ten-window tracker/CM runs, the cap sweeps and the crypto algorithms). But the *cost* is now priced in **Remark D.5**, which is page-exempt: "Empirically the choice is not free: … 0.25 against 0.52 for a tuned constant η. We deploy it for horizon-free stability … not because it is more accurate." |
| B | Whether to add RMSProp/Adam rows to `tab:replication` (ten frozen windows) rather than the single-window §E.13 table. | **CLOSED — leave as is.** Single-window is enough to support the divergence claim §5 actually makes, and there is no page budget for a ten-window redo of two methods outside the main comparison. §E.13 states the single-window scope explicitly. |

### FIXED — follow-up consistency check

| # | Finding | Change |
|---|---|---|
| 12 | §E.13's schedule table reports SN-OMD at `η/√t` as **0.247**, while `tab:jane` reports **0.285** for the same method, protocol and window — a reviewer diffing the two would read it as a contradiction. Cause: the schedule sweep deliberately uses *one* grid common to all four methods (`η ∈ {1e-4 … 3}`) so the comparison is like-for-like, and that grid omits `tab:jane`'s `lr=2`. | §E.13 now states this outright: the 0.247 is that sweep's grid, "not a competing estimate of the same quantity". |

### NOT DONE — needs compute or data

| # | Item | Why not |
|---|---|---|
| 8 | Wall-clock runtime figure for the Reproducibility Statement | needs a timed full-suite run over the 12 GB Jane parquet |
| — | Positive non-finance demonstration (MUST-FIX #3 of the previous pass) | needs new data; Limitations now states the scope limit explicitly instead |
