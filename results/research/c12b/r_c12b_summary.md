# C12B — matched budget is not a free win: it *hurts* block-median per-row

Direction C12B, `kind: ARTIFACT_REGENERATION`. Registered at `5e71842`, script committed before
the run. 2026-08-24, 867 s. Artifacts: `c12b_blockmed.csv`, `c12b_summary.csv`, `c12b_report.json`.

## Reproduction gate — passed

| protocol | published arm, re-run | manuscript row | diff |
|---|---|---|---|
| per-row | **+0.2913** | 0.29 | 0.0013 |
| per-step | **+0.2012** | 0.20 | 0.0012 |

The harness reproduces the manuscript's block-median row, so the comparison below is sound.

## Result

| protocol | arm | setting | all-10 | std | min | held-out | window 1 |
|---|---|---|---|---|---|---|---|
| per-row | published | `lr=3, M=5` | **+0.2913** | 0.0678 | +0.1991 | **+0.2785** | +0.4067 |
| per-row | matched | `lr=3, M=10` | +0.2817 | 0.0851 | +0.1687 | +0.2657 | +0.4255 |
| per-step | published | `lr=2, M=5` | +0.2012 | 0.1255 | +0.0069 | +0.1845 | +0.3511 |
| per-step | matched | `lr=3, M=2` | **+0.2420** | 0.1087 | +0.0952 | **+0.2246** | +0.3983 |

**Per-row, matched budget makes block-median worse.** The wider search selects `M=10`, which
wins window 1 (+0.4255 vs +0.4067) and then *loses* held-out (+0.2657 vs +0.2785). That is
textbook selection overfitting: the extra search dimension bought in-sample fit and paid for it
out of sample.

**Per-step, matched budget helps**, and substantially: +0.2012 → +0.2420 all-ten,
+0.1845 → +0.2246 held-out, with dispersion down (0.1255 → 0.1087) and the worst window up
(+0.0069 → +0.0952).

Divergence is 0/10 under both criteria in every cell — the registered surprise (count moving
off 0/10) did not occur. Nor did the other: `M` selected 10 and 2, both interior.

## Why this matters beyond the table

**The matched-budget correction is not uniformly favourable, and should not be presented as
one.** C12 showed it lifting plain SN-OMD per-row by +0.0961; here it costs block-median
−0.0128 held-out per-row while gaining +0.0401 held-out per-step. The fix removes a *defect in
the comparison*; it does not reliably improve the method it was applied to.

This also sharpens the threat that has been standing since C10/Q6: **every one of these
selections rests on a single window.** Block-median per-row is now a concrete instance of that
threat biting — more search, better window 1, worse held-out. A rolling-origin protocol remains
the most load-bearing untested assumption in this line of work.

## Consequence for `tab:replication`

Adopting consistently (both SN-OMD rows at matched budget, CM untouched):

| method (per-row) | published | adopted |
|---|---|---|
| Cutkosky–Mehta | **0.29** | **0.29** (unchanged, 216-config 3-parameter grid is legitimate) |
| SN-OMD + block-median | **0.29** | **0.28** |
| SN-OMD (`M` tuned) | 0.14 | **0.24** |
| fixed-τ clip | 0.21 | 0.21 |
| AdaGrad-Norm | 0.20 | 0.20 |
| Normalized-GD | 0.18 | 0.18 |

**The paper's honest headline claim is unaffected.** Block-median SN-OMD at 0.28 against CM at
0.29 still *ties rather than beats* — which is exactly what the abstract already says. The
correction removes a defect without turning this into an accuracy win, and the abstract's
closing sentence stands as written.

Per-step, the ordering does change: block-median rises to 0.24, ahead of SN-OMD 0.21 and
fixed-τ 0.20, so the bolding in that half of the table would move.

## Threats to validity

1. **Single selection window** — now demonstrated to bite, not merely hypothesized (above).
2. **`B` held pinned by design** (10 000 per-row, 818 per-step), as the analogue of the EMA's
   pinned decay and winsorization. Tuning it is a different experiment.
3. **`lr` grids differ slightly between rows** (block-median's own 9 values against the plain
   row's 10); each row keeps its published grid so that the cap is the only change.
4. **One dataset, one preprocessing path**, as throughout.

## What this does NOT establish

- Not that block-median is worse than published — the *published* per-row number stands and is
  reproduced; matched budget is a different, fairer selection rule that happens to generalize
  slightly worse here.
- Nothing about CM, which was not re-run and needs no correction.
- Nothing about the theory.
