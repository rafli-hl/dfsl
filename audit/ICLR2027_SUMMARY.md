# ICLR 2027 — SN-OMD submission status

Progress tracker for the SN-OMD paper targeting **ICLR 2027**. Detail on individual
fixes lives in [`ICLR2027_REMEDIATION_LOG.md`](ICLR2027_REMEDIATION_LOG.md); this file
is the top-level view: where the paper stands, what is settled, what is still open.

Last verified: **2026-08-24**, commit `a506251` (branch `research/c10-q6`).

---

## At a glance

| | |
|---|---|
| Branch | `research/c10-q6`, **26 commits ahead of `origin/master`** (Phase-2 research; unmerged, unpushed) |
| Pass V commits | `202d983`..`c32db71` — paper-claim guard, `references.bib` deletion, OMD/OGD naming, supplement exclusions, `out/` untrack |
| Phase-2 research | `142a075`..`a506251` — eight preregistered directions, C10/Q6 through C10C3. See **Phase 2** below |
| `master` | `212d32c`, the PR #7 merge — **contains all Pass V work**. Phase-2 research is not on it |
| Tag | `iclr2027-submission` → `c32db71` (annotated object `347bcb1`). Marks the **submission** state; deliberately not moved onto the research branch |
| Canonical source | `paper/iclr2027/iclr2027.tex` (1841 lines) |
| Main text | **8.878pp** of a 9pp limit (re-measured from the PDF 2026-08-23: 8.88–8.90pp, ~0.1pp headroom) |
| Total | 28pp (statements, references, appendix do not count) |
| Build | 0 undefined refs, 0 overfull >10pt, 0 stray tabs |
| Tests | **104 passed** (84 + 20 anon-exclusion guards) |
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
| The cap `M` interpolates normalized-GD ↔ scale-adaptive OGD | M-sweep, optimum at `M=5` | `jane_msweep.csv` — **⚠ the sweep is at a single `lr=0.5`, not joint; at matched budget `M=2` wins (Phase 2)** |
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

## Open items

| # | Item | Blocked on |
|---|---|---|
| 1 | `tab:replication` rests on a confounded comparison. **A corrected artifact now exists** (C12, `results/research/c12/`): SN-OMD 0.1398 → 0.2359 per-row, 4th → 1st; every other row unchanged to 4 d.p.; reproduction gate 0.000000 on all ten checks; divergence partition unchanged. | Author decision only: adopt the regenerated table (and relabel the row `M` tuned), or narrow the claim. No longer blocked on measurement. |
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
python -m pytest -q                               # 104 tests
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

- [x] Main text within 9pp (8.878)
- [x] 0 undefined refs, clean build
- [x] Tests pass (104)
- [x] Tables regenerated from corrected code
- [x] Anonymized supplement builds, 0 identity tokens (307 files, 2026-08-24)
- [x] ICLR PDF gitignored, so metadata cannot leak into the supplement
- [x] Prior-venue material excluded from the supplement — exclusion glob repaired 2026-08-24 after the `paper/` move silently un-matched it; pinned by `tests/test_anon_exclusions.py`
- [x] Tag on the submission commit (`c32db71`) — deliberately NOT moved onto the research branch
- [ ] Wall-clock runtime disclosed
- [ ] §4 schedule sentence — decide
- [x] `tab:replication` re-run at matched budget — corrected artifact in `results/research/c12/`
- [ ] **Adopt the corrected `tab:replication`, or narrow the claim** — author decision (open item 1)
