# C10C3 — criterion ACCEPTED. And V7 shows half of it is dead code.

Direction C10C3, `kind: INSTRUMENT_CONSTRUCTION`. Registered at `125c1a7`; suite committed at
`0c346bf`; both **before** the run. Run 2026-08-23, 280 s. Artifacts: `c10c3_probe.csv`,
`c10c3_report.json`, `c10c3_run.log`. The criterion in `research_divergence.py` is
**unchanged** — only the suite moved.

## Verdict

**ACCEPTED**, with the qualifications attached below, none of them optional.

| test | result | detail |
|---|---|---|
| V1 reference sanity | **PASS** | 0/18 flagged; inherited rule flags 6 |
| V2 blow-up recall | **PASS** | 20 true blow-ups, 0 missed |
| V3 monotone in `P` | **PASS** | 12 rays, 0 violations |
| V5 κ robustness | **PASS** | 0.000 movement — but see V7, this is vacuous |
| V6 truncation stability | **PASS** | 1.000 / 0.983 / 0.967 vs inherited 1.000 / 0.983 / 1.000 |
| **V8 scale invariance** | **PASS** | **1.000 on every stream** |

## V8 — the blind test, and the one that validates the whole premise

A pure change of units applied to the criterion function: multiply both `y` and `preds` by
`c ∈ {1e-3, 1, 1e3}` and require identical classification.

| stream | new criterion | inherited Jane rule |
|---|---|---|
| jane | **1.000** | 0.458 |
| crypto | **1.000** | 0.236 |
| synthetic | **1.000** | **0.062** |

The new criterion is exactly invariant everywhere. The inherited rule changes its answer on
**54% to 94% of runs** under a pure change of units. That is the concrete demonstration that
the inherited criteria carry units and cannot transfer across streams — the claim C-10 was
opened on, now tested rather than argued.

## V7 — the peak clause is inert. That is a finding about my own construction.

Registered blind, with its consequence fixed in advance:

| stream | divergent | by `P_ratio` only | by `L_ratio` only | by both |
|---|---|---|---|---|
| jane | 66 | **0** | 6 | 60 |
| crypto | 34 | **0** | 13 | 21 |
| synthetic | 9 | **0** | 3 | 6 |

**Across 109 divergent runs on three streams, the peak clause changed zero decisions.** The
aggregate clause always fired first. Under the registered consequence:

- The criterion is **reducible to `L_ratio ≥ 2` alone** on this evidence.
- The peak machinery, and `κ` with it, carry no weight.
- **V5 was vacuous, not passed.** Zero movement across `κ ∈ {5,10,20}` is what an inert
  parameter looks like, and I reported it as robustness in C10C and C10C2.

### What that means for the C-10 fix

`L_ratio ≥ 2` is exactly `R² ≤ −1` measured against the best constant. So the working part of
the new criterion is the inherited rule's *first* clause with a best-constant baseline instead
of a zero baseline — and that clause was **already scale-invariant**: scaling `y` and `preds`
by `c` scales both the model's and the baseline's squared error by `c²`, leaving the ratio
fixed.

So the inherited rule's failure to transfer was caused **entirely by its absolute peak-loss
clause** (`peak > 50`), and the fix is to remove it. The elaborate peak-*ratio* replacement I
built to take its place contributes nothing on any stream tested. The real repair is far
smaller than the artifact I wrote around it.

## Qualifications on the acceptance — all load-bearing

1. **V4 was removed by user decision, not by evidence.** I argued it was unfalsifiable for
   capped methods, and flagged at the time that this is exactly the argument a motivated
   author produces for a change that makes their own instrument pass. The argument still
   looks right to me, and that is not the same as it being right.
2. **Only three of the six tests were ever blind at the moment they were run**: V1/V2/V3/V5 in
   C10C, V6 in C10C2, V8 here. Everything else is a re-run of a test already passed.
3. **V5's pass is vacuous** (V7, above).
4. **V6 is a marginal pass on Jane** — 0.967 against the inherited rule's 1.000, inside the
   registered 0.05 margin but not matching it. The new criterion is slightly *less*
   truncation-stable than the one it replaces.
5. **Amendment A1's reduced Jane row cap (40 000)** applies to every acceptance run.

## Threats to validity, ordered

1. **The criterion is simpler than its specification**, and the specification is what was
   validated. A future user reading `research_divergence.py` would reasonably assume the peak
   clause does something.
2. **Three windows or streams each, one synthetic tail index.** Instrument checks, not
   measurements.
3. **V2's ground truth exists only for uncapped methods.** For capped configurations there is
   no criterion-independent check at all, which is what killed V4 twice.
4. **Nothing here validates any threshold.** No threshold search was run, by design.

## What changes

**C-10 is resolved enough to use, with the peak clause understood as inert.** The criterion is
accepted and lives at `scripts/research_divergence.py`.

Two follow-ups, neither started here:

- **Simplify the criterion to its single working clause**, or find a stream where the peak
  clause earns its place. That is a change to the criterion, so it needs its own registration
  — not an edit in the session that discovered the redundancy.
- **The unblocked work.** C-7 (relocate `P*` under a criterion that transfers), C-8 (still
  untested — but note C-11: capped SN-OMD does not diverge on synthetic at all, so a third
  stream for C-8 remains a problem), and C-9.
