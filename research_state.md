# Research state

**This file is new as of 2026-08-23.** The Phase-1 `research_state.md` referenced by the
Phase-2 brief — including its §17 candidate ranking — is absent from this repository and
`git log --all` confirms it was never committed here. Neither were `RESEARCH_CHARTER.md`,
`claim_ledger.md`, or any `results/research/r1_*` artifact. This file records state from
the first Phase-2 session that ran in this repository, and does not reconstruct Phase 1.

## Environment (verified 2026-08-23)

- Branch `research/c10-q6`, cut from `paper-submission` at `e66768d`.
- Jane data **present**: `data/raw/jane/` is 12 GB of hive-partitioned parquet
  (`train.parquet/partition_id=0..9`), not a single file. Loads in ~0.8 s per
  150 000-row window.
- Test suite: **84 passed** in `.venv`. A bare `python -m pytest` fails with
  `ModuleNotFoundError: dfsl` — the project venv is required.
- Compute: 12 cores, 43 GB free disk, single-process foreground runs.

## Session 1 — direction C10/Q6 (complete)

**Question.** On the ten-window benchmark a constant scale (fixed-tau clip) beat the
predictable tracked scale the method is built on. Property of the scale process, or
artifact of tuning budget?

**Selection rationale.** C10/Q6 was chosen over T1, T4 and E2 because it could falsify a
central premise rather than confirm one, and because the phenomenon was already present
in committed artifacts so no new measurement was needed to motivate it. R1c was excluded
as not actionable: no `r1_*` artifact exists in this repository.

**Result.** H1 survived, decisively — `fraction_closed = 1.32` against a registered
threshold of 0.50, per-row. The gap did not merely close, it reversed: at matched budget
SN-OMD 0.2270 vs fixed-tau 0.2020 held-out, winning 9/9 held-out windows and 10/10
overall. Full write-up: `results/research/c10/r_c10_summary.md`. Ledger: `claim_ledger.md`
C-1 through C-6.

**Key structural fact established.** The two methods are one algorithm. Update magnitude
is `(lr/sqrt(k))*min(||g||, tau)` for fixed-tau clip and `(lr/sqrt(k))*min(||g||/s_t, M)`
for SN-OMD, so SN-OMD with a constant scale `s0` is exactly fixed-tau clip with
`tau = M*s0`, `lr' = lr/s0`. The family differs in one place only: whether the clip
threshold is constant or tracks a predictable scale. Any comparison between them is a
comparison of scale processes **only** at matched budget over `(lr, threshold)`.

**Defect found and fixed.** `research_windows_replication._grid` gave the baseline a joint
2-D grid and the proposal a 1-D grid with the cap pinned at a value selected in a separate
sweep at a different learning rate. This is a fairness defect in the baseline's favour.
The published SN-OMD ten-window figures are the under-tuned ones.

## What is now open

1. **Mechanism (successor to C10/Q6).** Why does `M=2` at `lr=3` transfer across windows
   when `M=5` at `lr=2` does not? Clip-binding frequency is the obvious first probe. It
   was deliberately not run this session — it was not preregistered, and running it after
   seeing the result would be post hoc.
2. **Rolling-origin selection.** Every transfer claim here rests on one selection window.
   Whether the ordering survives a different choice of selection window is untested and is
   the single most load-bearing threat to the result.
3. **Per-step grid adequacy.** The matched per-step arm selected at two grid edges
   (`lr=8.0`, `M=0.5`); its optimum is unresolved. A widened per-step grid would be a
   separate, explicitly post-hoc run.
4. **Re-run the full ten-window table at matched budget.** Only three arms were re-run.
   Normalized-GD, AdaGrad-Norm, OGD and the uncapped endpoint were not, and their
   published tuning budgets have not been audited.

## Directions not taken

- **T1** (variation-adaptive dynamic-regret bound) and **T4** (formal separation for
  bounded scale-free methods) — both untouched, both still the only routes to a
  non-vacuous theorem.
- **E2** (synthetic phase diagram) — untouched; still the cheapest route to a
  "when does this help" boundary, and data-free, hence reviewer-reproducible.
- **R1c** — not actionable in this repository.
