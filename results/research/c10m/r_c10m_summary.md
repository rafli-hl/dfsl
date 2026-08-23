# C10M — clip-binding frequency is not the mechanism; the cap is a stability parameter

Direction C10M. Preregistered in `experiment_matrix.yaml` (second document) at commit
`a0fc908`; script committed at `bc326c2`; both **before** execution. Run 2026-08-23,
854 s wallclock, 640 runs. Artifacts: `c10m_binding.csv`, `c10m_report.json`.

**Provenance, as registered.** This hypothesis was generated *after* seeing the C10/Q6
result. It is preregistered before its own execution but is not independent of the data
that motivated it, and nothing here is independent confirmation of C10.

## Registered verdicts

| Hypothesis | Statistic (per-row, primary) | Verdict |
|---|---|---|
| **H2** product sufficiency (`P = lr·M` alone) | `eta2_P = 0.5781` | **INCONCLUSIVE** (band 0.50–0.80) |
| **H3** binding-rate mediation | `rho2_b − rho2_logP = −0.0110` | **INCONCLUSIVE** (band ±0.05) |

Neither registered mechanism was established. Per-step agrees qualitatively
(`eta2_P = 0.4690`, which would be H2-falsified were per-step primary; margin `+0.0145`,
inconclusive).

## Instrumentation gate

Passed **bit-exactly**: worst difference `0.00e+00` across four `(lr, M)` configurations in
both protocols against `research_batched_check._step`. The binding statistics therefore
describe the algorithm the rest of the repository measures, not a lookalike.

## The direct answer on binding frequency

Held-out means over windows 2–10, per-row, for the two anchor configurations:

| Config | `lr` | `M` | `P` | held-out R² | **bind rate** | `r_p99` | `disp_max` |
|---|---|---|---|---|---|---|---|
| published | 2 | 5 | 10 | 0.1237 | **0.0122** | 5.33 | 6.93 |
| matched | 3 | 2 | 6 | 0.2270 | **0.1220** | 5.99 | 4.24 |

The matched configuration clips **ten times more often** and truncates its largest step by
**39%**. Taken alone this looks like strong support for a binding-frequency mechanism.

**It does not survive the grid.** Across the 30-configuration dyadic surface:

- Binding rate is **almost a deterministic function of `M` alone**, essentially independent
  of `lr` (per-row, pooled over `lr`: `M=0.5 → b=0.566±0.012`, `M=1 → 0.327±0.010`,
  `M=2 → 0.123±0.003`, `M=4 → 0.025±0.004`, `M=8 → 0.003±0.001`, `M=16 → 0.001±0.001`).
  Testing "binding rate mediates" is therefore almost exactly testing "`M` mediates".
- Among the 20 non-diverged configurations, binding rate has the **weakest** rank
  association with held-out performance of the four registered candidates:
  `rho2[log_lr]=0.158 > rho2[logP]=0.018 > rho2[log_M]=0.011 > rho2[b]=0.007`.

So the anchor contrast is not explained by binding frequency in general. The two anchors
also differ in `lr` (2 vs 3) and in `P` (10 vs 6), and a single pair cannot separate those
— which is why C10 could not answer this and why the grid was run.

## A weakness in my own registered statistic

`rho2` is a **monotone** association measure, and the performance surface is **single-peaked**
in both `lr` and `M` (best configurations sit in the interior, near `P = 2–4`). A rank
correlation is near-zero for a single-peaked relationship even when the variable matters,
so the H3 test was under-powered by construction. The H3 "inconclusive" verdict must not
be read as "binding frequency is irrelevant".

The following is **unregistered and post hoc**, run because of that flaw. Exact-grouping
`eta2` does not assume monotonicity, so it compares the three candidates on equal footing
(level counts differ slightly, which inflates `eta2` mechanically for more levels):

| grouping | per-row `eta2` (levels) | per-step `eta2` (levels) |
|---|---|---|
| `P = lr·M` | **0.578** (6) | **0.469** (7) |
| `M` | 0.443 (6) | 0.081 (6) |
| `lr` | 0.357 (5) | 0.195 (5) |

`P` is the best single summary of the three, reversing the ordering `rho2` implied. No
candidate is sufficient.

## Exploratory finding — NOT preregistered

**Divergence is a clean threshold in `P = lr·M`.** Per-row, the separation is perfect:

| `P` | 0.25 | 0.5 | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 |
|---|---|---|---|---|---|---|---|---|---|---|
| diverged | 0/1 | 0/2 | 0/3 | 0/4 | 0/5 | 0/5 | **4/4** | **3/3** | **2/2** | **1/1** |

20/20 configurations with `P ≤ 8` are stable; 10/10 with `P ≥ 16` diverge. Per-step is
nearly the same (1/5 at `P=8`, 3/4 at `P=16`). The true threshold lies in `(8, 16]` and is
unresolved by this grid.

No hypothesis about divergence was registered, so this is an exploratory observation
requiring independent confirmation. It suggests a reading the registered analysis did not
test: **the cap's role is to set, jointly with the rate, an effective maximum step that
governs stability — not to control fine-grained accuracy among stable configurations.**
On that reading the published setting's fragility is proximity to the boundary (`P = 10`,
against an optimum near `P = 2–4` and a cliff at `P ≈ 16`) rather than insufficient
clipping. This is consistent with C10's observation that the published configuration
collapses on window 7 while the matched one does not — but it is a hypothesis generated
from these data, not a result.

## A trap in the registered secondary analysis

`eta2_P` computed on **all 30** configurations with R² floored at −1 is **0.9873** — which
would read as overwhelming support for H2. It is an artifact: `P` predicts *divergence*
almost perfectly, and floored divergent configurations therefore line up by `P` by
construction. The primary (non-diverged) figure of 0.578 is the one that speaks to
performance. Reporting the 0.987 as H2 support would be wrong.

## Threats to validity, ordered

1. **The registered H3 statistic was the wrong tool** for a single-peaked surface (above).
   This is a design error made before seeing results, not a post-hoc excuse.
2. **`eta2` comparisons across grouping variables are confounded by level count.** `P` has
   6 levels against `lr`'s 5; some of `P`'s advantage is mechanical.
3. **The divergence threshold is unresolved and unregistered.** `(8, 16]` is a wide bracket
   on a dyadic grid, and the finding is exploratory.
4. **No selection, by design — and therefore no recommendation.** Every configuration was
   evaluated directly on held-out windows. No configuration in this run may be reported as
   a recommended setting; that would be selection on evaluation data.
5. **One dataset, 150 000 rows per window, inherited `_diverged` definition.**

## What this does NOT establish

- **Not** that binding frequency is irrelevant — the registered test for it was weak, and
  `M` (its near-deterministic driver) does carry `eta2 = 0.44` per-row.
- **Not** that `P` is sufficient for performance: `eta2_P = 0.578` leaves most of the
  between-configuration variance among stable configurations unexplained.
- **Nothing about C10's conclusion**, which stands on its own paired comparison.
- Nothing about the divergence partition, the theory, or any other claim in the ledger.

## What changed in the research plan

C-6 (mechanism) remains **OPEN**. The clip-binding reading is not supported; the
max-step/stability reading is promoted to the leading candidate but is exploratory and
untested. The successor question is now: **is `P = lr·M` the stability parameter it appears
to be, and where exactly is the threshold?** That is a registrable hypothesis with a sharp
prediction, and it connects directly to `thm:stability` — which bounds iterates under a
capped normalized step and should imply a `P` boundary if the theory describes the
implementation.
