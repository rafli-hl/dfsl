# ICLR 2027 — SN-OMD submission status

Progress tracker for the SN-OMD paper targeting **ICLR 2027**. Detail on individual
fixes lives in [`ICLR2027_REMEDIATION_LOG.md`](ICLR2027_REMEDIATION_LOG.md); this file
is the top-level view: where the paper stands, what is settled, what is still open.

Last verified: **2026-08-23**, at `c32db71` (tagged `iclr2027-submission`).

---

## At a glance

| | |
|---|---|
| Branch | `paper-submission` (68 commits), in sync with `origin/paper-submission` |
| Pass V commits | `202d983`..`c32db71` — paper-claim guard, `references.bib` deletion, OMD/OGD naming, supplement exclusions, `out/` untrack |
| `master` | At the PR #6 merge (`df25bc3`), which is **pre-Pass-V** — the Pass V commits are on `paper-submission` only, pending a new PR |
| Tag | `iclr2027-submission` → `c32db71` (annotated object `347bcb1`), force-moved off `1cfdfaa` and pushed |
| Canonical source | `paper/iclr2027/iclr2027.tex` (1841 lines) |
| Main text | **8.878pp** of a 9pp limit (re-measured from the PDF 2026-08-23: 8.88–8.90pp, ~0.1pp headroom) |
| Total | 28pp (statements, references, appendix do not count) |
| Build | 0 undefined refs, 0 overfull >10pt, 0 stray tabs |
| Tests | **84 passed** |
| Anon supplement | 246 files, 0 identity tokens, rebuilt at `D:\dfsl-anon-release` |

`paper/icml2026.tex` is a **frozen ICML snapshot**. It is not back-synced, and it is
excluded from the anonymized supplement.

---

## The claim structure

What the paper argues, and where each piece is measured:

| Claim | Evidence | Artifact |
|---|---|---|
| Gradient heavy tails are a *predictable-scale artifact*, not intrinsic | pooled vs. normalized separation on Jane; interaction effect heavier than either factor alone | `fig:problem` |
| Normalize by a predictable scale, then cap → bounded iterates | `thm:stability` (Prop. 3.1), measured √t envelope | `app:iternorm` |
| Dynamic regret under a drifting scale, high probability | `thm:regret` (Thm. D.2), restated as `thm:regretbody` | proofs, App. D |
| The cap `M` interpolates normalized-GD ↔ scale-adaptive OGD | M-sweep, optimum at `M=5` | `jane_msweep.csv` |
| Stability is not unique to SN-OMD, but the *predictable* scale is | ten frozen windows, divergence partition | `tab:replication` |
| The tracker is a documented choice, not a free win | block-median co-leads per-row; ties Cutkosky–Mehta | `app:tracker` |
| RMSProp/Adam do **not** diverge — they are bounded-step | run head-to-head, not argued | `app:adaptive` |

**Headline numbers.** Per-row weighted R² on window 1: SN-OMD `0.285±.080`, per-step
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

## Open items

| # | Item | Blocked on |
|---|---|---|
| 1 | Wall-clock runtime figure for the Reproducibility Statement | A timed full-suite run over the Jane parquet. Open across four rounds. |
| 2 | §4 sentence noting the deployed anytime schedule is not the more accurate one | Author decision. The gate (a decomposition giving trustworthy numbers) is satisfied; the investigation showed the gap was grid-tuning, so if this goes in it stands on the schedule argument alone — not automatic. |
| 3 | GitHub release | `gh` authenticated as `rafli07p`, repo owner is `rafli-hl`. |
| 4 | Audit finding 10 — bootstrap block-length sensitivity | A re-run of the block bootstrap at 3-day and 5-day blocks. Compute, not a text fix. |
| 5 | Audit finding 6 — Jane numbers not reviewer-reproducible | Partly mitigated (crypto auto-downloads, synthetic suite is data-free); a seeded Jane mini-slice is still not shipped. |
| 6 | Audit finding 3 residual — the "$3\times$" SE claim names no comparator | Author call: ~3.3x against the family's tightest per-row SE, 2.2x against normalized-GD, and per-step SN-OMD's SE is *lower* than normalized-GD's. |

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
python -m pytest -q                               # 84 tests
python scripts/make_anon_release.py               # double-blind supplement
```

43 scripts, 50 result CSVs, 10 figures.
`tests/test_preprocessing.py::test_step_is_predictable` pins the library tracker's
measurability — it is what kept `dfsl.preprocessing` correct while the research scripts
drifted away from it.

---

## Submission checklist

- [x] Main text within 9pp (8.878)
- [x] 0 undefined refs, clean build
- [x] Tests pass (84)
- [x] Tables regenerated from corrected code
- [x] Anonymized supplement builds, 0 identity tokens
- [x] ICLR PDF gitignored, so metadata cannot leak into the supplement
- [x] Prior-venue material excluded from the supplement
- [x] Tag on the current commit
- [ ] Wall-clock runtime disclosed
- [ ] §4 schedule sentence — decide
