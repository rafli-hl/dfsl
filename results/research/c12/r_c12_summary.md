# C12 — tab:replication at matched budget: SN-OMD goes from 4th to 1st, and nothing else moves

Direction C12, `kind: ARTIFACT_REGENERATION`. Registered at `14e6652`; script committed at
`0aa50c1`; both **before** the run. Run 2026-08-24, 2369 s, 466 configurations.
Artifacts: `c12_matched.csv`, `c12_matched_summary.csv`, `c12_report.json`, `c12_run.log`.

## Reproduction gate — passed perfectly

All ten checks (five untouched methods × two protocols) reproduce the published CSV at
`max|diff| = 0.000000`. **The only thing that changed is SN-OMD's grid**, which is what makes
the difference attributable.

## The table, per-row (primary), all ten windows

| method | cfg | mean | std | min | diverged | held-out 2–10 | window 1 |
|---|---|---|---|---|---|---|---|
| **SN-OMD (M tuned)** | 70 | **+0.2359** | 0.0471 | +0.1693 | 0/10 | **+0.2270** | +0.3152 |
| fixed-tau clip | 70 | +0.2064 | 0.0311 | +0.1567 | 0/10 | +0.2020 | +0.2463 |
| AdaGrad-Norm | 8 | +0.1980 | 0.0706 | +0.0737 | 0/10 | +0.1835 | +0.3286 |
| Normalized-GD | 10 | +0.1787 | 0.0286 | +0.1425 | 0/10 | +0.1741 | +0.2205 |
| OGD | 5 | +0.0010 | 0.0434 | −0.1122 | 0/10 | −0.0010 | +0.0184 |
| Scale-adaptive OGD | 10 | −2.99e5 | 8.47e5 | — | **7/10** | — | +0.1593 |

Per-step, SN-OMD also leads: **+0.2138** (held-out +0.1949) against fixed-tau's +0.2016
(+0.1815), with OGD diverging 9/10 as published.

## What changed, and what did not

| method | published | matched | Δ |
|---|---|---|---|
| SN-OMD | 0.1398 | **0.2359** | **+0.0961** |
| fixed-tau clip | 0.2064 | 0.2064 | 0.0000 |
| AdaGrad-Norm | 0.1980 | 0.1980 | 0.0000 |
| Normalized-GD | 0.1787 | 0.1787 | 0.0000 |
| OGD | 0.0010 | 0.0010 | 0.0000 |

**SN-OMD moves from 4th place to 1st** on the paper's own headline table, purely by tuning the
cap it already has over the same number of configurations its comparator was already getting.
Its dispersion more than halves (std 0.1095 → 0.0471) and its worst window goes from
**−0.1071 to +0.1693** — the catastrophic window-7 collapse in the published table is a property
of the pinned `M=5`, not of the method.

## The three registered surprises: none occurred

1. **SN-OMD did not collapse onto an endpoint.** Selected `M = 2`, interior to `[0.5 … 100]`.
   It remains a distinct row rather than a relabelling of normalized-GD (`M→0`) or
   scale-adaptive OGD (`M→∞`).
2. **The divergence partition is unchanged.** Scale-adaptive OGD 7/10 per-row, OGD 9/10
   per-step, every bounded scale-free method 0/10 — exactly as published. Tuning `M` cannot
   make an uncapped or unnormalized method stable, and it did not.
3. **The untouched methods reproduced exactly** (gate above).

## Secondary: the divergence partition under the accepted C-10 criterion

Reported alongside the inherited rule, since C10C3 accepted a criterion that actually transfers
across streams:

| protocol | method | inherited `_diverged` | relative (C-10) |
|---|---|---|---|
| per-row | Scale-adaptive OGD | 7/10 | **6/10** |
| per-step | OGD | 9/10 | 9/10 |
| — | every bounded scale-free method | 0/10 | 0/10 |

**The partition is robust to the criterion**, which is the substantive point: the paper's
stability dichotomy is not an artifact of the absolute loss threshold. One window differs on
scale-adaptive per-row (7 vs 6), so the exact count is criterion-dependent even though the
partition is not.

## The fairness question a reviewer will ask

*SN-OMD searched 70 configurations and normalized-GD only 10 — isn't that the same unfairness,
reversed?*

No, and the distinction is the registered principle: **each method is tuned over its own free
parameters.** Normalized-GD is the `M→0` limit and scale-adaptive OGD the `M→∞` limit of the
SN-OMD family; neither has a threshold to tune, so a 1-D grid searches their parameter space
*completely*. OGD and AdaGrad-Norm likewise. Only SN-OMD and fixed-tau clip have a threshold
parameter, and they now get 70 configurations each. The original defect was that one of those
two had its parameter frozen while the other's was swept.

The residual risk that *is* real — more search means more opportunity to overfit window 1 —
runs the wrong way here. SN-OMD's held-out mean (0.2270) sits close to its all-ten mean (0.2359),
its dispersion is second-lowest in the table, and it leads on held-out windows as well as
pooled. The published `M=5` arm did the opposite: it won window 1 (0.2846) and collapsed
held-out (0.1237).

## Threats to validity, ordered

1. **Single selection window.** Everything still rests on tuning at window 1 and freezing. A
   rolling-origin protocol is untested and remains the most load-bearing untested assumption in
   this line of work.
2. **`M` and `τ` grids are matched in cardinality, not in placement.** Both optima are interior
   (`M=2` of `[0.5…100]`, `τ=20` of `[2…300]`), which is the best available evidence that
   neither grid is limiting, but placement is still a judgement.
3. **Per-step is noisier** (std 0.12–0.13 for the leaders against 0.03–0.05 per-row); the
   per-step ordering is correspondingly less firm.
4. **One dataset, 150 000 rows per window, one preprocessing path.**

## What this does NOT establish

- **Not that SN-OMD is the best method.** It leads this table at matched budget on this
  benchmark; the margins over fixed-tau (+0.0295 all-ten, +0.0250 held-out) are small next to
  across-window dispersion, and C10/Q6's paired analysis is the place where that comparison was
  done properly (−0.0250 [−0.0338, −0.0162], 9/9 held-out).
- **Nothing about the theory.** `thm:regret`, `thm:stability` and the D1/T1 findings are
  untouched.
- **Nothing about the accuracy claim the paper makes.** The abstract's *"the contribution is the
  measurement and the stability, not an accuracy win"* remains the right sentence — this result
  removes a defect in a comparison, it does not turn the paper into an accuracy paper.

## What changes

The manuscript's `tab:replication` now has a defensible replacement artifact. **No manuscript
edit was made** — deciding what the table should say, and whether the SN-OMD row is relabelled
`M` tuned, is author judgement and out of scope for this phase.

`windows_replication*.csv` are untouched, so the paper's current numbers and the guard that
pins them (`test_paper_number_matches_its_csv`) both still hold.
