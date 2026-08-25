# C10C — criterion REJECTED on V4. The evidence says V4 is the defect, not the criterion.

Direction C10C, `kind: INSTRUMENT_CONSTRUCTION`. Registered in `experiment_matrix.yaml`
(sixth document) at `a55b599`; criterion and suite committed at `07b8172`; amendment A1
(Jane row cap 150 000 → 40 000, cost only) at `76548d7` — all **before** the run.
Run 2026-08-23, 222 s. Artifacts: `c10c_probe.csv`, `c10c_report.json`, `c10c_run.log`.

## Registered verdict

**REJECTED.** Acceptance required all five tests to pass on all three streams.

| test | result | detail |
|---|---|---|
| V1 reference sanity | **PASS** | 0/18 reference runs flagged. The inherited Jane rule flags **6/18**. |
| V2 detects true blow-up | **PASS** | 20 runs with `max‖w‖ > 1e6`, **0 missed** — 100% recall |
| V3 monotone in `P` | **PASS** | 12 rays, 0 violations |
| **V4 non-vacuous** | **FAIL** | synthetic 0/60 divergent — one class only (jane 23/60, crypto 12/60) |
| V5 κ robustness | **PASS** | 0.000 of 60 classifications move across κ ∈ {5,10,20}, all streams |

Per the registration the criterion is **not patched and re-run in this session**. Patching
against a failed acceptance test with the thresholds already known is how an instrument gets
fitted to the answers.

## The diagnosis, which points at my test rather than the criterion

On synthetic the capped grid **genuinely contains nothing divergent**, all the way to
`P = 256`:

| `lr` | `M` | `P` | `max‖w‖` | `L_ratio` | `P_ratio` |
|---|---|---|---|---|---|
| 0.5 | 0.5 | 0.25 | 1.12 | 0.999 | 1.000 |
| 2 | 32 | 64 | 26.89 | 0.999 | 1.002 |
| 4 | 32 | 128 | 59.11 | 1.023 | 1.026 |
| 8 | 32 | **256** | **160.60** | **1.152** | **1.223** |

(divergence needs `L_ratio ≥ 2` or `P_ratio ≥ 10`)

Nothing is remotely close. For contrast, the true blow-ups on the same stream:

| probe | `max‖w‖` | `L_ratio` |
|---|---|---|
| OGD, `lr=4` | 2.48e54 | **2.75e103** |
| uncapped, `lr=4` | 2.93e07 | **4.33e10** |

So the criterion separates a genuine blow-up from a well-behaved run by **a hundred orders of
magnitude**, and correctly reports that the capped synthetic grid contains no divergence.
**V4 asked the wrong question**: "both classes present on every stream" is a property of the
*stream × grid*, not of the instrument. On a stream where nothing diverges, a correct
criterion must return one class, and V4 punishes it for doing so.

That is a defect in a test I wrote and registered, and the registered verdict stands anyway.
What it should have asked is non-vacuity *conditional on a divergent configuration existing* —
for instance over capped **and** uncapped probes together, where synthetic does contain both
classes.

## A substantive finding that fell out of the failure

**Capped SN-OMD does not diverge at any `P ≤ 256` on the synthetic stream, while it does on
Jane and crypto.** So C-7's threshold `P*` is not a property of the algorithm alone. The
synthetic stream is stationary in scale with a static comparator; Jane and crypto have
drifting gradient scale and a moving target. Whatever `P*` measures needs that drift, which
the synthetic suite lacks by construction — registered as a scope limit in C10T and now
confirmed from the other side. It also explains C10T's void independently of the criteria.

## The inherited criteria, for contrast (descriptive)

| stream | new | Jane rule | crypto rule | agree(new, Jane) | agree(new, crypto) |
|---|---|---|---|---|---|
| jane | 23/60 | 25/60 | 7/60 | 0.97 | 0.73 |
| crypto | 12/60 | 12/60 | 0/60 | 1.00 | 0.80 |
| synthetic | **0/60** | **60/60** | 41/60 | **0.00** | 0.32 |

The new criterion agrees closely with the Jane rule **on the streams where the Jane rule is
calibrated** (0.97, 1.00) and departs from it completely on synthetic — which is the intended
behaviour, since there the Jane rule fires on the zero predictor. That pattern is what a
working replacement should look like: same answers where the old instrument worked, different
answers exactly where it was broken.

## Threats to validity, ordered

1. **V4 is mis-specified** (above). The rejection is real under the registered rule but does
   not indict the criterion.
2. **Amendment A1 reduced Jane to 40 000 rows.** Registered before the run, on cost grounds,
   and V1–V5 are pass/fail properties — but a shorter window could in principle move a
   classification near a boundary. The full-cap run is recoverable by dropping the flag.
3. **κ was never stressed.** V5 shows 0.000 movement across κ ∈ {5,10,20} on every stream,
   which passes — but it also means no configuration sits near the `P_ratio` boundary in this
   grid, so V5 is weak evidence rather than strong.
4. **Three windows per stream, one tail index on synthetic.** Instrument checks, not
   measurements.

## What this does NOT establish

- **Not** that the criterion is sound. Four of five acceptance tests passed and the fifth
  appears mis-specified, but it has not passed a corrected suite.
- **Nothing about any threshold.** No threshold search was run, by design.
- **Nothing about C-7 or C-8.** Those stay where C10T left them.

## What changes

C-10 stays **OPEN**, one step further along: a candidate criterion exists, passes reference
sanity, blow-up recall, monotonicity and κ-robustness, and is committed at
`scripts/research_divergence.py` — but it is **not accepted**, because the registered suite
rejected it and the suite is not edited in the same session that ran it.

The next step is to respecify V4 (non-vacuity conditional on a divergent configuration
existing in the probe set) and re-validate. That is a registration change, so it belongs to a
new registration, not to this one.
