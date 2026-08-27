# ICLR 2027 — SN-OMD submission status

Progress tracker for the SN-OMD paper targeting **ICLR 2027**. Detail on individual
fixes lives in [`ICLR2027_REMEDIATION_LOG.md`](ICLR2027_REMEDIATION_LOG.md); this file
is the top-level view: where the paper stands, what is settled, what is still open.

Last verified: **2026-08-26**, commit `a637d38` on `research/d1c-propf1-propagation` — three commits ahead of `master` and **not pushed**, by instruction. Phase-2 reached `master` via PRs [#8](https://github.com/rafli-hl/dfsl/pull/8)–[#11](https://github.com/rafli-hl/dfsl/pull/11).

---

## At a glance

| | |
|---|---|
| Branches | **Two: `master` and `research/d1c-propf1-propagation`** (local only, 3 commits, unpushed — D1C's registration ended "commit, then stop", so merging is the author's call; open item 8). `research/c10-q6` landed via [PR #8](https://github.com/rafli-hl/dfsl/pull/8) (106 files, +15,981/−526) plus three tracker follow-ups ([#9](https://github.com/rafli-hl/dfsl/pull/9)–[#11](https://github.com/rafli-hl/dfsl/pull/11)), then was deleted local and remote once every commit was contained in `master`. `paper-submission` deleted too (stale, remote gone, 0 unique commits). Merged rather than squashed: the preregistration trail is the point. |
| Pass V commits | `202d983`..`c32db71` — paper-claim guard, `references.bib` deletion, OMD/OGD naming, supplement exclusions, `out/` untrack |
| Phase-2 research | `142a075`..`a506251` — eight preregistered directions, C10/Q6 through C10C3. See **Phase 2** below |
| Phase-3 research | `72efa43`..`a637d38` — the revision-assessment actions (C13) and two propagations (D1B, D1C). See **Phase 3** below. C13 and D1B are in `master`; D1C is not |
| `master` | Carries Pass V, **all Phase-2 research**, the publication pass, the appendix QA, the closed open items — landed by [PR #8](https://github.com/rafli-hl/dfsl/pull/8) on 2026-08-25 — and since then C13 (`72efa43`) and D1B (`e59a2fa`..`5e6c383`), pushed directly. `master` head is `5e6c383` |
| Tags | Two, both annotated and pushed. `iclr2027-submission` → `c32db71` marks the **submitted** state (84 tests, 28pp, 246-file supplement) and is deliberately **not** moved — moving it would destroy the record of what was actually submitted. `iclr2027-phase2` → `a0f1516` marks the state after Phase-2, the publication pass and the closed open items |
| Canonical source | `paper/iclr2027/iclr2027.tex` (2068 lines) |
| Main text | **8.942pp** of a 9pp limit, ~0.06pp (3 lines) of margin. Trajectory: 8.885 pre-adoption → 9.007 (matched-budget table adopted) → 8.615 (appendix relocation) → 9.007 (`fig:problem` promoted) → 8.502 (`fig:main` demoted) → 8.720 (publication pass §4–19, §21–23) → 8.871 (§8–10) → 8.907 (the Limitations schedule sentence, open item 3) → 8.907 (C13 — the inverted tracker sentence is no longer than what it replaced) → **8.942** (D1B's five "left open" → "closed" sites and the Limitations concession). D1C moved it **not at all**: all three of its claim-site revisions were written to be no longer than the text they replaced |
| Total | **31pp** (statements, references, appendix do not count against the 9pp limit). 29 → 30pp at D1B's new appendix subsection, 30 → 31pp at D1C's paragraph inside it |
| Build | 31pp, exit 0. **0 undefined refs, 0 overfull**, 0 float-specifier warnings, 0 stray tabs. 5 underfull boxes: four vbox (badness 4036, 6893, **10000**, 1895) and the badness-1342 line in the dynamic-regret proof where a long unbreakable math atom ends the line. **One badness-10000 page is back, on p18** — appendix-only, and new since D1C; see open item 10. Also 3 pre-existing `pdfTeX warning (ext4): destination with the same identifier` — measured, not assumed, by building `master`'s tex in a scratch tree and diffing the logs |
| Tests | **115 passed** (106 + 5 data-free Jane-path guards + 2 SE-prose guards + 2 of C13's 3 new matched-bootstrap `PAPER_CLAIMS` guards; the third re-pointed an existing guard rather than adding a case) |
| Anon supplement | Builds clean with **0 identity tokens**; 336 files at the 2026-08-25 rebuild. Prior-venue material excluded, pinned by `tests/test_anon_exclusions.py` |

`paper/icml2026/` is a **frozen ICML snapshot** (moved there from flat `paper/*` on
2026-08-24). It is not back-synced, and it is excluded from the anonymized supplement.

---

## The claim structure

What the paper argues, and where each piece is measured:

| Claim | Evidence | Artifact |
|---|---|---|
| Gradient heavy tails are a *predictable-scale artifact*, not intrinsic | pooled vs. normalized separation on Jane; interaction effect heavier than either factor alone | `fig:problem` |
| Normalize by a predictable scale, then cap → bounded iterates | `thm:stability` (Prop. 3.1), measured √t envelope | `app:iternorm` |
| Dynamic regret under a drifting scale, high probability | `thm:regret` (Thm. D.2), restated as `thm:regretbody` | proofs, App. D |
| The cap `M` interpolates normalized-GD ↔ scale-adaptive OGD | M-sweep, optimum at `M=5` | `jane_msweep.csv` — the single-`lr` sweep still stands as a *frontier* claim; `tab:replication` now tunes `(lr, M)` jointly and selects `M=2` (per-row EMA), `M=10` (per-row block), `M=0.5`/`M=2` per-step |
| Stability is not unique to SN-OMD, but the *predictable* scale is | ten frozen windows, divergence partition | `tab:replication` — **corrected and adopted** at `de33ee0`. The Phase-2 confound is fixed, not outstanding: the printed table *is* the matched-budget one, and every statement it invalidated was repaired |
| The tracker is a documented choice, not a free win | block-median co-leads per-row ($0.28\pm.09$), statistically tied with Cutkosky–Mehta ($0.29\pm.04$) — **and, since C13, not shown to beat the deployed EMA per-row** once the subsection's own Bonferroni correction is applied ($+0.046$, CI $[-0.006,+0.098]$). The "not a free win" reading is *strengthened* by Phase 3, not weakened | `app:tracker` |
| RMSProp/Adam do **not** diverge — they are bounded-step | run head-to-head, not argued | `app:adaptive` |

**Headline numbers**, re-verified against `tab:replication` on 2026-08-26 — the ten-window row had been carrying the pre-adoption figures since `de33ee0` and survived two later sweeps.
Per-row weighted R² on window 1: SN-OMD `0.285±.080`, per-step
`0.307±.059`. Ten-window frozen, **matched budget**: SN-OMD (`M` tuned) `0.24±.05` (0/10
divergences), its block-median variant `0.28±.09`, Cutkosky–Mehta `0.29±.04`. Stability
partition on crypto: OGD diverges `10/10`, uncapped endpoint `3/10`, every bounded
scale-free method `0/10`.

---

## Audit history

Five review rounds. Each ran adversarially against the previous round's output, and each
found something the previous one had not.

| Round | Date | Outcome |
|---|---|---|
| Pass I | — | Liu citation fix; iterate norm measured directly (`fig:iternorm`) rather than asserted |
| Rev. 2 | — | Liu & Zhou (2025) cite; §1 tail-scope qualifier; Aggarwal (2026) concurrent work |
| Pass II | 2026-08-18 | Reproducibility disclosures |
| Pass III | 2026-08-18 | 3 regressions fixed; **RMSProp/Adam run rather than argued** — §5's "they diverge" was false and was removed |
| Pass IV | 2026-08-21 | **Predictable-scale defect** found and fixed; 12 artifacts regenerated; 15 manuscript numbers reconciled |
| Verification sweep | 2026-08-22 | Divergence-count propagation, "intentional" site audit, negative-control grep, 2 pre-existing errors fixed |
| Pass V | 2026-08-22 | Frozen ICML-round audit re-checked against the current tree; 3 of its 4 open findings closed |
| **Phase 2** | 2026-08-23/24 | Eight preregistered research directions. Found the ten-window comparison confounded, the divergence criteria non-transferable, and "divergence" mis-named. See below |
| **Phase 3** | 2026-08-25/26 | An external revision assessment, then two propagations. Its three consistency regressions were real; the per-row tracker claim **inverted** under a re-run bootstrap (C13); the switching bound closed **negatively** (D1B); Prop F.1's analytical discharge measured **empty on this data** (D1C). See below |

### Two results worth carrying forward

**Pass III — the armchair argument was wrong.** §5 claimed EMA-denominator optimizers
inherit the scale drift and diverge. Running them showed the opposite: sharing the round
*bounds* the step, since `v_t = ρ·v_{t-1} + (1-ρ)·g_t²` forces
`|g_i|/√v_i ≤ (1-ρ)^(-1/2)` however extreme the gradient. RMSProp and Adam belong in the
bounded family, and they *tie* SN-OMD once the step schedule is matched — the fourfold
gap a naive comparison shows is the schedule, not the preconditioner.

**Pass IV — the code did not implement Algorithm 1.** Three research scripts normalized
by the post-update scale `s_t` instead of the predictable `s_{t-1}`, making the deployed
tracker `F_t`-measurable. That is precisely the property Freedman (`lem:freedman`) and
`ass:track` require, and the one §1 uses to distinguish SN-OMD from normalized-GD. The
library and every theory-validation script were always correct; only the scripts behind
the tables were not.

The defect was **measured before it was fixed**
(`scripts/research_predictability_check.py`): a 2×2 of {post-update, predictable} ×
learning-rate grid with a *paired* circular block bootstrap, because marginal SEs (~.08)
cannot resolve a ~.04 gap between two runs on the same rows. Result: **the grid accounts
for +0.0379 of the +0.0378 total gap; measurability accounts for 0.3%.** The defect was
real and is fixed — but it is not what moved the number, and a Pass-III edit that had
claimed otherwise was itself reverted.

Two substantive consequences reached the manuscript: the uncapped endpoint diverges on
`7/10` per-row rather than `6/10`, and a Bonferroni correction at α/14 now flips *two*
verdicts rather than one. Neither is load-bearing — the tracker claim the paper makes is
the per-row one, where every gap survives correction.

### Methodological note

Two full audits had independently reverified `tab:replication`'s divergence count as
"exact" against `windows_replication.csv` — and that CSV was generated by code carrying
the predictability bug the whole time. Both audits confirmed the arithmetic and neither
had any way to know the ground truth was wrong. **Matching a stored artifact proves
internal consistency, not correctness.** Every number in the verification sweep was
therefore re-derived against *regenerated* CSVs, not against their predecessors.

A related failure mode: a non-raw Python string turned `\texttt` into a literal tab, so a
citation rendered as `exttt{...}` — and LaTeX compiled it with **0 errors and 0 undefined
refs**. A clean build proves the syntax parsed, not that it is the syntax you meant.

---

## Frozen ICML-round audit (`AUDIT_REPORT.md`)

That file is read-only and is **not** updated. Its Top-10 findings were re-checked against the
current tree in Pass V — six were already resolved, four were still open, three are now closed.

| # | Finding | Status |
|---|---|---|
| 1 | CRITICAL — repo not anonymized, export never run | Resolved |
| 2 | MAJOR — `tab:residual` surrogate rows unbacked | Resolved |
| 3 | MAJOR — bootstrap-SE prose contradicts its table | Resolved in substance; a residual imprecision, below |
| 4 | Extend the staleness test to bootstrap CSVs | **Closed Pass V** |
| 5 | MODERATE — per-regime theorem, undischarged assumption | Closed by design (hedged) |
| 6 | MODERATE — headline numbers not reviewer-reproducible | Partial |
| 7 | MINOR — `references.bib` orphaned | **Closed Pass V** |
| 8 | MINOR — doc-drift "Theorem 3.3" | Resolved |
| 9 | MINOR — `ScaleNormalizedOGD` vs "OMD" | **Closed Pass V** |
| 10 | MODERATE — block length may understate variance | Open |

### Why finding 4 mattered more than its rating

Its recommended action was never taken, and the cost compounded. The staleness test guarded
exactly one CSV; none of the bootstrap artifacts was checked against anything. That is why the
predictable-scale defect survived two audits which both certified `tab:replication`'s divergence
count as "exact".

Adding those CSVs to the regeneration guard would **not** have caught it — generator and
artifact were wrong together, so re-running reproduces the same wrong file and the test stays
green. The new guard compares the pair that actually has to agree: **the number printed in the
paper and the measurement behind it**. It reads committed bytes only, so it runs in a data-less
checkout, and it is verified by mutation — reverting the prose `7/10` to `6/10` fails it.

---

## Phase 2 — research execution (2026-08-23/24)

Eight preregistered directions on `research/c10-q6`. Every one registered in
`experiment_matrix.yaml` and committed **before** execution; ledger in `claim_ledger.md`,
state in `research_state.md`. **At the time, none of it was merged and no manuscript text was touched — that was out
of scope for the phase.** Both have since changed: Phase 2 landed on `master` via PR #8
on 2026-08-25, and the manuscript consequences were worked through in the adoption and
publication passes below.

| Dir. | Question | Outcome |
|---|---|---|
| C10/Q6 | Does a constant scale really beat a tracked one? | **H1 survived** — the gap is a tuning-budget artifact and **reverses** |
| C10M | Is clip-binding frequency the mechanism? | Both hypotheses **inconclusive**; binding rate is the *weakest* predictor |
| C10S | Where exactly is the stability threshold? | **H4 inconclusive**; `P*≈11.5` on Jane, spread 1.68× across rays |
| C10R | Does the *realized* max step explain the residual? | **Vacuous** — a degenerate fit made the test an identity |
| C10T | Same, on a third stream | **VOID** — both divergence criteria structurally broken |
| C10C | Build a stream-comparable criterion | **Rejected** on a mis-specified test |
| C10C2 | Correct that test | **Rejected** again; the test was *unfalsifiable* |
| C10C3 | Drop it, add blind tests | **ACCEPTED**, with load-bearing qualifications |

### What bears on the manuscript

Three claims in the table above are now known to rest on evidence that cannot support them.
**The stored numbers are not wrong** — the preregistered reproduction gate re-derived them
from source and matched `windows_replication.csv` to `diff = 0.0000` in both protocols. What
fails is the *comparison design*.

1. **The ten-window comparison is confounded by tuning budget.**
   `research_windows_replication._grid` gives `fixed-tau clip` a joint 2-D grid over
   `(lr × tau)` = 70 configurations and gives SN-OMD a 1-D grid over `lr` alone = 10, with the
   cap pinned at `M=5` — a value chosen in a *separate* sweep at a single fixed `lr=0.5`,
   never jointly. At matched budget (70 joint `(lr × M)`) the **ordering reverses**: held-out
   per-row SN-OMD `0.2270` vs fixed-tau `0.2020`, SN-OMD winning 9/9 held-out windows and
   10/10 overall. The published SN-OMD ten-window figures are the **under-tuned** ones.
2. **The fragility attributed to the tracked scale is a property of that configuration.**
   Held-out sd falls `0.103 → 0.040` and the window-7 collapse (`−0.107`) disappears entirely
   at matched budget.
3. **The reported ten-window mean pools its own selection window.** Per-row the published
   SN-OMD arm *wins* window 1 (`0.2846`) and loses all nine held-out windows — a
   selection-overfitting signature the pooled mean conceals.

Also established, and relevant to how `tab:replication` should be read:

- **"Divergence" was never iterate divergence.** `thm:stability` bounds
  `‖w_T‖ ≤ 2·lr·M·√T`, so a finite cap makes iterate blow-up impossible; every divergence
  measured in this project is a **loss** phenomenon. Measured `max‖w‖` across the whole
  capped grid never exceeded `276.6`.
- **The inherited divergence criteria carry units and do not transfer.** Under a pure change
  of units the Jane rule changes its answer on 54–94% of runs; it fires on the *zero
  predictor* on a heavy-tailed stream. A scale-invariant replacement is now accepted at
  `scripts/research_divergence.py` (1.000 invariant on every stream).
- **Capped SN-OMD does not diverge at all on a stationary-scale synthetic stream**, at any
  `P ≤ 256`, while it does on Jane and crypto. Whatever the threshold measures needs scale
  drift.

**Consequence for submission.** `tab:replication` and any prose resting on the ten-window
ordering should be re-run at matched budget before the paper is submitted, or the claim
narrowed to what the current design supports. This is a **new blocker**, entered below.

## Adoption of the matched-budget table, and what it invalidated

`de33ee0` adopted the C12/C12B numbers into `tab:replication`. Adoption changed what the
table *is* — the cap `M` is now a tuned parameter there, not a pinned one — and that
invalidated statements elsewhere that the adoption commit did not catch. Repaired
2026-08-24:

| Where | Was | Now |
|---|---|---|
| `tab:replication` caption | "All *accuracy-relevant* optima are interior" | False as written: C12's own boundary flags put the **per-step SN-OMD row at both grid edges** (`lr=8` ceiling, `M=0.5` floor, collapsing toward the `M→0` normalized-GD endpoint). Caption and `app:grid` now record it. |
| Limitations (§6) | "not fully tuning-free (setting-dependent rate; untuned `M`, decay, winsorization)" | `M` *is* tuned in the headline table, so the method carries **two** tuned parameters. The limitation got stronger, not weaker. |
| `app:grid` cap paragraph | "The one axis we do *not* tune is SN-OMD's cap `M`, fixed at 5 a priori" | Scoped: `tab:jane`/`fig:main`/the cap sweeps pin `M=5`; `tab:replication` does not. |
| `app:grid` ranking robustness | frozen block 0.29, EMA 0.14 | Scoped to the pinned `M=5` re-sweep, which is what that check actually varied; the matched-budget 0.24 is noted as reaching the same place from window 1 alone. |
| `tab:grid` caption + footnote | "We do not tune `M` (fixed at 5 a priori) … does not enter any reported number" | Both false after adoption; rewritten. |

One corroboration worth recording: the ten-window cap sweep says the block tracker's cap
optimum is a plateau at `M=5–7` (0.29) with `M=10` falling back to 0.28. C12B, selecting
`M=10` from **window 1 alone**, measures 0.2817 across the ten — an independent
reproduction of that sweep to 0.002.

## Detailed diagnostics moved to the appendix (2026-08-24)

Main text 9.007pp → **8.615pp** (0.392pp freed, ≈21 typeset lines). Nothing was deleted:
every moved number is either already stated in the appendix or was added there by the same
edit, and a mechanical check confirms all 24 moved facts are present post-`\appendix`.

| From | To |
|---|---|
| Estimator-by-estimator tail decomposition, the GARCH causal-estimation-cost argument, the rank-ACF/Ljung–Box statistics, the per-day Hill caveat, the null-control script name, the 200k-gradient provenance | new **"Tail diagnostics in detail"** paragraph in `app:tables`, beside `tab:residual` |
| Crypto replication read out number-by-number | `app:secondmarket`, which already carried all of it |
| Single-window error-bar audit (±.079 vs ±.037) | `app:tracker`, next to the variability finding it belongs to |
| Block-median paired CIs (+0.15, +0.11, +0.004 …) | `app:tracker` |
| Per-timestep batching numbers, learning-rate spans | `tab:jane` |
| RMSProp/Adam boundedness derivation and peak-loss figures | `app:adaptive` |
| Iterate-norm envelope detail | `app:iternorm` |

The §4 tail paragraph was also split in two — it was a single 37-line block carrying the
paper's central finding.

## Figure inversion fixed (2026-08-24)

`fig:problem` carries the paper's central measurement — the interaction tail and the drifting
scale — is cited three times from the main text and **only** from there, yet it typeset as
**Figure 6, in the appendix**, while a validation figure was Figure 1. Promoted into the body,
immediately before `fig:nullcontrol`, so the reader meets the phenomenon before the controls
that validate it:

| | before | after |
|---|---|---|
| Figure 1 | `fig:nullcontrol` — body | **`fig:problem` — body** |
| Figure 2 | `fig:main` — body | `fig:nullcontrol` — body |
| Figure 3 | `fig:mechanism` — appendix | `fig:main` — **appendix** |
| Figure 4 | `fig:iternorm` — appendix | `fig:mechanism` — appendix |
| Figure 6 | **`fig:problem` — appendix** | `fig:tracker` — appendix |

All appendix figures renumber down by one and every `\cref` resolves; 0 undefined refs.
Its caption lost three sentences that restated the paragraph directly above it; the unique
one — why an order-shuffle leaves the *pooled* index unchanged (an order-statistic identity)
— moved into `app:tables`' tail-diagnostics paragraph. `fig:nullcontrol`'s caption lost the
GARCH band, which now lives in that same paragraph.

**Cost: 0.392pp**, i.e. exactly the margin the relocation had freed. Recovered ~0.06pp by
trimming caption/prose restatement, then closed the gap structurally: **`fig:main` moved to
`app:tables`**, beside the other single-window artifacts. It is a *single-window*
learning-rate sweep; `tab:jane` carries its values and `tab:replication` carries the same
dichotomy across ten windows and stays in the body, so nothing it shows leaves the main text's
evidence base. Its caption title changed from "Main result" — never accurate for a
single-window sweep, and misleading in an appendix — to "The stability dichotomy on the
reported window".

Final body inventory: **Figure 1** (the phenomenon), **Figure 2** (the null controls),
**Table 1** (the ten-window replication), **Algorithm 1**. Main text **8.502pp**, ~0.50pp of
margin. The four `[h]` floats were promoted to `[htbp]` in the same pass, closing
the last float-specifier warnings.

## Publication-quality pass (2026-08-24)

Four commits, `82e290b`..`(this one)`. Cost 0.218pp of the 0.498pp margin; main text
8.502 → 8.720pp.

| Brief § | What changed |
|---|---|
| 5 Introduction | Dropped the generic "Financial markets are a canonical source…" opening — eleven lines of background before the paper said anything of its own. Its six citations survive, compressed into a positioning paragraph. The 36-line two-paragraph opening is now four paragraphs with one job each. |
| 6 Contributions | Two of three bold leads were topic labels, so the list read as a table of contents. Each lead is now the claim; item 3's states the honest result the old label buried. |
| — Abstract | The audited 26-line slab: longest compound sentences broken, em-dash chains reduced, filler cut. Single paragraph, all ~8 claims kept in order. |
| 4, 7, 11, 18 | Seven body paragraphs split at seams they already had. Cost 0.011pp — `\parskip` is ~0 here, so structure is nearly free. |
| 21, 23 Terminology | "per-timestep" (6) vs "per-step" (28) unified on per-step, zero remaining. Two near-identical method lists under two names — they differ by exactly the uncapped endpoint, which is the paper's point — now say so. Three names for the fixed-τ baseline reduced to one plus a gloss. |
| 16, 17 Captions | Five of seventeen float captions lacked a bold lead or a section reference; now uniform. `tab:jane`'s 19-line caption trimmed to 11, its self-correction note moved to `app:tables` prose. |
| 19 Equations | All three body displays already punctuated as sentence parts and correctly introduced. No change needed. |
| 21 Typography | One em-dash rendered "it— AdaGrad" from a source line break. Ragged-right bibliography fixes the visibly-stretched Jane Street entry (two badness-10000 lines). Two `\cref`s rendered "Sections B.1 and 3" — cleveref sorts appendix numbers first — split with explicit connectives. |
| 22 Tone | Scanned for overclaiming: no "state-of-the-art", "outperforms", "dramatically", "we believe". The one "novel" is *"we claim no novelty for the mechanism"*. No change needed. |
| 8 Theory | Both formal statements mixed result with interpretation. Proposition 3.1 said "Hence … Hence …" and ended in three clauses of reading; it now states, and the reading follows in two paragraphs. Theorem 3.2's environment title was doing bibliographic work, and its hypotheses, tuning, comparator, horizon and probability all arrived in one sentence; hypotheses are now separate sentences, the pointer is prose, and the two costs are one paragraph each. |
| 9 Tracker | Was a trailing clause at the end of the dense Algorithm paragraph — three names, no definitions — despite being what Assumption D.1 is about and where the paper's main honest limitation lives. Now its own paragraph, one line per tracker, gap stated up front. |
| 10 Related Work | Had no map, and said "we differ in targeting dynamic regret under a drifting scale" three times. An orienting lead states the three literatures and the gap once; each paragraph keeps only its own delta. The Cutkosky–Mehta head-to-head (results, not related work) keeps the verdict and cites the decomposition. The dynamic/scale-free paragraph now answers the question its citation list left open: scale-freeness there is invariance to one *global* rescaling; the drift here is *within* a stream. |
| — De-duplication | The SN-OMD update was written out three times in two pages (intro display, Section 3 prose, Algorithm 1); the prose copy goes. The "Further experiments" signpost summarised both appendix studies instead of pointing at them. The Conclusion's opening restated the abstract sentence for sentence; it now says what the result means. |

**One clarity repair found in passing.** The tail-diagnostics paragraph and `tab:residual`'s
caption both quoted the GARCH surrogate's normalized index, as `3.9–4.5` and `4.1–4.8`.
Both correct — different sweeps, one over assumed persistence and one over threshold — but
nothing said so, and forty lines apart it reads as a discrepancy. The paragraph now gives the
union with both axes named and defers to the table.

**§25 no scientific regression, verified mechanically.** Diffing every numeric literal in
the `.tex` against `5c8a9ad`, the commit before the pass, over all seven commits: four
changes total. Two are the deliberate GARCH-range reconciliation (`4.5`→`4.8`,
`≈9`→`8–10`), both matching what `tab:residual` already prints. Two are a subscript index
from a deleted duplicate equation and the `β=0.5` value in the Cutkosky–Mehta paragraph,
whose full decomposition is stated in `app:tracker` and cited from the sentence that
replaced it. Every reported result is identical, `tab:replication` included.

## Appendix QA, page by page (§26, 2026-08-24)

The publication pass had worked the main text; this is the appendix read as a reader
meets it -- in typeset order, with every float, heading, and relative reference checked
against where it lands. Main text untouched at **8.871pp**; every reported number
identical (numeric-literal multiset diff against `7f6b1ee`: **1078 = 1078**).

| Finding | What it was | What it is now |
|---|---|---|
| **Eight pages of experiments filed under "Proofs"** | Synthetic streams, the crypto/image second market, trackers, grid adequacy and RMSProp/Adam typeset as §E.9–E.13, i.e. as subsections of Appendix E, running pp.21–28. A reader looking for the crypto replication found it inside a proofs appendix. | Their own top-level **Appendix F, "Scope and robustness"**, with a lead saying what the five studies are for: two ask whether the mechanism appears away from Jane, two ask whether our own choices (tracker, grid) carry the result, one runs the adaptive optimizers rather than arguing about them. Sectioning level only — no prose moved. |
| **A cross-reference pointing at the wrong subsection** | *"removed by the strongly-adaptive wrapper of the preceding subsection"*, in the tracker subsection, resolved to *"A second market (crypto), and an image-model boundary"*. The wrapper is in "Reductions", four subsections earlier. | "Reductions" labelled `app:reductions`; both relative references replaced by `\cref`. |
| **Two headings making the same promise** | *"Discharging the scale-tracking assumption"* appeared twice five pages apart — §B.2 (the measurement) and §E.8 (the bracket proposition). | Retitled in the paper's own terms: **"…: what we measure"** and **"…: what we can prove"**. |
| **Five floats parked away from their prose** | `fig:tracker` and `tab:beta` are each cited exactly once, from §B.2 on p15, and were typeset on pp.20 and 22; `tab:tracker` sat in a subsection that never cites it; `fig:synthetic` and `fig:msweep` were sourced inside the crypto subsection but are cited only from the synthetic one. | All five moved next to the prose that reads them. Every appendix float now lands in the subsection that cites it, `tab:grid` (2 pages, float mechanics) excepted. |
| **Nothing pointed at the new Appendix F, and Appendix B had no lead** | B opened straight into its first subsection. | One lead paragraph in B does both jobs: these are the two studies the main text promises, and the ones it does not are in `app:scope`. It is also what keeps B and F from reading as two appendices with the same title. |

Checked and clean: no heading stranded at a page foot (font-size sweep over the typeset
pages); no sentence appearing twice anywhere in the paper; no terminology the main-text
pass unified drifting back in the appendix half; no hard-coded appendix letter that the
promotion could falsify (every pointer goes through cleveref); no `\cref` rendering with an
appendix number before a plain one; and no overclaiming or stale "tuning-free" language
left over from the `M`-tuning adoption.

Two things left deliberately. §E.2 *"The iterate norm obeys the stability bound
(measured)"* is a measurement inside Proofs, kept there because it sits directly under the
stability proof it checks. And one underfull `\hbox` (badness 1342) remains in the
dynamic-regret proof, where a long unbreakable math atom ends the line; rewording a proof
to fix one mildly loose line is not a trade worth making. The two badness-10000 pages the
old structure produced are gone.

Build after the pass: 29pp, exit 0, **0 overfull, 0 undefined refs**, underfull boxes
6 → 4. 106 tests pass.

## Publication pass: closing report (§28)

Nine commits, `82e290b`..`b44999d`, over the brief's §4–§30. Three earlier commits paid
for them structurally: `3af12c6` (detailed diagnostics to the appendix), `fb276ce` (the
figure inversion — the paper's central measurement was typesetting as Figure 6 in the
appendix while a validation figure was Figure 1), and `5c8a9ad` (`fig:main` demoted).

**What actually changed.** Almost none of it was typographic. In order of how much a
reviewer would notice:

1. *The paper now opens on its own claim.* The Introduction spent eleven lines on
   generic background before saying anything of its own. It now opens on the finding
   itself — a heavy gradient tail is largely manufactured by a drifting scale, and largely
   removed by dividing by a causal estimate of it — with the background compressed into a
   positioning paragraph that keeps all six citations.
2. *The contributions read as claims rather than as a table of contents.* Two of three
   bold leads were topic labels; item 3's lead now states the honest result the label
   buried.
3. *The two formal statements state, and the reading follows.* Proposition 3.1 ended in
   three clauses of interpretation; Theorem 3.2's environment title was doing
   bibliographic work and its hypotheses all arrived in one sentence.
4. *The scale tracker got its own paragraph.* It had been a trailing clause — three names,
   no definitions — despite being what \cref{ass:track} is about and where the paper's
   main honest limitation lives.
5. *Related Work got a map.* Three literatures, the gap stated once instead of three
   times, each paragraph keeping only its own delta.
6. *The appendix stopped filing eight pages of experiments under "Proofs"* (§26 above),
   and five floats went back to the prose that reads them.
7. *One clarity repair found in passing*: two GARCH ranges forty lines apart read as a
   discrepancy; both were correct, over different sweeps, and now say so.

**What was verified, and how.**

| Check | Result |
|---|---|
| §25 no scientific regression | Numeric-literal multiset diffed at every commit. Over the whole pass: `0.5`,`4.5` out; `1`,`10`,`4.8` in. Two are the deliberate GARCH reconciliation, one the subscript of a deleted duplicate equation, one the `β=0.5` whose decomposition is stated in `app:tracker` and cited from the sentence that replaced it. Every reported result identical, `tab:replication` included. |
| §27 page budget | Main text **8.871pp** of 9. Measured from the PDF by line-gutter geometry, not by page count. |
| Build | 29pp, exit 0, **0 overfull**, **0 undefined references**, 4 underfull boxes (float slack plus one badness-1342 proof line). |
| Cross-references | Every `\cref` resolves; no multi-target reference rendering an appendix number before a plain one; no hard-coded appendix letter anywhere. |
| Floats | Figures 1–9 and Tables 1–7 sequential; every appendix float in the subsection that cites it, `tab:grid` excepted (2 pages, float mechanics). |
| Prose | No sentence appearing twice anywhere; terminology unified across body and appendix; no overclaiming vocabulary; no stale "tuning-free" language after the `M`-tuning adoption. |
| Tests | 106 pass. |
| Anonymity | 0 identity tokens in the manuscript. |

**What was deliberately left alone.** No experiment, dataset, or number was invented or
changed. No limitation was softened — the Limitations restatement makes one *stronger*,
recording that the deployed method now carries two tuned parameters. No underperforming
method was dropped, and the GARCH and null controls stay. Nothing was fitted into the page
budget by shrinking a font, a margin, or a float; the 0.14pp the pass cost came out of
redundancy — the SN-OMD update had been written out three times in two pages, a signpost
summarised what it should have pointed at, and the Conclusion restated the abstract.

**Where the paper stands.** The manuscript is submission-shaped: within budget, clean
build, reproducible tables, anonymized supplement. What remains open is not writing.

## Phase 3 — the revision assessment, and the two propagations (2026-08-25/26)

An external manuscript-revision assessment (v2 vs v1) opened this phase. It named three
consistency regressions and ranked four research directions. **The regressions were real.**
The top-ranked direction turned out to be already resolved in our own record — and following
that thread properly closed two things the paper had been presenting as open, or as
available.

Same discipline as Phase 2: registered in `experiment_matrix.yaml` and committed **before**
execution, ledger in `claim_ledger.md`, state in `research_state.md`, theory in
`theory_notes.md`. Unlike Phase 2, manuscript text **was** in scope here, because two of the
three results contradict sentences the paper prints.

| Dir. | Question | Outcome |
|---|---|---|
| C13 | Does `app:tracker`'s paired bootstrap survive the adopted matched-budget table? | **Partly not.** The Cutkosky–Mehta tie holds; the per-row block-over-EMA gap falls `+0.152 → +0.046` and **no longer survives** the subsection's own Bonferroni correction |
| D1B | Can Remark D.3's switching bound be derived? | **Closed negatively.** `N` grows at least linearly, so the target rate is `Θ(T)` at every `p` — the bound is *unavailable*, not underived |
| D1C | Does that same count also void Prop F.1's discharge? | **H_D1C survives in the operative regime.** `NW ≪ T^{1/p}` fails on *both* factors; Prop F.1 is correct and **empty here** |

### C13 — the assessment's three regressions were real, and the fix does not all go one way

`tab:replication` took the C12/C12B matched-budget rows two sessions earlier, but the paired
across-window bootstrap behind `app:tracker` was never re-run. So the appendix claimed a
`+0.15` block-over-EMA gap against a table whose own cells differ by `+0.05`.

No new compute was needed — `c12_matched.csv`, `c12b_blockmed.csv` and `windows_cm.csv`
already hold per-window values on identical windows, so `research_c13_matched_bootstrap.py`
recomputes the same statistic with the same floor, pairing and intervals, and only the input
changes.

- **The CM tie holds.** `+0.004 → −0.005`, CI `[−0.036, +0.025]`, 6/10. The nominal lead flips
  to CM and the interval still straddles zero, so the abstract's tie language stands as
  written. This was the open question and it came back favourable.
- **The per-row tracker claim inverts.** `+0.152 → +0.046`, CI `[−0.006, +0.098]` — under the
  subsection's own Bonferroni correction the block median is *not shown* to beat the deployed
  EMA per-row. That is the claim the old text called load-bearing while dismissing two
  per-step failures as not. The sentence is **inverted, not softened**.
- **Per-step strengthens**, block now clearing zero against both the EMA and the clip where
  the pinned-cap run tied both — with the caveat that the per-step SN-OMD row sits at two grid
  edges, so it is a truncated comparator.

Two things found while checking, which the assessment had not raised. CM is tuned over **216**
configurations against 70 for the capped methods — a deliberate call in the research record
but undisclosed in a caption that enumerates every other method's budget; now **disclosed, not
reversed**. And `research_predictability_check.py`'s measurability arm is a direct measurement
of what predictability costs in accuracy (`+0.0001` to `+0.0009`), which is the paper's own
framing claim, until now asserted rather than shown.

**Why the drift went unnoticed for two sessions:** no `PAPER_CLAIMS` entry covered the per-row
figures. Three guards now point at `c13_matched_bootstrap.csv` (two new cases, one existing
guard re-pointed — it failed correctly when the sentence was reworded).

### D1B — the switching bound is unavailable, not underived

The assessment ranked "D1 — variation-adaptive bound" highest. **The naming was wrong and our
own record said so:** ledger C-13 had established that this bound already exists inside
`thm:regret`, which carries `W_s` and `P_T^s` explicitly. The object actually left open was
Remark D.3's *switching* bound in the regime count `N`.

D1B registered that, with a **premise check ahead of the derivation** — and the check settled
the direction on its own. The target rate `Õ(N^{1−1/p} T^{1/p})` is non-vacuous only if `N` is
sublinear in `T`; at `N = Θ(T)` it is `Θ(T)` for every `p`, which is the vacuous bound the
direction exists to escape. Measured on the committed 200k-round scale process using the
paper's own definition of a regime — a horizon over which the tracker's upward variation is
`O(1)` — `N` grows with an exponent of **at least 1** (fitted `1.155`–`1.240` across the eight
tracker×budget combinations with enough segments to fit one). So no proof of that form can
help here, and D1's three GAP sub-problems are now unmotivated on this data.

**Two things make this a claim rather than an impression.** The ≥50-segment reliability rule
is `tab:beta`'s own, already applied there to the analogous `W_s` fit — and it discards exactly
the seven combinations that looked sublinear, so it removes the only evidence that would have
licensed proceeding. *A filter that costs me the outcome letting me keep working is not one
chosen to reach the conclusion.* And `N ≤ T` by construction, so the fitted value above 1 is a
finite-horizon artifact; the claim made is the **lower bound**, which is all the argument needs.

Five manuscript sites said "left open". They now say closed, with the measurement in a new
appendix subsection, and Limitations concedes that the per-regime restriction is **not a gap we
expect to close** — stronger and less flattering than "left open". That also closes the route
by which the introduction's reframe could have been redeemed theoretically.

### D1C — a discharge that is correct and empty

D1B closed a route the paper listed as *open*. D1C asked the more consequential question:
does the same measurement void something the paper presents as **discharged**?

Prop F.1 buys the lower bracket at one added term `O(D·N·W·sup_t σ_t)`, "dominated whenever
`NW ≪ T^{1/p}`". Both factors were measured for the first time, and neither is small.

- **`N`** is at least linear (D1B) — and now also **tracker-free**. A non-causal block-median
  segmentation with no adaptive filter in the loop gives boundaries per block of
  `0.193 → 0.210` (`c=0.5`) and `0.121 → 0.135` (`c=1`) as the block length runs `50 → 1000`:
  a roughly constant *rate*, so the linearity is a property of the process, not of our filters.
- **`W`** is not free either, which the paper's own proof sketch says: the blocking step needs
  `≍W/ℓ` near-independent blocks of length `ℓ ≳` the mixing time. The scale process's rank
  autocorrelation is `0.180` at lag 1 and still `0.069` at lag 2000 — it never reaches `0.05`
  in the range tested — so `ℓ ≳ 2000` and `W ≳ 2×10⁴`.

**(a) Asymptotically**, `NW/T^{1/p} ~ T^{1−1/p}`, evaluated at `β = 1` **exactly** rather than
at the fitted exponent, so the conclusion cannot be attacked through the finite-horizon
artifact. `1 − 1/p > 0` for every `p > 1`: there is no admissible `p` at which the term is
dominated.

**(b) At the paper's own horizon** (`T = 200 000`, envelope tracker, measurable `c` only):

| `W` | `p=1.3` | `p=1.5` | `p=2.0` |
|---|---|---|---|
| `64` — the tracker's own window, which *ignores* the blocking requirement and is therefore the most favourable value available | 0.46 – 1.7 | 1.6 – 6.0 | **12 – 46** |
| `2×10⁴` — what the proof actually needs | 144 – 537 | 503 – 1877 | **3846 – 14356** |

The script's registered verdict line reads **"falsified in part — dominated in 2 of 18
measurable combinations"**, and those two cells are reported rather than buried: `c=1, W=64,
p=1.3` (`0.894`) and `c=2, W=64, p=1.3` (`0.460`). They do not rescue the proposition. Each
needs `p = 1.3` — a heavier tail than the measured normalized index admits, since `ass:moment`
caps `p ≤ 2` and ledger C-14 records the measurement pinning it *at* 2 — **and simultaneously**
`W = 64`, shorter than the proposition's own blocking argument permits. Domination requires
both a tail we do not have and a window the proof does not allow, which is why the operative
reading is that **H_D1C survives**.

So Prop F.1 is not wrong. It is **empty here**: its guarantee is real for a process with
macroscopic regimes, and this process does not have them. What the paper actually leans on is
§B.2's *empirical* discharge — 100% lower-bracket coverage, measured — and three claim sites
(§3, §F.2, §B.2) now say that rather than implying the analytical route is available.

### Two corrections to my own D1B write-up, forced by D1C's review seams

Recorded because the tracker is where this kind of thing has to be visible.

1. **S2 — a corroboration claim that was near-tautological.** D1B reported the agreement
   between `N`'s exponent and `tab:beta`'s `β` for `W_s` as *independent* corroboration, "two
   views of one drift process". It is not independent: `W_s` sums upward moves and `N` counts
   the boundaries those same upward moves induce when they accumulate past `c`. It is one
   measurement viewed twice. **Withdrawn as corroboration** in the manuscript, `theory_notes.md`
   and ledger C-20 (point 2 struck through); kept as an internal consistency check. The `N`
   claim is unaffected — it never rested on this.
2. **S3 — a defence overstated as a binary.** D1B asserted that a tracker coarse enough to see
   few regimes *fails* the lower bracket. `tab:beta` shows the `B=10⁴` tracker holds it at
   **0.93**, not 0. The accounting reaches the same place and is checkable rather than
   asserted: 7% of rounds violating, charged trivially at `O(D sup σ)` per round, is
   `0.07·T = Θ(T)`. Coarsening trades an `O(NW)` lapse set for an `O(T)` violation set — the
   same wall by a different route.

### What Phase 3 costs the paper, and what it buys

**Costs.** One appendix tracker claim inverted (C13). Two theory routes closed rather than
open (D1B, D1C). Limitations now concedes the per-regime restriction is permanent. None of
this is a retreat under pressure — every item is a measurement, and the two that could have
gone the other way (the CM tie, D1C's 2-of-18 cells) were registered as such in advance.

**Buys.** Two independent measured obstructions now stand — `W_s = Θ(T)` and `N ≥ Θ(T)` —
which together say this class of stream has **no macroscopic regime structure at any
resolution that preserves the bracket**. `research_state.md` Session 14 records the candidate
reframe this suggests and **explicitly does not act on it**: T4 resolves first. See open
item 9.

---

## Open items

| # | Item | Status |
|---|---|---|
| 1 | ~~`tab:replication` rests on a confounded comparison.~~ | **Closed 2026-08-24** — corrected table adopted at `de33ee0`, and the four appendix statements it invalidated repaired. |
| 2 | ~~Wall-clock runtime figure for the Reproducibility Statement.~~ | **Closed** — `research_runtime_suite.py` times a defined set (every script the paper names, plus the ones that generate the tables it prints), one fresh interpreter each, writing `results/research/runtime_suite.csv` incrementally. Measured: **3.0 h** over 29 scripts on one commodity CPU, of which the **Kaggle-free** subset — everything a reviewer without a competition account can run — is **3 min** across 5 scripts. Slowest three: `research_c12b_blockmed.py` 50 min, `research_c12_matched_table.py` 37 min, `research_grid_adequacy.py` 15 min; the two C12 runs alone are 49% of the total. One caveat on the measurement: rows 17–24 of the CSV overlapped for part of their run with one other single-threaded job on this 12-core machine, so those eight figures are upper bounds by a small margin. The total is robust to it — even a 10% inflation on all eight moves 177 min by 4 — and the rest of the CSV was measured with nothing else running. |
| 3 | ~~§4 sentence on the deployed schedule.~~ | **Closed** — placed in **Limitations**, not §4: it is one window on one shared grid, weaker evidence than anything in §4, and Limitations is where the paper already concedes its tuned parameters. It stands on the schedule argument alone, as required — the paired bootstrap attributes the $0.285$-vs-$0.247$ difference to the grid, but the $0.52$-vs-$0.25$ gap is the schedule. |
| 4 | GitHub release | **Decided and staged; one command short of done.** The judgement call was put to the author, who chose to proceed. Everything the release needs exists: the `iclr2027-phase2` tag is pushed, the notes are written, and the PDF asset is verified clean. It is blocked on the two-identity problem below — not, as this row previously claimed, merely a judgement call. See **The two GitHub identities** below. |
| 5 | ~~Audit finding 10 — bootstrap block-length sensitivity.~~ | **Closed, and the answer is not the one the objection expected.** See below. |
| 6 | ~~Audit finding 6 — Jane numbers not reviewer-reproducible.~~ | **Closed** — `research_jane_mini.py` closes it from both ends: a seeded mini-slice in the Jane schema drives the same loader, harness and evaluation with no market data, and the same script pins the sha256 of the real canonical slice so a reviewer with their own download can confirm it matches before spending the compute. Covered by `tests/test_jane_mini.py`. |
| 7 | ~~Audit finding 3 residual — the SE claim names no comparator.~~ | **Closed** — and it was two defects. The prose said `±.079` where the table prints `±.080`, the same prose-versus-table disagreement finding 3 was about, recurring; and "about twice normalized-GD's" picked the flattering comparator when SN-OMD's is the *widest* bar in that column. Both fixed, and both halves now pinned to the source CSV by new `PAPER_CLAIMS` guards. |
| 8 | D1C is committed but unmerged | **Open by instruction, not by oversight.** `research/d1c-propf1-propagation` is 3 commits ahead of `master` (`82af136`, `e3faead`, `a637d38`) and **not pushed**. The registration brief ended "commit on the branch, then stop", so pushing and merging is the author's call. Build clean, 115 tests green on the branch. |
| 9 | T4 — a separation theorem for the stability partition | **Open, and now the last live theory direction.** D1B closed the switching route; D1C emptied Prop F.1's analytical discharge. T4 — conditions on the scale process under which bounded scale-free methods provably beat scale-dependent ones — is the one remaining route to a non-vacuous theory contribution, and nothing measured so far obstructs it. The partition it would explain (0/10 vs 9/10 per-row, replicated on crypto with frozen hyperparameters) is still the sharpest unexplained empirical result in the paper. The candidate reframe in `research_state.md` Session 14 is gated on this and is **not** to be acted on first. |
| 10 | One badness-10000 appendix page (p18) | **Open, low severity, and mine.** New since D1C — established by building `master`'s tex in a scratch tree, where the worst underfull vbox is 6893. It is a page-breaking consequence of D1C's appendix paragraph, **appendix-only**: main text is unchanged at 8.942pp and the build has 0 overfull, 0 undefined. The obvious one-line fix does not work — relaxing `fig:iternorm` from `[t]` to `[htbp]` produces a **byte-identical** PDF, so that float is not the cause. Left rather than chased, because a page-breaking hunt is a typesetting project D1C's scope did not cover. |
| 11 | `PAPER_CLAIMS` coverage is built row by row, and the gaps are where drift lives | **Open, and worth a session on its own.** Three separate findings now trace to the same cause: C-18's `app:tracker` figures drifted two sessions because no guard covered the per-row numbers; T4 found **neither** `tab:jane` scale-dependent row guarded; and the clipper row's provenance error survived every audit pass. Guards have been added one row at a time, reactively, each time after something drifted. The useful version is a coverage *audit* — enumerate every number the paper prints, mark which are pinned to a CSV cell, and close the set — rather than another single row. |
| 12 | ~~A recurring failure class: boundary artifacts that print a confident verdict~~ | **Closed 2026-08-27 by a gate, after four occurrences.** `scripts/research_grid_interior.py` + `tests/test_grid_interior.py` audit every grid-based claim in a declared registry for two distinct failures — an optimum at a grid edge, and a ceiling the sweep never brackets — reading committed bytes only, so it runs in a data-less checkout in about a second. An edge is not automatically a bug; an *undeclared* edge is, on `PAPER_CLAIMS`' principle. Five declarations so far, each with its reason. Verified the gate can fail. `--survey` maps all 40 artifacts carrying a grid axis. Original note follows. **It had happened twice when this was filed, and twice more within the same session.** §E.12's grid-adequacy work found optima sitting at a grid edge, where the reported optimum is an artifact of where the sweep stopped. T4's step 2 hit the same shape: normalized-GD never diverges on the committed grid, so its ceiling is right-censored, and the uncorrected code would have printed a `1.88×` spread and a **FALSIFIED** verdict that was purely an artifact of the grid ending. Caught both times, but only by looking. The class is: *a statistic computed at the edge of a swept range, reported as if the range were the domain.* Worth a standing check in any script that reports an extremum or a threshold over a grid. |
| 13 | Venue: is ICLR 2027 still the right target? | **Open decision for the author; raised 2026-08-27 and never examined before.** This tracker has carried "ICLR 2027" as settled since the venue moved, and the work has changed underneath it: four registered theory directions, all closed, three with *measured* obstructions, plus a taxonomy correction and a rigorous measurement study. That is good work poorly shaped for a main-track slot optimising for novelty, and well shaped for a venue where the measurement or the negative result is the contribution. Not a recommendation — a decision that should be made deliberately rather than by default. |


### The two GitHub identities, and the misleading error they produce

This cost several rounds and will cost more later, so it is written down.

**There are two GitHub accounts in play on this machine, and they are not the same one.**

| | account | on `rafli-hl/dfsl` |
|---|---|---|
| `git` (Windows Credential Manager) | **`rafli-hl`** | writes fine — pushed branches, tags and four PR merges |
| `gh` CLI (keyring) | **`rafli07p`** | `{"admin":false,"maintain":false,"pull":true,"push":false,"triage":false}` |

Because git works, everything git-shaped succeeded and nothing hinted at a problem. Every
`gh` **write** fails, and the errors do not name the cause:

- `gh pr create` → `must be a collaborator` (accurate, but does not say which account)
- `gh release create` → `"workflow" scope may be required` — **wrong**. That token already
  carries `workflow`; the real cause is `push: false`. Following the error's own advice
  (`gh auth refresh -s workflow`) would not have fixed it.

An earlier version of open item 4 recorded `viewerPermission: READ` as a hard blocker and
was corrected to "the permission half was wrong" once the push succeeded. Both statements
were half right and neither named the split: the *permission* claim was true of `gh`'s
token and false of git's.

**The fix is one command**, which re-points `gh` at the credential git already uses:

```
printf "protocol=https\nhost=github.com\n\n" | git credential fill \
  | sed -n 's/^password=//p' | gh auth login --hostname github.com --with-token
```

Afterwards `gh auth switch --user rafli07p` restores the old account if it is wanted for
other work, and the GCM token's scopes are worth checking — they may be narrower than the
`gist, read:org, repo, workflow` the current one carries.

Until then, `gh` reads work and `gh` writes do not. PRs #8–#11 were created by passing the
git credential explicitly, which is why they succeeded where the plain command failed.

### Finding 10, measured: the block-length objection does not reproduce

The audit expected a one-day block to be too short for the dependence and therefore to
*understate* the standard errors in `tab:jane`. Re-bootstrapping every row at its own tuned
setting with blocks of 1, 3, 5 and 10 trading days (`research_block_length.py`,
`block_length_sensitivity.csv`) says otherwise, in two parts.

At the three-day block the audit itself proposed, the standard errors do not move — ratios
**0.88–1.18** across all twelve series. So at that scale the one-day block is not
understating them.

Past three days they **shrink**, and that is an artifact rather than a result. The slice is
20 trading days, so a three-day block leaves 7 blocks per resample and a ten-day block
leaves 2; a moving-block bootstrap assembled from a handful of long contiguous stretches
collapses toward the original series, and its spread goes to zero. Those columns measure the
record length, not the dependence. Settling the question at longer horizons needs a longer
slice, and that limitation is now stated in the paper rather than left implicit.

Every reading the paper takes from `tab:jane` survives at every block length tried: the
per-step SN-OMD/normalized-GD intervals overlap throughout, SN-OMD and AdaGrad-Norm overlap
per-row throughout, and the separation from scale-dependent OGD is disjoint throughout. And
the accuracy claims do not rest on this bootstrap in the first place — they rest on the
paired across-window bootstrap over ten frozen windows, which resamples at a granularity
that absorbs within-window dependence outright.


### The timing run doubled as a full reproduction, and found one trap

Timing the suite meant re-running every script, which regenerates every artifact -- so the
`git status` afterwards is a reproduction report. Reading it:

**The heavy tables reproduce exactly.** `research_c12_matched_table.py` and
`research_c12b_blockmed.py` -- 37 and 50 minutes, together half the suite, and the source of
`tab:replication` -- came back with `repro_gate_pass: true` and identical tuned
configurations and R^2 values. The only fields that moved were wall-clock timings.
`tracker_a1.csv` was identical. `synthetic_regret.csv` differed in the sixteenth
significant digit (max relative difference `6.6e-15`), which is floating-point reduction
order, not a change.

**One artifact came back different, and the fault was in the instruction.**
`iterate_norm.csv` changed substantially: SN-OMD's peak `||w||` read `6.63` where
`app:iternorm` reports `40.6`. The cause is that `research_iterate_norm.py` defaults to
`--lr 2` while the appendix reports the run at the shared competitive rate `eta=8`, and the
suite ran every script bare. Re-running it with `--lr 8` reproduces the committed CSV
**byte-for-byte** -- peak `40.6`, final `1.78`, `0/150000` envelope breaches, log-log
exponent `-0.307` -- so the measurement was never in doubt.

What was wrong is that the paper named the script without the flag, so a reviewer following
it would have run a different experiment and silently overwritten the artifact with it. The
paper now names `research_iterate_norm.py --lr 8`, the tracker's reproducing list carries
the flag with a warning that it is not the default, and `research_runtime_suite.py` holds an
`ARGS` table so the suite reproduces the paper's configuration rather than each script's
own defaults. Of the 29 scripts this is the only one whose defaults disagree with the
paper; the rest were checked.

Every regenerated artifact was restored to its committed state, so the tree still holds
exactly what the paper was built from.

**Decided, not open.** RMSProp/Adam do *not* get ten-window rows — the schedule control
is a single window at each method's own tuned rate, and `app:adaptive` says so. Whether
to add a non-finance result is a scope decision, deferred deliberately.

---

### Release: what is staged, and the one step left

`iclr2027-phase2` is an **annotated** tag at `a0f1516`, pushed to `origin`. Its message
records the Phase-2 result, the five directions that failed or came back void, the
publication pass, and the closed open items.

Prepared and checked, waiting on the auth fix above:

| piece | state |
|---|---|
| Tag | `iclr2027-phase2` → `a0f1516`, annotated, pushed |
| Notes | Markdown release notes written (`--notes-from-tag` is the fallback, so the notes file is not load-bearing) |
| PDF asset | `paper/iclr2027/iclr2027.pdf` — **0 identity tokens** in the extracted text, `/Author` and `/Title` metadata **empty**, only MiKTeX's producer string. The three "ICML" hits are bibliography venue names (Cutkosky 2020, Daniely 2015, Zinkevich 2003), not prior-venue self-disclosure. 29pp, newer than the `.tex`, working tree clean at `a0f1516` — so the asset corresponded exactly to the tagged tree **when this was written**. ⚠ **No longer true as of 2026-08-26**: see the staleness note below the command |

The command, once `gh` is authenticated as `rafli-hl`:

```
gh release create iclr2027-phase2 --repo rafli-hl/dfsl \
  --title "Phase-2 research, the corrected table, and the publication pass" \
  --notes-from-tag --verify-tag \
  "paper/iclr2027/iclr2027.pdf#SN-OMD paper (29pp, main text 8.907pp)"
```

⚠ **This command has gone stale and must not be run as written.** It attaches the PDF from the *working tree*, not from the tag. C13, D1B and D1C have since landed, so the working-tree PDF is **31pp, main text 8.942pp** — it would be uploaded under a label saying 29pp/8.907, against a tag at `a0f1516` that contains neither. Two coherent ways out, and the choice is the author's:

1. **Release the tagged state.** Build the PDF from `a0f1516` into a scratch tree and attach *that*, leaving the label as written. Keeps the tag's meaning intact.
2. **Cut a new tag.** Tag the current head, write fresh notes covering Phase 3, and update the label to `31pp, main text 8.942pp`. This is the better option if the release is meant to represent where the work now stands rather than where it stood on 2026-08-25 — but it should wait until open item 8 is decided, since D1C is not yet in `master`.

**Why the manuscript being public is not a new exposure.** `paper/iclr2027/iclr2027.tex`
was already on the public `origin/master` before any of this, as were `paper/icml2026.tex`
and its PDF. The push updated a manuscript that was already there. A *tagged release* is
still a publicising act in a way a branch push is not, which is why it was put to the
author rather than done silently.

## Reproducing

```
python scripts/research_predictability_check.py   # the 2x2 decomposition
python scripts/research_batched_check.py          # tab:jane, tab:replication
python scripts/research_tracker_bootstrap.py      # app:tracker + Bonferroni
python scripts/research_rmsprop_adam.py           # app:adaptive
python -m pytest -q                               # 115 tests (needs .venv; a bare python fails on `dfsl`)
python scripts/make_anon_release.py               # double-blind supplement (336 files)
python scripts/research_iterate_norm.py --lr 8   # fig:iternorm -- the flag is NOT the default
python scripts/research_runtime_suite.py          # wall-clock for the whole suite
python scripts/research_block_length.py           # bootstrap block-length sensitivity
python scripts/research_jane_mini.py --build --run   # the Jane path with no market data
python scripts/research_jane_mini.py --verify        # hash-check a real Kaggle download
```

Phase-2 research (preregistered in `experiment_matrix.yaml`; merged to `master`, the branch is deleted):

```
python scripts/research_c10_budget_match.py       # C10/Q6  matched-budget ten windows
python scripts/research_c10m_binding.py           # C10M    clip-binding mechanism
python scripts/research_c10s_threshold.py         # C10S    stability threshold
python scripts/research_c10r_realized.py          # C10R    realized max step (crypto)
python scripts/research_c10t_synthetic.py         # C10T    same, synthetic
python scripts/research_c10c3_validate.py         # C10C3   divergence-criterion acceptance
```

Phase-3 research (same registration discipline; C13 and D1B are on `master`, D1C is on `research/d1c-propf1-propagation`):

```
python scripts/research_c13_matched_bootstrap.py  # C13  app:tracker at matched budget
python scripts/research_d1b_regime_count.py       # D1B  the regime count N(T)
python scripts/research_d1c_propf1.py             # D1C  Prop F.1's domination condition
```

60 scripts, 111 result CSVs, 10 figures.
`tests/test_preprocessing.py::test_step_is_predictable` pins the library tracker's
measurability — it is what kept `dfsl.preprocessing` correct while the research scripts
drifted away from it.

---

## Submission checklist

- [x] Main text within 9pp (**8.942**, ~0.06pp margin — 3 lines)
- [x] 0 undefined refs, 0 overfull, clean build (one appendix-only badness-10000 page, open item 10)
- [x] Tests pass (115)
- [x] Tables regenerated from corrected code
- [x] Anonymized supplement builds, 0 identity tokens (336 files, 2026-08-25)
- [x] ICLR PDF gitignored, so metadata cannot leak into the supplement
- [x] Prior-venue material excluded from the supplement — exclusion glob repaired 2026-08-24 after the `paper/` move silently un-matched it; pinned by `tests/test_anon_exclusions.py`
- [x] Tag on the submission commit (`c32db71`) — deliberately NOT moved onto the research branch
- [x] Wall-clock runtime disclosed — ~3 h for the whole suite, ~3 min for the Kaggle-free part
- [x] §4 schedule sentence — decided: it goes in **Limitations**, not §4
- [x] `tab:replication` re-run at matched budget — corrected artifact in `results/research/c12/`
- [x] Corrected `tab:replication` adopted (`de33ee0`), and every statement it invalidated repaired
- [x] Publication-quality pass §4–§19 — introduction, abstract, contributions, paragraph structure, terminology, captions, cross-references, bibliography (below)
- [x] Publication-quality pass §8–§10 — the two formal statements, the tracker paragraph, Related Work
- [x] §26 appendix QA page by page — experiments promoted out of "Proofs", one wrong cross-reference, two colliding headings, five mis-parked floats
- [x] Audit finding 10 — bootstrap block-length sensitivity measured; the objection does not reproduce
- [x] Audit finding 6 — a data-free Jane path ships (`research_jane_mini.py`), plus a sha256 pin on the real slice
- [x] Audit finding 3 residual — the SE claim names both comparators and is pinned to its CSV by two new guards
- [x] Phase-2 research merged to `master` (PRs #8–#11); branches cleaned up, one branch remains
- [x] `iclr2027-phase2` tag pushed at `a0f1516`; `iclr2027-submission` deliberately left where it is
- [x] Phase-3 revision-assessment actions — the three consistency regressions the assessment named are fixed, and the paired bootstrap re-run at matched budget (C13)
- [x] D1B — Remark D.3's switching bound closed *negatively*, five "left open" sites corrected, Limitations concession added
- [x] D1C — Prop F.1's discharge measured empty on this data; three claim sites revised without spending a line of the page budget
- [ ] D1C branch pushed and merged — deliberately not done; the registration ended "commit, then stop" (open item 8)
- [ ] T4 — the last live theory direction, not yet registered (open item 9)
- [ ] GitHub release published — staged, blocked on the `gh` identity, **and the staged command is now stale** (see above)
- [ ] `gh` CLI authenticated as `rafli-hl` rather than `rafli07p`
