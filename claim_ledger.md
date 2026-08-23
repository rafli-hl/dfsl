# Claim ledger

**This file is new as of 2026-08-23.** The Phase-1 `claim_ledger.md` referenced by the
Phase-2 brief is absent from this repository and `git log --all` shows it was never
committed here. This ledger therefore starts from the claims a Phase-2 session has
actually examined, not from an inherited list. Claims not listed here have not been
audited by this process and carry whatever status the manuscript gives them.

Status values: `SUPPORTED` (measured, survives the check applied) ·
`CONFOUNDED` (the evidence offered cannot answer the question) ·
`OPEN` (asked, not answered) · `UNTOUCHED` (not examined this phase).

---

## C-1 — "A constant scale beats a predictable tracked scale on the ten-window benchmark"

**Status: CONFOUNDED → REVERSED at matched budget.**

Evidence as published: `windows_replication.csv`, per-row held-out means, fixed-tau clip
0.2020 vs SN-OMD (M=5) 0.1237, fixed-tau winning 9/9 held-out windows.

What was found (direction C10/Q6, `results/research/c10/r_c10_summary.md`): the two arms
were tuned at unequal budget — 70 joint `(lr x tau)` configurations for the baseline
against 10 `lr` configurations for the proposal with the cap pinned at `M=5`. At matched
budget (70 joint `(lr x M)` configurations) the ordering **reverses**: SN-OMD 0.2270 vs
fixed-tau 0.2020, held-out `delta = -0.0250` [−0.0338, −0.0162], SN-OMD winning 9/9
held-out and 10/10 overall. `fraction_closed = 1.32` against a registered survival
threshold of 0.50.

Scope: per-row primary. Per-step agrees in direction (`-0.0134`, 0/9) but its matched arm
selected at two grid edges, so its magnitude is not resolved.

**Consequence:** the published comparison cannot support a claim about constant vs tracked
scale processes in either direction. It must be re-run at matched budget before any
manuscript use.

## C-2 — "SN-OMD is fragile across windows (held-out sd 0.103, min −0.107)"

**Status: CONFOUNDED.** The fragility is a property of the published configuration
(`M=5, lr=2`), not of the tracked scale. At matched budget the same method has held-out
sd 0.0403 and min +0.1693; the window-7 collapse disappears entirely.

## C-3 — "The ten-window mean is a held-out measurement"

**Status: CONFOUNDED.** The published protocol tunes on window 1 and reports the mean over
all ten windows *including* window 1. Per-row, the published SN-OMD arm wins the selection
window (0.2846) and loses all nine held-out windows — a selection-overfitting signature
the pooled mean conceals. Held-out and in-sample figures should be reported separately.

## C-4 — "Stored research artifacts reproduce"

**Status: SUPPORTED.** The preregistered reproduction gate re-derived the fixed-tau and
published-SN-OMD held-out means from source and matched `windows_replication.csv` to
`diff = 0.0000` in both protocols (tolerance 0.005). The stored numbers are sound; the
defect found is in comparison design, not arithmetic.

## C-5 — "Why does a constant scale beat a tracked one?" (the C10/Q6 question as posed)

**Status: DISSOLVED — false premise.** At matched budget it does not. Replaced by C-6.

## C-6 — Mechanism: why does `M=2` at `lr=3` transfer across windows when `M=5` at `lr=2` does not?

**Status: OPEN.** The winning matched configuration uses a *tighter* cap at a *higher*
rate. Whether that reflects clip-binding frequency, an interaction between cap and the
tracked scale's drift, or something else is unexamined. This is the natural successor
direction.

---

## Untouched this phase

`UNTOUCHED` — not examined, status unchanged:

- The stability/divergence partition (OGD 10/10, uncapped endpoint 7/10, bounded
  scale-free 0/10). Those arms were not re-run.
- All theory: `thm:stability`, `thm:regret`, `thm:regretbody`, the Freedman
  measurability argument, `ass:track`.
- The Pass-IV predictable-vs-post-update decomposition (grid accounts for +0.0379 of the
  +0.0378 gap; measurability 0.3%).
- RMSProp/Adam bounded-step finding (`app:adaptive`).
- The tracker bootstrap and Bonferroni analysis (`app:tracker`).
- Every crypto, synthetic, MNIST and GARCH-surrogate result.
