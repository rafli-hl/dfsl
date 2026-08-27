# Research decisions

**This file is new as of 2026-08-27.** It was requested by name during Structure C and was
**absent from this repository** — `git log --all` shows it was never committed here, like
`RESEARCH_CHARTER.md`, `MANUSCRIPT_ASSESSMENT.md` and `PHASE2_RESEARCH.md` before it. It starts
from the decisions taken in the Structure C restructure and does not reconstruct earlier ones;
those live in `research_state.md` session by session.

Its purpose is narrow and different from `research_state.md`: this records **judgement calls
where a different reasonable person would have chosen otherwise**, with the reason, so the
choice can be revisited rather than re-litigated.

---

## D-1 — The intro moved with §3, and that was not scope creep (2026-08-27)

**Decision.** When Structure C demoted the dynamic-regret bound out of §3, the third
contribution bullet in §1 was rewritten in the same commit, from *"what the predictable scale
does add is a per-regime dynamic-regret bound"* to the tuning-transfer result and the
`9/10`-vs-`0/10` split it predicts.

**Why it could have gone the other way.** The restructure's brief was §3 and Appendix D. Editing
the introduction in the same step widens the blast radius of a change already flagged as the
first irreversible one, and a narrower commit would have been easier to revert.

**Why it did not.** Leaving it would have reproduced a defect this project has already made
once: after the Table 1 rework, §B.2 kept quoting numbers the new table contradicted, because
the change did not reach every claim site. A contributions bullet promising the regret bound
while §3 demotes it is the same failure — an unreached claim site — and it sits in the first
page rather than an appendix. The restructure was **incomplete** without it, not extended by it.

**How to revisit.** If Structure C is abandoned, the bullet reverts with the rest; it is not a
separable change. `pre-structure-c` rebuilds the prior framing.

## D-2 — Tagged the current state, not `master`, before restructuring (2026-08-27)

**Decision.** The restructure's first constraint said to branch off a tagged `master`. `master`
is at `5e6c383` and contains none of D1C, T4 or T4B. The tag went on the **current
pre-restructure state** instead, and `research/structure-c` branches from there.

**Why.** The constraint's purpose clause was *"so the current framing is recoverable as a
build."* Tagging `master` would have preserved a framing seven commits stale — the wrong
artifact. Flagged before acting rather than after.

**Cost.** `master` is now well behind the work, and the recoverable baseline lives on a tag
rather than a branch. Merging the research branches to `master` remains an open decision.

## D-3 — The clipper row was marked off-stream rather than deleted or restated (2026-08-27)

**Decision.** T4's C-23 found `tab:jane`'s AdaptiveClip/RobustOMD row sourced from a different
window than the caption names. The row was kept, marked with a dagger recording where it was
measured, rather than deleted or replaced with the other window's numbers.

**Why it could have gone the other way.** Deleting it removes a known-mis-sourced number.
Replacing it with `continuous_stream.csv`'s figures would have made the caption true.

**Why it did not.** Deleting removes an underperforming method from a comparison, which the
standing constraints forbid. Replacing would have imported numbers from a 300k-row stream into a
table whose every other row is 150k — trading a disclosed provenance mismatch for a hidden one.
T4B then measured the row on the instrument's own slice and **confirmed both figures**, so the
conservative choice was also the correct one.

## D-4 — A boundary sentence was cut from the Conclusion for the page budget (2026-08-27)

**Decision.** The Conclusion gained the tuning-transfer clause but *lost* a proposed sentence,
*"What it does not buy is a global regret rate: a boundary we map by measurement."* It did not
fit under 9pp, and §0/§30 forbid reclaiming space from fonts, margins or floats.

**Why this is recorded rather than silently dropped.** It is the sentence that most directly
answers *"what does the field learn"*, and it was cut for space, not because it is wrong. §3 and
Limitations both carry the claim, so nothing is unsupported — but if space frees up in a later
pass, this is the first thing that should go back in.
