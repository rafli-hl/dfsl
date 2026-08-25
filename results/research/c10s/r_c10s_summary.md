# C10S — the threshold is at `P* ≈ 11.5`, but `P` is not sufficient, and the boundary is not sharp

Direction C10S. Preregistered in `experiment_matrix.yaml` (third document) at commit
`44f6fa1`; script committed at `bbfdf83`; both **before** execution. Run 2026-08-23,
941 s wallclock, 84 configurations × 10 windows × 2 protocols. Artifacts:
`c10s_threshold.csv`, `c10s_report.json`, `c10s_run.log`.

**Provenance, as registered.** This tests ledger C-7, which was itself an exploratory
observation generated from the C10M data. The configurations here are new, but the
hypothesis originated in data, so a positive result is weaker than a first-registered one.

## Registered verdict

**H4 INCONCLUSIVE.** Per-row spread = **1.682** against a survival band of ≤1.25 and a
falsification band of ≥2.00. Per-step spread = **2.378**, which *would be* H4-falsified
were per-step the primary protocol.

Both registered guards came back clean in both protocols: **0 censored rays, 0
non-monotone rays, all 6 usable.** Every ray's bracket was resolved to a factor of 1.044.

## Where the threshold is

Per-row, hyperparameters `lr = P/M` along each ray, all ten windows:

| ray `M` | `P*` | bracket | `lr* = P*/M` |
|---|---|---|---|
| 0.5 | 8.671 | [8.485, 8.861] | 17.342 |
| 1 | 9.055 | [8.861, 9.253] | 9.055 |
| 2 | 12.806 | [12.531, 13.086] | 6.403 |
| 4 | **14.583** | [14.270, 14.902] | 3.646 |
| 8 | 13.373 | [13.086, 13.665] | 1.672 |
| 16 | 11.743 | [11.491, 12.000] | 0.734 |

**`P*_hat = 11.49`** (geometric mean), per-ray range **[8.67, 14.58]**.

Per-step: `P*_hat = 9.80`, range [7.29, 17.34], and the ray thresholds are **monotone
increasing in `M`** (7.29, 7.29, 8.30, 9.46, 12.26, 17.34) — a clean systematic residual.

## The result that matters more than the verdict

`P` is not sufficient, but it is **dramatically better than either factor alone**. Across
these six rays:

| quantity | variation across rays |
|---|---|
| `M` (by construction) | **32×** |
| `lr*` (critical rate) | **23.6×** |
| `P* = lr*·M` | **1.68×** |

Compressing a 32-fold and a 23.6-fold variation into 1.68-fold is a substantive statement
about the effective maximum step, even though it misses the registered 1.25 tolerance. The
design was built to make this test hard: at a given `P`, the `M=0.5` ray clips ~57% of
steps while `M=16` clips ~0.1% and takes typical steps more than an order of magnitude
smaller. `P` survives that variation to within a factor of 1.68.

## C-7's "perfect separation" was partly a resolution artifact — post hoc

The registered secondary (divergent-window fraction at every visited point) shows the
boundary is **graded, not sharp**. The any-window criterion marks where the *first* of ten
windows fails; a median-window criterion sits much higher:

| per-row ray | any-window `P*` | first `P` with ≥5/10 diverging |
|---|---|---|
| M=0.5 | 8.86 | 12.00 |
| M=1 | 9.25 | 12.00 |
| M=2 | 13.09 | 16.97 |
| M=4 | 14.90 | 24.00 |
| M=8 | 13.67 | 16.97 |
| M=16 | 12.00 | 24.00 |

The transition zone spans roughly a factor of 1.5–2 in `P`. C10M sampled `P` at factor-2
spacing, which is exactly the width of the zone — so it could not see the gradient and the
separation looked perfect. **C-7 should be restated:** a threshold exists and `P` locates
it far better than `lr` or `M` alone, but it is a transition band, not a cliff.

Consistency check: every C10M per-row observation is reproduced. `P=8` stable on all rays
(all `P*` > 8.67); `P=16` divergent on all rays (all `P*` < 14.59).

## Strongest competing explanation

**The any-window criterion is an extreme-value statistic** — a minimum over ten windows —
so each `P*` is set by the single most fragile window, and the per-ray differences may be
window heterogeneity rather than a property of `M`. This is the likeliest explanation for
the per-row non-monotonicity (`P*` peaks at `M=4` then falls at `M=8, 16`), which no
mechanism predicts. The per-step monotone trend is harder to dismiss this way, being
ordered across all six rays.

The criterion was inherited deliberately, unchanged, so C10S and C-7 are comparable — but
it is the wrong statistic for locating a boundary, and that is a design cost I accepted for
comparability rather than a discovery.

## Threats to validity, ordered

1. **Extreme-value criterion** (above). The median-window figures reorder the rays, so the
   per-ray pattern is criterion-dependent.
2. **No uncertainty on `P*`.** The runs are deterministic, so there is no sampling noise to
   report — but across-window heterogeneity is real and the design has no replication to
   quantify it. The 1.044 bracket is search resolution, **not** a confidence interval, and
   must not be read as one.
3. **Protocol dependence.** Per-row is inconclusive, per-step would be falsified, and the
   residual has different shapes. Any claim that `P` governs stability is protocol-specific.
4. **Horizon-specific.** Measured at 150 000 rows per window. The step is
   `(lr/√k)·min(r_t, M)`, so `k` enters; the 4 000-row smoke left-censored every per-row ray,
   which is that effect at full strength.
5. **Six rays, one dataset, one preprocessing path.**

## What this does NOT establish

- **Not** that `P` is *the* stability parameter. H4 is inconclusive per-row and would be
  falsified per-step. The systematic residual in `M` is real, at least per-step.
- **Not** that proximity to the threshold explains held-out accuracy. The published
  configuration sits at `P=10` against an `M≈5` threshold near 14, and the matched one at
  `P=6` against 12.8 — relatively closer for the published one — but neither diverges on any
  window, and no link between boundary proximity and R² was tested here.
- **Nothing about C10 or C10M**, whose conclusions stand on their own analyses.
- **Nothing about `thm:stability`.** Its constant was not derived or compared; the
  comparison remains the open opportunity.

## What changed in the research plan

C-7 is updated from "perfect separation on `P`" to "a transition band located by `P` to
within a factor of 1.68 across rays spanning 32× in `M`", with a numeric estimate
`P*_hat ≈ 11.5` per-row at this horizon.

The successor question is the residual: `P` is the *nominal* maximum step, but it is only
attained when the clip binds, which for large `M` is rare. The natural candidate is the
**realized** maximum step, `lr·min(r_max, M)`, which would predict exactly the per-step
pattern of `P*` rising with `M`. That is a post-hoc proposal generated from this run's
residual; per the registration it may be proposed but not tested on this data.
