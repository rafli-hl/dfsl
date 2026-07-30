# Anticipated objections and load-bearing answers (internal — strip before any public release)

Written now, unhurried, so the time-pressured rebuttal version is not the one we ship.
Each answer is the honest one; none re-inflates a claim we already walked back.

## 1. "R² ≈ 0.16–0.28 is impossibly high for this dataset."
It is not comparable to the competition, by **protocol, not leakage**. We evaluate
*progressive online* prediction on the historical record: the learner plays w_t, then
observes (x_t, y_t) and updates. The competition serves batched (date,time) timesteps with
**day-lagged** responders and scores a **held-out future** window — a strictly poorer
feedback channel at both the cross-sectional and daily granularity. An order-of-magnitude
gap is exactly what that difference predicts, with no bug. We say so in Setup and quote no
leaderboard number. We separately *removed* a real look-ahead leak (full-sample feature
standardization → causal), which dropped every method ~2.5×; the numbers reported are
post-fix. Invariance check: SN-OMD is essentially unchanged under per-row vs per-timestep
updates (0.285 → 0.309), so its accuracy is **not** a contemporaneous-information artifact.

## 2. "SN-OMD only ties normalized-GD on the real data — so what's the contribution?"
Normalized-GD is not a competitor; it is the **M→0 endpoint** of SN-OMD's one-parameter cap
family (uncapped scale-adaptive OGD is M→∞). The contribution is the *frontier* and the
two-directional prediction of **when the finite cap matters**: (a) it buys non-divergence —
uncapped diverges at lr ≥ 2 while SN-OMD(M=5) peaks there; (b) it buys accuracy **only when
the normalized tail is genuinely heavy**, confirmed by an interior optimum on a synthetic
p=1.5 stream (≈240× better than uncapped, ≈10× better than normGD, outside the seed band)
and its *absence* on Jane (where the normalized tail is mild). On real data the two ties
because the normalized tail is light — which our own thesis predicts. We report the tie
plainly rather than hiding it.

## 3. "W_s is a data-dependent constant you've hidden."
Stated plainly, not hidden. The drift enters the bound as √W_s, and we **measure** W_s to
grow linearly (β ≈ 1: W_s vs update-count is linear with a B-independent slope ~1.7,
R²>0.98). So the drift is a genuine √T factor and the T^{1/p} rate is **per regime**, not
global; we say this in the theorem's remark and in the tracker section. The tracker's update
timescale controls the *constant* in W_s (~250× on √W_s from round-level to regime-level),
not the exponent. This is exactly why Theorem A.2 is in the appendix and the body leads with
the empirics. (We caught our own earlier "β<1 rescue" as a finite-horizon artifact and
reverted it.)

## 4. "One financial dataset plus a weaker MNIST effect doesn't support the title."
Fair, and we scope it honestly. The **genuine within-regime** effect is established on the
market data, where it survives an **exogenous** control (dividing by a feature-norm scale
that never sees the gradient magnitude still lightens 2.4 → 2.9) and is a feature–residual
*interaction*. On MNIST training gradients the effect **recurs but in a weaker,
schedule-driven form**: in a constant-lr window the pooled tail is already light (α ≈ 6–9),
so the full-run heaviness comes from the decay + lr drops, not within-phase drift. We state
this limit in the text; the title claim rests primarily on the market evidence + exogenous
control, with MNIST as a supporting (transient-driven) recurrence. A second domain with
genuine within-phase drift is stated future work.

## 5. "The §2.1 lower bound is hand-waved."
It is deliberately **motivation, not a bound**. We label it a budget heuristic, note it
lower-bounds only *unconstrained* dynamic regret (trivially Ω(T)), and show its super-√T
growth is driven by pooled-α<2 days that **disappear after normalization** — so we do not
lean on it. "Matching lower bound"/"information-theoretically unreachable" were removed; a
proper P_T-constrained Ω is stated open.

## 6. "The contribution is below the ICML median (scope)."
This is a scope judgment we can't correct by revising, and we won't answer it by
re-inflating claims. The paper is an honest empirical + mechanism contribution with a
stability theorem: (i) nonstationarity manufactures pooled heavy tails (with an exogenous
control), (ii) the cap-interpolation frontier with a tested prediction, (iii) a
protocol-careful evaluation (causal standardization, per-row/per-timestep invariance, a
true stationary negative control), (iv) unconditional stability (Thm 3.1). If a reviewer
finds this below-bar, the paper repositions to an empirical venue or workshop at near-zero
cost — the honesty work is already done.

## 7. "You changed your own results mid-review — is anything trustworthy?"
Yes, and it is the reason to trust it. We stress-tested our *favorable* numbers, not just
suspicious ones: the standardization leakage, the β "rescue," and the MNIST generalization
were all caught by us re-running the measurement that could contradict us and reporting what
came back. Every number in the paper is reproducible from the released scripts
(`scripts/research_*`), and the causal/leak-free protocol is the default in the code.
