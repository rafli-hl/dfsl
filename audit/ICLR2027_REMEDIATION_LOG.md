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

---

## Pass IV — predictability correction (2026-08-21)

Input: a verify-first challenge to Pass III's §E.13 claim that the `0.247` vs `0.285` SN-OMD
discrepancy was a tuning-grid artifact. Verifying it found a real defect in the *code*, and
measuring the defect showed it was **not** what produced the discrepancy.

### The finding

`alg:snomd` specifies a **predictable** scale: `s_t <- S.scale` (uses `g_t'` for `t'<t`), then
`ghat_t = clip(g_t/s_t, M)`, then the step, then `S.update(||g_t||)`. The `F_{t-1}`-measurability
is not decoration — Freedman (`lem:freedman`) and `ass:track` require it, and §1 sells it as what
distinguishes SN-OMD from normalized-GD's non-predictable `1/||g_t||`.

Three research-script implementations folded `||g_t||` into `s_t` **before** normalizing, making
the deployed tracker `F_t`-measurable:

| site | feeds |
|---|---|
| `research_batched_check.py::_step` | `tab:jane`, `tab:replication`, cap sweep, grid adequacy, crypto, lr-curves, `windows_tracker` |
| `research_leakage_controls.py::snomd_run_returnw` | the leakage battery |
| `research_normalize.py::ScaleNormalizedOGD` | `jane_msweep.csv`, `research_audit_checks.py` |

The split was clean and unlucky: the **library** (`dfsl.preprocessing.OnlineScaleTracker`, pinned
by `tests/test_preprocessing.py::test_step_is_predictable`) and every theory-validation script
(`research_synthetic`, `research_review2/3_checks`, `research_crypto_mechanism`,
`research_second_domain`, `make_paper_figures`, and `research_iterate_norm` via the library) were
always correct. The **research scripts behind the tables** were not. This is not a leakage bug —
predictions at round `t` are formed from `w_t` before `g_t` exists — but a theory/experiment
mismatch: the tables did not measure Algorithm 1.

An exhaustive re-sweep on `winsor` (which every winsorized EMA must reference) returns 15 sites:
3 offenders, 10 already correct, 2 intentional (both arms of the new decomposition script). An
earlier sweep on `decay * s` missed `research_normalize.py`, which writes `self.beta * self.s`.

### FIXED — the decomposition (new script)

**`scripts/research_predictability_check.py`** crosses {post-update, predictable} x the full
`research_baselines.LRS` grid on the reported window, with a *paired* circular block bootstrap on
each contrast (marginal SEs are ~.08, far too wide to resolve a ~.04 gap between two runs on the
same rows). Both published numbers reproduce to four decimals, validating the harness:

```
code path @ lr=2   +0.0001 +-0.0009  [-0.0017, +0.0018]  inconclusive
code path @ lr=1   +0.0009 +-0.0001  [+0.0007, +0.0012]  significant
grid @ predictable +0.0379 +-0.0630
TOTAL gap          +0.0378 +-0.0621
reproduction: post-update @ lr=2 = +0.2845 (Table 1 reports +0.2845)
reproduction: predictable @ lr=1 = +0.2467 (sweep reports  +0.2467)
```

**The grid explains +0.0379 of the +0.0378 total; measurability explains 0.3% of it.** §E.13's
*original* sentence was substantively right; Pass III's "correction" of it attached a real defect
to a number it does not explain. Mechanism: on capped rounds (`||g||/s > M=5`) the scale cancels
exactly, and elsewhere `s_t/s_{t-1}` lies in `[0.99, 1.07]`.

### FIXED — the correction and full regeneration

All three sites now capture the pre-update scale. Twelve artifacts regenerated. Every method that
never touches the tracker (OGD, normalized-GD, fixed-tau, AdaGrad-Norm, Cutkosky-Mehta,
block-median) came back **bit-identical including bootstrap SEs** — a validity check on each
re-run.

| artifact | outcome |
|---|---|
| `baselines_jane.csv` | SN-OMD per-row `0.2845 -> 0.2846`, per-step `0.3091 -> 0.3066` |
| `table1_errorbars.csv` | scale-adaptive per-row `0.1619 -> 0.1593`; SN-OMD agrees with baselines to 4 d.p. |
| `cap_sweep_jane.csv` | both arg-maxima hold (EMA M=2, block M=5); across-window means unchanged to 4 d.p. |
| `jane_msweep.csv` | M=5 optimum holds; finite-cap-beats-uncapped margin *widens* `+0.0069 -> +0.0103` |
| `grid_adequacy.csv` | every tuned optimum and all four boundary flags unchanged |
| `leakage_controls.csv` | every quoted value unchanged at reported precision |
| `crypto_algorithms.csv` | divergence partition `10/10 . 3/10 . 0/10` unchanged |
| `crypto_lr_sweep.csv` | two quoted lr=8 peaks moved (below) |
| `lr_curves_*.csv` | all quoted figures survive at reported precision |
| `windows_tracker.csv` | `0.14+-0.11`, `0.29`, the `0.11 -> 0.07` halving all unchanged |
| `windows_replication*.csv` | two substantive changes (below) |
| `rmsprop_adam_*.csv` | `rmsprop_adam_jane` and `schedule_control_jane` **bit-identical** |

`windows_cm.csv`, `cm_normgd_equiv.csv` and the synthetic suite need no re-run — they exercise no
tracker path.

### Manuscript edits (12 numbers + 3 corrections)

| site | old | new | source |
|---|---|---|---|
| `tab:jane` scale-adaptive per-row | `0.162+-.022` | `0.159+-.024` | `table1_errorbars.csv` |
| `tab:jane` SN-OMD per-row SE | `0.285+-.079` | `0.285+-.080` | `baselines_jane.csv` |
| `tab:jane` SN-OMD per-step | `0.309+-.056` | `0.307+-.059` | `baselines_jane.csv` |
| §4 batching sentence | `0.285 -> 0.309` | `0.285 -> 0.307` | as above |
| §4 halving sentence | `0.162 -> 0.080` | `0.159 -> 0.080` | as above |
| `app:secondmarket` uncapped peak | `1.4e17` | `5.0e17` | `crypto_lr_sweep.csv` |
| `app:secondmarket` SN-OMD peak | `6.5` | `6.6` | `crypto_lr_sweep.csv` |
| `tab:replication` uncapped div | `6/10` | `7/10` | `windows_replication_summary.csv` |
| §4 stability-partition sentence | `6/10` | `7/10` | as above |
| `tab:replication` SN-OMD per-step | `0.13+-.14` | `0.12+-.15` | as above |
| §E.10 multiple comparisons | "exactly one verdict" | "two verdicts" | `tracker_bootstrap.csv` |
| §E.10 closing | "the one borderline result" | "the two borderline results" | as above |

**The one changed conclusion.** Bonferroni at `alpha/14` (`t_9`=3.909) now flips *two* verdicts,
not one. The scale-adaptive per-step gap still flips (`+0.106`, `[+0.005,+0.208]` ->
`[-0.069,+0.281]`), and the per-step block-vs-EMA gap newly joins it: pre-fix it was `+0.0732`
with uncorrected CI `[-0.000,+0.147]` — never significant, so it had no verdict to flip; post-fix
it is `+0.0787`, `[+0.004,+0.154]`, significant uncorrected and inconclusive corrected. Verified
against the pre-fix CSV recovered from `git show HEAD:`. Neither is load-bearing — the tracker
claim the paper makes is the per-row one, where every gap survives correction unchanged (`+0.151`,
`+0.113`, `+0.085`, `+0.093`, `+0.290`, and the CM tie `+0.004 [-0.028,+0.036]`).

### FIXED — two Pass-III regressions in §E.13

| # | Finding | Change |
|---|---|---|
| 13 | §E.13's head claimed the run used the "same window, protocols, **grids** and circular block bootstrap as `tab:jane`" — false, and self-contradicted 40 lines later. `LRS_ADAPTIVE=[1e-4..1]` and the sweep's `[1e-4..3]` are neither of them `tab:jane`'s `[0.02..8]`. | Now "same window, protocols and circular block bootstrap ...; learning-rate grids as noted below". |
| 14 | The Pass-III caveat asserted the `0.247`/`0.285` gap was partly a code-path difference, without measuring it. | Now cites the measurement: grid effect `+0.038` against a total gap of `+0.038`. |

Also repaired: a non-raw Python replacement string turned `\texttt` into a literal TAB, so the new
citation rendered as `exttt{...}`. LaTeX compiled it silently — 0 errors, 0 undefined refs. Caught
on re-read, not by the build. The file now contains zero tab characters.

### Not disclosed in the paper, deliberately

The correction needs no reproducibility note: the code now implements `alg:snomd` as written, so
there is no gap between description and implementation left to declare.

**Build after all edits: 8.878pp main text (unchanged), 28pp total, 0 undefined refs, 0 overfull
>10pt, 77 tests pass.**

### Pass IV addendum --- post-pass verification sweep

Prompted by a challenge that matching a stored CSV proves internal consistency, not correctness.
Every count and interval the manuscript states from a tracker-touching artifact was re-checked
against the *regenerated* CSV, not against its predecessor.

**Divergence counts.** All 18 `x/10` sites enumerated. The corrected `7/10` reaches both places
it is stated --- `tab:replication` (`:523`) and the running prose of the ten-window paragraph in
sec:experiments (`:479`). The crypto partition's `3/10` (`:404`, `:1394`) is a different dataset
and unchanged (`crypto_algorithms.csv` bit-identical). OGD's `9/10` and the `0/10` rows are
tracker-free and bit-identical.

**The `6/10` coincidence.** `:487` and `:1586` state `6/10` for the block-median-vs-Cutkosky-Mehta
paired win count --- same digits as the old divergence count, different quantity. It is *not*
inert: the block-median arm is SN-OMD, so it routes through the corrected code. Re-checked
against the regenerated `tracker_bootstrap.csv`: `+0.00422`, `t95 [-0.01417,+0.02262]`, `6/10`
wins --- matches `$+0.004$, CI $[-0.014,+0.023]$, $6/10$` exactly. It survives because
`blockmed_perrow` (`research_baselines.py:136`) was already predictable: it captures the
*previous* block's median (`sc = blk`) before appending `||g_t||` to the buffer. Same reason every
`block - X` row with a tracker-free `X` came back bit-identical.

**Correction to the "2 intentional" label.** The Pass-IV sweep reported "2 intentional (both arms
of the new decomposition script)". That was miscounted in both directions and is restated here:

* Exactly **one** site normalizes by a post-update scale on purpose:
  `research_predictability_check.py:76`, the `else` arm of the 2x2 --- the defect under
  measurement. Its sibling at `:74` is not an exemption, it is simply correct.
* A separate family of **three** estimators is deliberately *non-causal*, which is a stronger
  violation than post-update and an entirely different thing: `crypto_mechanism.noncausal_ema`,
  `review2_checks.centered_ema`, and `residual_surrogate`'s twin. All three are forward+backward
  geometric means whose only purpose is to see the future; they are the paper's own "centered EMA
  (non-causal twin)" control row (app:causality) and are labelled as such in every docstring.

Every other winsorized-EMA site is predictable by construction, in one of two idioms: `s[i] = cur`
recorded before `cur` is advanced (`make_paper_figures._ema`, `crypto_mechanism.causal_ema`,
`review2_checks.causal_ema`, `second_domain.causal_ema`), or step-then-update in the vectorized
scripts (`research_synthetic` both branches, `research_review3_checks:107`). No site claims an
exemption from predictability while purporting to implement `alg:snomd`.

`research_rmsprop_adam.py:161` is a fourth full winsorized-EMA implementation that was already
correct at `2c817aa`; that is why `rmsprop_adam_jane.csv` and `schedule_control_jane.csv` are
bit-identical while `rmsprop_adam_stability.csv`'s `snomd_peak` moved --- the latter calls
`anchor_perrow`, which routes through the corrected `_step`.

**Stale negative controls (SHOULD-FIX item 5, now closed).** `5.6e-4` and `18\%` appear nowhere in
the document. `6.4 / 5.5\times10^{-4} / 16\%` appear in both sites that state them --- `:539`
(sec:experiments) and `:1712` (the widened-grid appendix, the site that had not been confirmed
checked). The five `6.6` hits are the unrelated two-timescale envelope constant
`W_s\approx6.6 V_\sigma^+` (`:565`, `:870`, `:1308`, `:1547`) plus the crypto peak corrected in
this pass (`:1401`). The control was never at risk regardless: `research_review3_checks.py`'s
SN-OMD branch was already predictable.

### FIXED --- one pre-existing rounding error found by the sweep

| # | Finding | Change |
|---|---|---|
| 15 | app:tracker's closing paragraph gave the block median's margin over the remaining bounded baselines as `$+0.09$ to $+0.15$`. The floor is the fixed-tau gap, `+0.08489`, which rounds to `+0.08` --- and the same subsection states it as `$+0.085$` fourteen lines earlier, so the paragraph contradicted itself. Pre-existing, not a Pass-IV regression: the fixed-tau comparison is tracker-free and bit-identical across the correction. | `$+0.08$ to $+0.15$` |

Every other figure in the Bonferroni paragraph re-derived from the regenerated CSV and confirmed:
both flipped intervals, all six surviving per-row gaps, the per-step normalized-GD/CM margin, and
the CM tie under correction.

**Build after the addendum edit: 8.878pp main text (unchanged), 28pp total, 0 undefined refs,
0 overfull >10pt.**

| 16 | app:adaptive's closing sentence gave SN-OMD's deployed-schedule score as `$0.28$` (`tab:jane`'s lr=2 number) four lines below a table of the same quantity reading `$0.247$` from the common sweep, and rmk:scope already quotes `$0.25$` from that same sweep. Three statements of one quantity, one of them from a different grid. | `$0.25$`, matching both the table above it and rmk:scope |

**Build after item 16: 8.878pp main text, 28pp total, 0 undefined refs, 0 overfull >10pt.**
