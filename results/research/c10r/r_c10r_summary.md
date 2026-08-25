# C10R — the registered test was vacuous. C-8 is untested, not refuted.

Direction C10R. Preregistered in `experiment_matrix.yaml` (fourth document) at commit
`6b46199`; script committed at `6a59f88`; both **before** execution. Run 2026-08-23, 88 s.
Artifacts: `c10r_crypto.csv`, `c10r_report.json`, `c10r_run.log`.

## Registered verdict, and why it means almost nothing

**H5 FALSIFIED**, `ratio = spread_R / spread_P = 1.0000`.

That number is not evidence. It is an identity. Stage 1 selected `q* = max`, and Jane's
`r_max = 49.93` exceeds every `M` on the grid (max 16), so `min(r_max, M) = M` for every
ray and `R ≡ P` **identically**. The ratio was 1.0000 by construction before any crypto
data was touched. The registered procedure produced a falsification that carries no
information about C-8.

## The registration error that caused it

C-8 was generated from the Jane **per-step** residual: thresholds rising monotonically with
`M` (7.29 → 17.34). I registered the stage-1 fit on Jane **per-row**, where the residual is
*non-monotone* (peaks at `M=4`, falls at 8 and 16) and which C-8 was never proposed to
explain. No quantile can straighten a non-monotone residual, so the fit was doomed before
it ran:

| `q` | Jane `r_q` | per-row spread of `R*` | vs `P`'s 1.6818 |
|---|---|---|---|
| p50 | 0.670 | 17.63 | worse |
| p90 | 2.256 | 7.73 | worse |
| p99 | 5.588 | 3.56 | worse |
| max | 49.93 | 1.6818 | identical (degenerate) |

Had stage 1 been registered on per-step — the protocol C-8 actually came from — it would
have selected `q = p99`, spread `2.378 → 1.561`, **ratio 0.656**, comfortably inside the
survival band. This is my error in the registration, not a property of C-8.

## What the held-out data actually shows — POST HOC

The crypto thresholds are a registered output; reading them for C-8's prediction is not.
Under the registered secondary criterion, all eight rays resolved cleanly (0 censored,
0 non-monotone, brackets to a factor of 1.0054):

| `M` | 0.25 | 0.5 | 1 | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|---|---|
| `P*` | 6.60 | 6.93 | 7.60 | 11.34 | 14.55 | 18.67 | 28.02 | 37.95 |

`P*` rises **monotonically with `M` across all eight rays, spanning 128× in `M`** — exactly
the pattern C-8 predicts, now on a stream that did not generate the hypothesis. Applying a
non-degenerate quantile (crypto's own reference `r`, measured on this stream):

| `q` | crypto `r_q` | spread of `R*` | ratio vs `spread_P = 5.7495` | would have been |
|---|---|---|---|---|
| p50 | 0.614 | 9.51 | 1.654 | falsified |
| p90 | 2.278 | 4.20 | 0.730 | **survived** |
| p99 | 7.033 | **2.49** | **0.433** | **survived decisively** |
| max | 77.86 | 5.75 | 1.000 | degenerate |

**C-8 is therefore not refuted by this run. It is untested**, and the one piece of held-out
evidence available points in its favour. Saying otherwise in either direction would
misreport what happened.

I have now seen this, so I cannot repair it by re-fitting on per-step and re-testing on
crypto — that would be fitting and testing after seeing both. A clean test requires a
**third** stream.

## The primary divergence criterion was voided

Registered primary was crypto's own rule (peak rolling loss > 1e3), adopted unchanged
specifically so the threshold could not be chosen after seeing results. **All eight rays
came back right-censored**: nothing diverges by that rule even at `P = 128`. Under the
registered rule (≥2 censored rays voids the statistic) the primary yields no verdict, and
everything above rests on the registered secondary (Jane's `_diverged`).

That criterion was calibrated by prior work for a different question — true blow-up at
competitive rates — and is far too lenient for locating a boundary. Adopting it unchanged
was the right call for avoiding post-hoc threshold choice, and it cost the primary analysis.
Both outcomes are reported, as registered.

## A registered finding that does stand: `P` is stream-dependent

`spread_P` and `spread_lr` are registered outputs, and on crypto:

| parameterization | Jane (C10S) | crypto (here) |
|---|---|---|
| `P = lr·M` | **1.68×** | **5.75×** |
| `lr` alone | 23.6× | 22.3× |

`P` remains far better than the rate alone on both streams (3.9× better on crypto), but its
quality as a stability parameterization is **much weaker off Jane**. C-7's headline figure
of 1.68× is Jane-specific and should not be quoted as a general property.

## Threats to validity, ordered

1. **The registered test was vacuous** (above). Nothing here is a clean test of C-8.
2. **The post-hoc crypto analysis fits and evaluates on the same data.** The favourable
   ratios (0.43, 0.73) use crypto's own `r` quantiles on crypto's own thresholds. They are
   suggestive, not a test.
3. **Criterion dependence is severe.** The two registered criteria differ so much that one
   voids entirely while the other resolves all eight rays. Any threshold quoted here is a
   statement about `_diverged`, not about divergence.
4. **One held-out stream**, hourly crypto, near-unpredictable (`R² ≈ 0.002`), so this speaks
   to the stability boundary only.
5. **Window length differs** between streams (6000 bars vs 150 000 rows), and thresholds are
   horizon-dependent, so cross-stream spread comparisons carry that confound.

## What this does NOT establish

- **Not** that C-8 is false. The registered test could not test it.
- **Not** that C-8 is true. The supporting evidence is post hoc and self-fitted.
- **Nothing about accuracy** — crypto returns are near-unpredictable and no R² claim is made.
- **Nothing about C10, C10M, or C10S's own conclusions**, which stand on their analyses.

## What changed in the research plan

C-8 stays **OPEN** and is now explicitly *untested*, with the record of why. The successor
requires a third stream (the synthetic suite is the obvious candidate — data-free and
reviewer-reproducible), with `q` fitted on Jane **per-step** and frozen, and a divergence
criterion chosen on stability grounds rather than inherited.

C-7 is amended: `P` locates the boundary to 1.68× on Jane but only 5.75× on crypto. The
compression relative to the rate alone replicates; the tightness does not.
