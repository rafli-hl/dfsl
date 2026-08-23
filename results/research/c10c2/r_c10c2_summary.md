# C10C2 — REJECTED again on V4. I made the same specification error twice.

Direction C10C2, `kind: INSTRUMENT_CONSTRUCTION`. Registered at `08bd66f`; suite committed at
`c65031c`; both **before** the run. Run 2026-08-23, 271 s. Artifacts: `c10c2_probe.csv`,
`c10c2_report.json`, `c10c2_run.log`. The criterion in `research_divergence.py` is
**unchanged** — only the acceptance suite moved.

## Registered verdict

**REJECTED.**

| test | result | detail |
|---|---|---|
| V1 reference sanity | **PASS** | 0/18 flagged; inherited Jane rule flags 6 |
| V2 blow-up recall | **PASS** | 20 true blow-ups, **0 missed** |
| V3 monotone in `P` | **PASS** | 12 rays, 0 violations |
| **V4 non-vacuity** | **FAIL** | **not applicable on any stream** |
| V5 κ robustness | **PASS** | 0.000 movement, all streams |
| **V6 truncation stability** | **PASS** | the one blind test here — see below |

## V6 — the only test in this direction that carried evidence

Registered blind, comparative against the inherited rule so that a genuine change in the
algorithm's trajectory under truncation is not scored against the criterion:

| stream | agreement, new | agreement, inherited Jane rule | margin |
|---|---|---|---|
| synthetic | 1.000 | 1.000 | ok |
| crypto | 0.983 | 0.983 | ok |
| jane | **0.967** | **1.000** | −0.033, inside the registered 0.05 |

**Reported plainly because it is a real cost:** on Jane the new criterion is *less* stable
under truncation than the inherited rule — 2 of 60 classifications move when the window is
halved, where the inherited rule moves none. It passes because the registered margin allows
0.05, not because it matched. If the instrument is later used to locate horizon-sensitive
thresholds, that 3% is a source of noise the old rule did not have.

## Why V4 failed, and why it is my error twice over

V4's respecified applicability condition asks whether the capped probe grid contains a
configuration with `max‖w‖ > 1e6` — a criterion-independent ground truth, so the criterion
cannot exempt itself. It cannot be satisfied **by construction**:

| stream | analytic bound `2·P·√T` at `P=256` | observed `max‖w‖` | required |
|---|---|---|---|
| jane (40 000 rows) | 102 400 | **276.6** | > 1e6 |
| synthetic (T=20 000) | 72 408 | **160.6** | > 1e6 |
| crypto (T=6 000) | 39 659 | **128.3** | > 1e6 |

`thm:stability` bounds `‖w_T‖ ≤ 2·lr·M·√T` for any finite cap, so no capped configuration can
reach `1e6` at any grid point. The condition is unreachable by three to four orders of
magnitude.

**This is the same error I made in C10T**, where the state-based primary criterion used a
`1e8` iterate threshold that the same bound made unreachable. I diagnosed that failure,
wrote it up, and then reproduced it here with `1e6`. Both trace to one fact I keep
under-using: *because* the theorem bounds the iterates, the iterate norm cannot discriminate
among capped configurations at all.

## The conclusion that follows, and it is not a patch

For capped methods **there is no criterion-independent ground truth of divergence.** The
iterates are provably bounded, so "divergence" for this family is inherently a judgment about
loss — which is what the criterion under test measures. Non-vacuity *within the capped grid*
therefore cannot be validated against independent ground truth by any construction, and V4 as
conceived is unfalsifiable rather than merely mis-tuned.

Degeneracy is already excluded without it: an always-divergent criterion fails V1 (it would
flag the zero and best-constant predictors), an always-stable one fails V2 (it would miss 20
genuine blow-ups). V1 and V2 are anchored on uncapped and OGD probes, where `‖w‖` *is*
unbounded and ground truth *does* exist — 2.48e54 and 2.93e07 on synthetic alone.

The suite should therefore drop V4. **I have not done that**, because the registration says a
failed acceptance test is not patched in the session that ran it, and that rule exists
precisely for moments like this one, where I have a clean argument for a change that also
happens to make my instrument pass.

## Where the criterion actually stands

On evidence rather than on the registered verdict: **five of six tests pass, including the
one blind test in this direction.** The blind evidence for the criterion is now V1, V2, V3, V5
from C10C plus V6 from here. The sole failure is a test that cannot be passed by any
criterion whatsoever.

That is a good instrument with a broken suite — but it is **not accepted**, and it should not
be used to locate thresholds until it passes a suite that can be passed.

## Threats to validity, ordered

1. **Nothing here was blind except V6.** V4's correction was written knowing what it was
   correcting; V1/V2/V3/V5 were re-runs of tests already passed. This was disclosed in the
   registration before running.
2. **V6's margin was chosen by me** at 0.05, and Jane's result sits at −0.033 — inside it, but
   not comfortably. A stricter margin would have failed it.
3. **V5 remains weak evidence.** 0.000 movement across κ means no configuration sits near the
   `P_ratio` boundary in this grid, so the test is unstressed rather than strongly passed.
4. **Amendment A1's reduced Jane rows** (40 000) still applies.

## What changes

C-10 stays **OPEN**. The criterion is unchanged and remains committed but unaccepted. The
next registration should drop V4 with the argument above, keep V6, and — given the pattern —
state explicitly, before choosing any threshold, whether the quantity it is applied to is one
`thm:stability` already bounds.
