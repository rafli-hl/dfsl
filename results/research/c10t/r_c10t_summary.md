# C10T — VOID. And the reason is the most useful thing this line of work has produced.

Direction C10T. Preregistered in `experiment_matrix.yaml` (fifth document) at commit
`4cdd9d3`; script committed at `bf1bc7a`; both **before** execution. Run 2026-08-23, 318 s.
Artifacts: `c10t_synth.csv`, `c10t_report.json`, `c10t_run.log`.

## Registered verdict

**H6: VOID. H7: VOID.** No ratio was computable at any tail index under either criterion.
All **48** ray × criterion × tail-index combinations (8 × 2 × 3) were censored — and, tellingly,
in *opposite directions*:

| criterion | outcome | meaning |
|---|---|---|
| primary — state-based, `max‖w‖ > 1e8` | **48/48 right-censored** | nothing ever diverges, even at `P = 128` |
| secondary — Jane `_diverged` | **48/48 left-censored** | everything diverges, even at `P = 0.5` |

C-8 is therefore **still untested**. Per the registered stopping rule the direction closes
here: no fourth stream is sought, and there is no uncontaminated one left in any case.

## The streams were fine — the registered sanity check held

Reference `r_p99` by tail index: **14.760** (p=1.3) > **11.663** (p=1.5) > **8.020** (p=2.0),
exactly the registered a-priori ordering. Heavier tails produce larger normalized-gradient
spikes, as the generator intends. The instrumentation gate passed **bit-exactly**
(worst diff `0.00e+00`). Nothing failed on the data side.

## Why the primary criterion cannot fire — provable without any data

For SN-OMD with a **finite** cap `M`, the step magnitude is at most `(lr/√k)·M`, so

```
‖w_T‖  ≤  Σ_{k=1..T} (lr/√k)·M  ≤  2·lr·M·√T  =  2·P·√T
```

At the top of the registered bracket (`P = 128`, `T = 20000`) that is **36,204** — against a
registered threshold of **1e8**. Measured maxima are far smaller still:

| `lr` | `M` | `P` | observed `max‖w‖` | analytic bound | threshold |
|---|---|---|---|---|---|
| 1 | 0.5 | 0.5 | 1.18 | 141 | 1e8 |
| 2 | 4 | 8 | 5.67 | 2 263 | 1e8 |
| 4 | 32 | 128 | **59.11** | 36 204 | 1e8 |

The criterion is vacuous by roughly **six orders of magnitude**, and would have been on Jane
(`bound 99,148`) and crypto (`19,830`) too.

**My justification for it was exactly backwards.** I wrote that a state-based criterion is
right because it "refers to the quantity `thm:stability` actually bounds". *Because* the
theorem bounds it, it cannot discriminate. A finite cap makes iterate divergence impossible
by construction. I could have derived this before registering and did not.

## Why the secondary criterion fires everywhere

Jane's `_diverged` triggers on `R² ≤ −1` **or** peak rolling loss `> 50`. On a Student-t(1.5)
stream the target has **infinite variance** (sample `var(y) ≈ 3499`), so:

| configuration | `R²` | peak rolling loss | `_diverged`? |
|---|---|---|---|
| `lr=1, M=0.5` (`P=0.5`) | +0.0007 | 34 612 | **True** |
| `lr=0.01, M=0.5` (`P=0.005`) | +0.0002 | 34 624 | **True** |
| **predicting zero everywhere** | +0.0000 | **34 627** | **True** |

The criterion fires on the zero predictor. Its absolute threshold of 50 is calibrated to
Jane's standardized targets (variance ≈ 1); on a heavy-tailed stream it is measuring the
noise floor, not the learner. `R² = +0.0007` says the learner is behaving fine.

## What this establishes — and it is not small

**"Divergence", as used throughout C-7, C10S and C10R, is not a well-defined quantity across
streams.** Two distinct failures, one structural and one calibration:

1. **Iterate divergence is impossible for capped SN-OMD.** `thm:stability` guarantees it. So
   every "divergence" measured in this line of work is a **loss** phenomenon — predictions
   becoming bad — not instability of the iterate. C-7's "stability threshold `P*`" is
   therefore a *loss-degradation* threshold, not a stability boundary in the theorem's sense.
   The iterates were bounded at every point on every grid, including the ones labelled
   divergent.
2. **Loss-based criteria carry absolute thresholds tied to a target scale and tail.** Jane's
   50 fires on a zero predictor here; crypto's 1e3 never fired even at `P = 128` (C10R). They
   are not interchangeable and neither transfers.

This generalizes ledger C-9 from "the criterion matters" to "no criterion currently in this
repository is comparable across streams, and the state-based alternative is vacuous."

## Threats to validity, ordered

1. **This run tested nothing about C-8.** Both criteria failed for reasons unrelated to it.
2. **The structural claim rests on a bound I derived**, `‖w_T‖ ≤ 2P√T`, verified numerically
   at three points here but not proved in general for the winsorized-EMA tracker. It follows
   only from the cap and the `1/√k` schedule, both of which are explicit in `_step`.
3. **Synthetic streams are stationary in scale** — registered as a scope limit up front. They
   test the `r`-quantile mechanism without drift, so even a working criterion would have left
   the drifting-scale case open.
4. **The heavy-tail diagnosis is specific to `p < 2`.** At `p = 2.0` the variance is still
   undefined at the boundary; the same left-censoring occurred there.

## What this does NOT establish

- **Nothing about C-8 in either direction.** It is untested, not refuted.
- **Nothing that invalidates C10, C10M, or C10S's within-Jane comparisons**, which used one
  criterion consistently. What changes is the *interpretation* of the word "divergence" in
  them, and the transferability of their thresholds.
- **Nothing about `thm:stability` being wrong.** The opposite: its guarantee is what makes
  the state-based criterion vacuous.

## What changed in the research plan

C-8 closes as **untested**, with a prerequisite now identified. Any future test needs a
divergence criterion that is *scale-free and stream-comparable* — for example loss relative
to the best-constant predictor on the same stream, or to a reference run — designed and
validated **before** any threshold search, not inherited. That prerequisite is logged as
C-10 and blocks C-7's, C-8's and C-9's remaining questions alike.

The direction closes here rather than moving to a fourth stream, as registered.
