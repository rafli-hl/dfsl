# ICLR 2027 — SN-OMD submission status

Progress tracker for the SN-OMD paper targeting **ICLR 2027**. Detail on individual
fixes lives in [`ICLR2027_REMEDIATION_LOG.md`](ICLR2027_REMEDIATION_LOG.md); this file
is the top-level view: where the paper stands, what is settled, what is still open.

Last verified: **2026-08-24**, commit `b44999d` (branch `research/c10-q6`).

---

## At a glance

| | |
|---|---|
| Branch | `research/c10-q6`, **48 commits ahead of `origin/master`** (Phase-2 research; unmerged, unpushed) |
| Pass V commits | `202d983`..`c32db71` — paper-claim guard, `references.bib` deletion, OMD/OGD naming, supplement exclusions, `out/` untrack |
| Phase-2 research | `142a075`..`a506251` — eight preregistered directions, C10/Q6 through C10C3. See **Phase 2** below |
| `master` | `212d32c`, the PR #7 merge — **contains all Pass V work**. Phase-2 research is not on it |
| Tag | `iclr2027-submission` → `c32db71` (annotated object `347bcb1`). Marks the **submission** state; deliberately not moved onto the research branch |
| Canonical source | `paper/iclr2027/iclr2027.tex` (1913 lines) |
| Main text | **8.871pp** of a 9pp limit, ~0.13pp (7 lines) of margin. Trajectory: 8.885 pre-adoption → 9.007 (matched-budget table adopted) → 8.615 (appendix relocation) → 9.007 (`fig:problem` promoted) → 8.502 (`fig:main` demoted) → 8.720 (publication pass §4–19, §21–23) → **8.871** (§8–10) |
| Total | 29pp (statements, references, appendix do not count) |
| Build | 0 undefined refs, 0 overfull, 0 float-specifier warnings, 0 stray tabs. 6 underfull boxes, all float slack or one badness-1342 proof line — the two badness-10000 bibliography lines are fixed |
| Tests | **106 passed** (84 + 20 anon-exclusion guards + 2 `tab:replication` mean guards) |
| Anon supplement | 307 files, 0 identity tokens, rebuilt at `D:\dfsl-anon-release` (2026-08-24) |

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
| Stability is not unique to SN-OMD, but the *predictable* scale is | ten frozen windows, divergence partition | `tab:replication` — **⚠ confounded by unequal tuning budget; the ordering reverses when equalized (Phase 2)** |
| The tracker is a documented choice, not a free win | block-median co-leads per-row; ties Cutkosky–Mehta | `app:tracker` |
| RMSProp/Adam do **not** diverge — they are bounded-step | run head-to-head, not argued | `app:adaptive` |

**Headline numbers.** ⚠ The ten-window SN-OMD figure below is the **under-tuned** one; see Phase 2.
Per-row weighted R² on window 1: SN-OMD `0.285±.080`, per-step
`0.307±.059`. Ten-window frozen: SN-OMD `0.14±.11` (0/10 divergences), block-median
tracker `0.29±.07`, Cutkosky–Mehta `0.29±.04`. Stability partition on crypto: OGD
diverges `10/10`, uncapped endpoint `3/10`, every bounded scale-free method `0/10`.

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
state in `research_state.md`. **None of this is merged, and no manuscript text was touched
— that was out of scope for the phase.**

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

## Open items

| # | Item | Blocked on |
|---|---|---|
| 1 | ~~`tab:replication` rests on a confounded comparison.~~ **Closed 2026-08-24** — corrected table adopted at `de33ee0`, and the four appendix statements it invalidated repaired in the same working tree (below). | — |
| 2 | Wall-clock runtime figure for the Reproducibility Statement | A timed full-suite run over the Jane parquet. Open across four rounds. |
| 3 | §4 sentence noting the deployed anytime schedule is not the more accurate one | Author decision. The gate (a decomposition giving trustworthy numbers) is satisfied; the investigation showed the gap was grid-tuning, so if this goes in it stands on the schedule argument alone — not automatic. |
| 4 | GitHub release | `gh` authenticated as `rafli07p`, repo owner is `rafli-hl`. |
| 5 | Audit finding 10 — bootstrap block-length sensitivity | A re-run of the block bootstrap at 3-day and 5-day blocks. Compute, not a text fix. |
| 6 | Audit finding 6 — Jane numbers not reviewer-reproducible | Partly mitigated (crypto auto-downloads, synthetic suite is data-free); a seeded Jane mini-slice is still not shipped. |
| 7 | Audit finding 3 residual — the "$3\times$" SE claim names no comparator | Author call: ~3.3x against the family's tightest per-row SE, 2.2x against normalized-GD, and per-step SN-OMD's SE is *lower* than normalized-GD's. |

**Decided, not open.** RMSProp/Adam do *not* get ten-window rows — the schedule control
is a single window at each method's own tuned rate, and `app:adaptive` says so. Whether
to add a non-finance result is a scope decision, deferred deliberately.

---

## Reproducing

```
python scripts/research_predictability_check.py   # the 2x2 decomposition
python scripts/research_batched_check.py          # tab:jane, tab:replication
python scripts/research_tracker_bootstrap.py      # app:tracker + Bonferroni
python scripts/research_rmsprop_adam.py           # app:adaptive
python -m pytest -q                               # 106 tests
python scripts/make_anon_release.py               # double-blind supplement (307 files)
```

Phase-2 research (branch `research/c10-q6`, preregistered in `experiment_matrix.yaml`):

```
python scripts/research_c10_budget_match.py       # C10/Q6  matched-budget ten windows
python scripts/research_c10m_binding.py           # C10M    clip-binding mechanism
python scripts/research_c10s_threshold.py         # C10S    stability threshold
python scripts/research_c10r_realized.py          # C10R    realized max step (crypto)
python scripts/research_c10t_synthetic.py         # C10T    same, synthetic
python scripts/research_c10c3_validate.py         # C10C3   divergence-criterion acceptance
```

43 scripts, 50 result CSVs, 10 figures.
`tests/test_preprocessing.py::test_step_is_predictable` pins the library tracker's
measurability — it is what kept `dfsl.preprocessing` correct while the research scripts
drifted away from it.

---

## Submission checklist

- [x] Main text within 9pp (8.502, ~0.50pp margin)
- [x] 0 undefined refs, 0 overfull, clean build
- [x] Tests pass (106)
- [x] Tables regenerated from corrected code
- [x] Anonymized supplement builds, 0 identity tokens (307 files, 2026-08-24)
- [x] ICLR PDF gitignored, so metadata cannot leak into the supplement
- [x] Prior-venue material excluded from the supplement — exclusion glob repaired 2026-08-24 after the `paper/` move silently un-matched it; pinned by `tests/test_anon_exclusions.py`
- [x] Tag on the submission commit (`c32db71`) — deliberately NOT moved onto the research branch
- [ ] Wall-clock runtime disclosed
- [ ] §4 schedule sentence — decide
- [x] `tab:replication` re-run at matched budget — corrected artifact in `results/research/c12/`
- [x] Corrected `tab:replication` adopted (`de33ee0`), and every statement it invalidated repaired
- [x] Publication-quality pass §4–§19 — introduction, abstract, contributions, paragraph structure, terminology, captions, cross-references, bibliography (below)
- [x] Publication-quality pass §8–§10 — the two formal statements, the tracker paragraph, Related Work
- [x] §26 appendix QA page by page — experiments promoted out of "Proofs", one wrong cross-reference, two colliding headings, five mis-parked floats
