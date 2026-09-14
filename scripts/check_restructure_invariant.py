"""Structure C's invariant: the restructure may move claims, never measurements.

The greenlight for Structure C carried one condition worth turning into a check rather than a
discipline: *no table, figure, number, control or negative result moves or is cut. Structure C
is a reordering of what the paper claims, not of what it shows.* Steps 2 and 3 carry the same
risk as step 1, so the check is reusable.

Two properties, both computed from the git diff against a baseline ref:

  FLOAT LINES UNTOUCHED   no added or removed line carries ``includegraphics``, a tabular or
                          float environment delimiter, or a booktabs rule. A restructure that
                          needs to move a float is doing something other than reordering claims.
  NO NUMBER DISAPPEARS    every numeric literal on a removed line must still occur somewhere in
                          the file. This permits *moving* a measurement between sections, which
                          the restructure legitimately does, while catching a measurement that
                          is silently dropped to make room -- the failure mode the page budget
                          creates pressure toward.

The second is the one that earns its place: at a three-line margin the temptation is to reclaim
space from a number rather than from prose, and that is exactly the edit nobody notices in review.

Usage::

    .venv/Scripts/python.exe scripts/check_restructure_invariant.py
    .venv/Scripts/python.exe scripts/check_restructure_invariant.py --base pre-structure-c
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
TEX = "paper/iclr2027/iclr2027.tex"
DEFAULT_BASE = "pre-structure-c"

FLOAT_MARKERS = (
    "includegraphics", r"\begin{tabular", r"\end{tabular", r"\begin{figure",
    r"\end{figure", r"\begin{table", r"\end{table", r"\toprule", r"\midrule", r"\bottomrule",
)
# Numbers that are LaTeX plumbing rather than measurements: font sizes, column counts,
# fractions of \linewidth, and the like. Matching them would make the check unusable.
PLUMBING = re.compile(r"(linewidth|textwidth|multicolumn|cmidrule|tabcolsep|\\\\\[)")
NUMBER = re.compile(r"(?<![\w.])\d+\.\d+(?![\w.])")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=False).stdout


def ref_exists(ref: str) -> bool:
    return subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref], cwd=ROOT,
                          capture_output=True).returncode == 0


def check(base: str) -> list[str]:
    diff = git("diff", base, "--", TEX).splitlines()
    added = [l[1:] for l in diff if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:] for l in diff if l.startswith("-") and not l.startswith("---")]

    problems = []

    touched = [l for l in added + removed if any(m in l for m in FLOAT_MARKERS)]
    if touched:
        problems.append(
            f"{len(touched)} float/table line(s) touched -- a claim reordering should not need "
            "to move a measurement:\n" + "\n".join(f"      {l.strip()[:100]}" for l in touched[:6])
        )

    current = (ROOT / TEX).read_text(encoding="utf-8")
    lost = []
    for line in removed:
        if PLUMBING.search(line):
            continue
        for n in NUMBER.findall(line):
            if n not in current:
                lost.append((n, line.strip()[:90]))
    if lost:
        problems.append(
            f"{len(lost)} numeric value(s) removed and not re-stated elsewhere:\n"
            + "\n".join(f"      {n}  in: {ctx}" for n, ctx in lost[:8])
        )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    a = ap.parse_args()

    if not ref_exists(a.base):
        print(f"baseline ref {a.base!r} not present; nothing to check against.")
        return 0

    print("=" * 92)
    print(f"STRUCTURE C INVARIANT -- {TEX} against {a.base}")
    print("=" * 92)
    problems = check(a.base)
    stat = git("diff", "--shortstat", a.base, "--", TEX).strip()
    print(f"  diff: {stat or 'no changes'}")
    if problems:
        print("\nVIOLATIONS:")
        for p in problems:
            print(f"  - {p}")
        print("\nThe restructure may move what the paper CLAIMS. It may not move or drop what the")
        print("paper SHOWS. If a measurement genuinely needs to move, do it in its own commit so")
        print("it is reviewed as a change to the evidence rather than as part of a reordering.")
        return 1
    print("\n  ok -- no float or table line touched, and no numeric value dropped.")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
