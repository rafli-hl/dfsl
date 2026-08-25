"""Wall-clock for the figure-and-table suite, for the Reproducibility Statement.

The statement says the suite reproduces on a single commodity CPU with no accelerator,
but gives no runtime, so a reviewer cannot tell whether "reproducible" means an evening
or a week. This times it.

The timed set is defined, not hand-picked: every script the paper names in the text or in
a caption, plus the scripts that generate the tables the paper prints. Each runs in a
fresh interpreter, sequentially, on one machine with nothing else running, and its
wall-clock, exit status and output size go to ``results/research/runtime_suite.csv`` as it
finishes -- so a partial run is still a usable measurement.

Scripts that need the Kaggle-gated Jane parquet are marked; on a machine without it they
fail fast and the row records that, which is itself the number a reviewer wants (how much
of the suite runs data-free).

Usage::

    .venv/Scripts/python.exe scripts/research_runtime_suite.py [--only NAME ...]
"""

from __future__ import annotations

import argparse
import csv
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"
LOGS = RES / "runtime_logs"

# Arguments a script needs to reproduce the paper's configuration rather than its own
# default. Running the suite bare is what surfaced this: research_iterate_norm.py defaults
# to lr=2 while app:iternorm reports lr=8, so a bare run silently overwrites the artifact
# with a different experiment. Anything not listed here reproduces from its defaults.
ARGS: dict[str, list[str]] = {
    "research_iterate_norm.py": ["--lr", "8"],
}

# (script, needs Jane parquet, what it produces)
SUITE: list[tuple[str, bool, str]] = [
    # --- named in the paper ---
    ("research_predictability_check.py", True, "the 2x2 predictability decomposition"),
    ("research_review2_checks.py", True, "tab:residual real-data rows"),
    ("research_residual_surrogate.py", False, "tab:residual GARCH-surrogate rows"),
    ("research_null_normalization.py", True, "fig:nullcontrol, the three null controls"),
    ("research_iterate_norm.py", True, "fig:iternorm"),
    ("research_leakage_controls.py", True, "tab:leakage"),
    ("research_cap_sweep_jane.py", True, "the Jane cap frontier"),
    ("research_crypto_mechanism.py", False, "crypto tail decomposition"),
    ("research_crypto_algorithms.py", False, "crypto stability dichotomy"),
    ("research_synthetic.py", False, "fig:synthetic, known-tail streams"),
    ("research_jane_msweep.py", True, "fig:msweep"),
    ("research_tracker.py", True, "fig:tracker, tab:tracker"),
    ("research_tracker_bootstrap.py", True, "app:tracker paired bootstrap"),
    ("research_cm_normgd_equiv.py", True, "Cutkosky-Mehta beta=0 equivalence"),
    ("research_cm_widen.py", True, "Cutkosky-Mehta grid widening"),
    ("research_lr_widen.py", True, "learning-rate grid widening"),
    ("research_lr_curves_windows.py", True, "per-window lr curves"),
    ("research_grid_adequacy.py", True, "tab:grid"),
    ("research_rmsprop_adam.py", True, "app:adaptive"),
    ("research_review3_checks.py", True, "round-3 audit checks"),
    # --- generate the tables the paper prints ---
    ("research_batched_check.py", True, "tab:jane"),
    ("research_baselines.py", True, "tab:jane baseline rows"),
    ("research_table1_errorbars.py", True, "tab:jane error bars"),
    ("research_block_length.py", True, "block-length sensitivity"),
    ("research_jane_mini.py", False, "reviewer-runnable Jane path"),
    ("research_windows_replication.py", True, "ten-window baselines"),
    ("research_windows_tracker.py", True, "ten-window tracker rows"),
    ("research_c12_matched_table.py", True, "tab:replication, matched budget"),
    ("research_c12b_blockmed.py", True, "tab:replication block-median row"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None,
                    help="run just these script names")
    ap.add_argument("--timeout", type=float, default=None,
                    help="per-script timeout in seconds")
    args = ap.parse_args()

    LOGS.mkdir(parents=True, exist_ok=True)
    out = RES / "runtime_suite.csv"
    jane = (ROOT / "data" / "raw" / "jane" / "train.parquet").exists()

    print("=" * 88)
    print("RUNTIME SUITE")
    print(f"  python   {sys.version.split()[0]}   {platform.python_implementation()}")
    print(f"  machine  {platform.processor() or platform.machine()}  "
          f"({platform.system()} {platform.release()})")
    print(f"  jane parquet present: {jane}")
    print("=" * 88)

    # With --only, keep the rows already measured: a suite this long gets finished in
    # pieces, and a partial re-run must not delete the parts that already completed.
    rows: list[dict] = []
    if args.only and out.exists():
        with out.open(newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r["script"] not in args.only]
        print(f"  keeping {len(rows)} previously measured rows")
    todo = [s for s in SUITE if args.only is None or s[0] in args.only]
    t_all = time.perf_counter()
    for i, (name, needs_jane, produces) in enumerate(todo, 1):
        path = ROOT / "scripts" / name
        if not path.exists():
            print(f"[{i:2d}/{len(todo)}] {name:38s} MISSING")
            rows.append({"script": name, "seconds": "", "status": "missing",
                         "needs_jane": needs_jane, "produces": produces})
            _write(out, rows)
            continue
        print(f"[{i:2d}/{len(todo)}] {name:38s} ...", end="", flush=True)
        log = LOGS / (name.replace(".py", "") + ".log")
        t0 = time.perf_counter()
        try:
            with log.open("w", encoding="utf-8", errors="replace") as fh:
                cmd = [sys.executable, str(path), *ARGS.get(name, [])]
                fh.write("$ " + " ".join(cmd[1:]) + "\n\n")
                p = subprocess.run(cmd, cwd=str(ROOT),
                                   stdout=fh, stderr=subprocess.STDOUT,
                                   timeout=args.timeout)
            status = "ok" if p.returncode == 0 else f"exit {p.returncode}"
        except subprocess.TimeoutExpired:
            status = "timeout"
        dt = time.perf_counter() - t0
        print(f" {dt:8.1f}s  {status}")
        rows.append({"script": name, "seconds": round(dt, 1), "status": status,
                     "needs_jane": needs_jane, "produces": produces})
        _write(out, rows)

    this_run = time.perf_counter() - t_all

    def secs(r):
        try:
            return float(r["seconds"])
        except (TypeError, ValueError):
            return 0.0

    def jane(r):
        return str(r["needs_jane"]).lower() in ("true", "1")

    ok = [r for r in rows if r["status"] == "ok"]
    free = [r for r in ok if not jane(r)]
    total = sum(secs(r) for r in ok)
    print("-" * 88)
    print(f"  {len(ok)}/{len(rows)} scripts completed")
    print(f"  suite wall-clock      {total/60:8.1f} min ({total/3600:.2f} h)")
    if free:
        print(f"  data-free subset      {sum(secs(r) for r in free)/60:8.1f} min "
              f"({len(free)} scripts, no market data needed)")
    if args.only:
        print(f"  (this invocation ran {len(todo)} of them, in {this_run/60:.1f} min)")
    print(f"  [saved {out.relative_to(ROOT)}]")
    return 0


def _write(out: Path, rows: list[dict]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["script", "seconds", "status",
                                           "needs_jane", "produces"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
