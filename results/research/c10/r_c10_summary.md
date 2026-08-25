# C10/Q6 — the constant-scale advantage is a tuning-budget artifact, and it reverses

Direction C10/Q6. Preregistered in `experiment_matrix.yaml` at commit `142a075`;
script committed at `48ce7f5`; both **before** execution. Run 2026-08-23, 426s wallclock,
single process. Artifacts: `c10_budget_match.csv`, `c10_report.json`.

## Registered verdict

**H1 SURVIVED.** `fraction_closed = 1.32` per-row against a registered survival threshold
of `>= 0.50`. The value exceeds 1.0, meaning the gap did not merely close — it **reversed
sign**. A reversal is a stronger outcome than H1 predicted; H1 claimed only that at least
half the gap was budget artifact.

## What was tested

The ten-window benchmark tunes `fixed-tau clip` over a joint `(lr x tau)` grid of 70
configurations and tunes `SN-OMD` over `lr` alone (10 configurations) with the cap pinned
at `M=5`. The two are the same algorithm — update magnitude `(lr/sqrt(k))*min(||g||,tau)`
versus `(lr/sqrt(k))*min(||g||/s_t,M)` — differing only in whether the clip threshold is
constant or tracks a predictable scale. This run gives SN-OMD a joint `(lr x M)` grid of
the same cardinality (10 x 7 = 70) and re-measures. Window 1 selects; windows 2–10 evaluate.

| Arm | Grid | configs | window 1 | held-out mean | held-out sd | held-out min |
|---|---|---|---|---|---|---|
| A1 fixed-tau clip | `lr x tau` | 70 | 0.2463 | **0.2020** | 0.0295 | 0.1567 |
| A2 SN-OMD `M=5` (as published) | `lr` | 10 | 0.2846 | **0.1237** | 0.1028 | −0.1071 |
| A3 SN-OMD (budget-matched) | `lr x M` | 70 | 0.3152 | **0.2270** | 0.0403 | 0.1693 |

Per-row, weighted R², hyperparameters frozen from window 1.

## What was found, with uncertainty

Paired over the nine held-out windows; 95% percentile bootstrap over windows (10 000
resamples, seed 20260823); exact two-sided sign test.

| Quantity | per-row | per-step |
|---|---|---|
| `delta_published` (A1 − A2) | **+0.0783** [+0.0391, +0.1325], 9/9 wins, p=0.0039 | +0.0795 [+0.0100, +0.1362], 8/9, p=0.0391 |
| `delta_matched` (A1 − A3) | **−0.0250** [−0.0338, −0.0162], 0/9 wins, p=0.0039 | −0.0134 [−0.0210, −0.0068], 0/9, p=0.0039 |
| budget gain (A3 − A2) | **+0.1033** [+0.0678, +0.1536] | +0.0928 [+0.0294, +0.1465] |
| `fraction_closed` | **1.32** | 1.17 |

Budget-matched SN-OMD beats the constant-scale baseline on **all ten windows**, held-out
9/9, in both protocols. Per-window held-out margins (per-row) run +0.0055 to +0.0464 —
consistently positive but small relative to the across-window spread of ~0.03–0.04.

Two secondary observations, both registered:

- **The instability attributed to the tracked scale was a hyperparameter artifact.** A2's
  catastrophic window-7 value (−0.1071) disappears at matched budget (A3: +0.1693), and
  held-out sd falls from 0.1028 to 0.0403. The published configuration, not the tracked
  scale, produced the fragility.
- **The published protocol's pooled mean hides a selection-overfitting signature.** A2
  wins window 1 (0.2846 vs A1's 0.2463) and loses all nine held-out windows. Pooling the
  selection window into the reported ten-window mean conceals that.

## Reproduction gate

Passed exactly. Reproduced A1 and A2 held-out means match `windows_replication.csv` to
`diff = 0.0000` in both protocols (registered tolerance 0.005). The stored artifacts are
internally sound; the defect is in the comparison design, not the numbers.

## Grid adequacy

- **per-row: every selected hyperparameter interior.** A1 selects `lr=0.2, tau=20` — 4th
  of 10 and 4th of 7 respectively, comfortably inside. A1 was *not* grid-limited and still
  lost. A3 selects `lr=3.0, M=2.0`, both interior.
- **per-step: A3's selection sits on two grid edges** (`lr=8.0` top of grid, `M=0.5`
  bottom). Its optimum is therefore **not resolved**, and the per-step result is reported
  as directionally consistent but grid-limited. Per the stopping rule, no widened re-run
  was performed; any such run would be post hoc and labelled.

## Strongest competing explanation

**Matched cardinality is not matched grid quality.** `TAUS` is inherited from the original
authors; `M_GRID` is my choice. If `M_GRID` happens to be better centred on its optimum
than `TAUS` is on its own, A3 gains an advantage that is not "budget".

The per-row evidence largely defuses this: A1's optimum is interior on both axes and well
away from the edges, so A1's grid resolved its own optimum and A1 still lost by
−0.0250 [−0.0338, −0.0162]. The argument does *not* hold for per-step, where A3 is
boundary-limited and the comparison is correspondingly weaker.

A second candidate — that A3 simply overfit window 1 harder, having searched 70 configs
against A2's 10 — runs the wrong way: more search produced *better* held-out performance,
not worse. And A1 searched the same 70, so A1 vs A3 is symmetric in search effort.

## Threats to validity, ordered by seriousness

1. **Grid placement** (above). Cardinality was matched by construction; centring was not,
   and cannot be without a joint sensitivity study.
2. **A single selection window.** Every transfer claim rests on one tuning event on window
   1. A rolling-origin selection would test whether the ordering is stable across choices
   of selection window; it was not run.
3. **Per-step is grid-limited.** Its `fraction_closed = 1.17` should be read as a direction,
   not a magnitude.
4. **n = 9 windows.** The paired bootstrap CIs are narrow for `delta_matched` but the
   effect (−0.025) is small next to the across-window spread (~0.03–0.04); the result rests
   on consistency of sign (9/9), not on margin size.
5. **One dataset, one preprocessing path.** Jane only, 150 000 rows per window,
   the existing `standardize=True` pipeline. The inherited `_diverged` definition was
   reused unexamined.

## What this does NOT establish

- **Not** that a tracked scale beats a constant one in general. It shows that on this
  benchmark, at matched budget and these grids, the published ordering reverses.
- **Nothing about the stability/divergence partition.** OGD diverging 10/10 and the
  uncapped endpoint 7/10 are untouched — those arms were not re-run and their claim does
  not depend on tuning budget in the same way.
- **Nothing about the theory.** `thm:stability`, `thm:regret`, and the Freedman
  measurability argument are unaffected; this is an empirical-comparison finding.
- **Nothing about the Pass-IV predictable-vs-post-update result.** That decomposition
  stands as measured.
- **It does not vindicate the method.** The tracked scale wins here only after a fix that
  the published protocol did not apply, and the mechanism — *why* a tighter cap `M=2` at a
  higher rate transfers across windows when `M=5` at `lr=2` does not — is unexplained.

## What changed in the research plan

C10/Q6's framing is dissolved as posed: "why does a constant scale beat a tracked one?"
had a false premise at matched budget. The question that replaces it is the mechanism one
above. The published ten-window comparison cannot support a claim about scale processes
and must be re-run at matched budget before any manuscript use — out of scope this phase.
