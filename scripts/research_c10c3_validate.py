"""C10C3 -- final acceptance suite for the C-10 relative divergence criterion.

Registered in ``experiment_matrix.yaml`` (eighth document) at commit 125c1a7 BEFORE this
script was executed. The criterion in ``research_divergence.py`` is **unchanged**; only the
suite moves.

V4 is dropped on the user's explicit instruction (see the registration's provenance
disclosure). With V1, V2, V3, V5 and V6 all having passed already, acceptance on those five
is a foregone conclusion and re-running them is bookkeeping. The two tests that carry
evidence here are new and blind:

    V8  SCALE INVARIANCE -- the property C-10 exists for, never yet tested. Multiply both y
        and preds by c in {1e-3, 1, 1e3}: a pure change of units, which a ratio-based
        criterion must be exactly invariant to and a unit-carrying one must not. Applied to
        the criterion FUNCTION; no learner is re-run, and this is NOT a claim that the
        algorithm is equivariant to rescaling the target.
    V7  CLAUSE NECESSITY (diagnostic, not a gate) -- does the peak clause ever change a
        decision the aggregate clause did not already make?

Usage::

    python scripts/research_c10c3_validate.py --jane-rows 40000
    python scripts/research_c10c3_validate.py --smoke
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import research_c10c_validate as base  # noqa: E402
from research_divergence import KAPPA_DEFAULT, best_constant, relative_divergence  # noqa: E402
from research_windows_replication import _diverged as jane_diverged  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research" / "c10c3"

KAPPAS = base.KAPPAS
KAPPA_MAIN = base.KAPPA_MAIN
BLOWUP_WNORM = base.BLOWUP_WNORM
V6_MARGIN = 0.05
V8_SCALES = [1e-3, 1.0, 1e3]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--jane-rows", type=int, default=40000)
    args = ap.parse_args()
    if args.smoke:
        base.LRS, base.MS = [0.5, 4.0], [0.5, 8.0]
        base.RAY_MS = [0.5, 8.0]
        base.RAY_PS = list(np.geomspace(0.5, 128.0, 4))
        base.BLOWUP_LRS = [0.1, 4.0]
        print(">>> SMOKE MODE <<<")

    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    lines: list[str] = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

    log("=" * 96)
    log("C10C3 -- final acceptance suite (criterion UNCHANGED; V4 dropped by user decision)")
    log(f"jane_rows={args.jane_rows}   V7 and V8 are new and blind")
    log("=" * 96)
    streams = base.load_streams(args.smoke, args.jane_rows)
    base.gate(streams["synthetic"], log)

    capped = [("snomd", M, lr) for lr in base.LRS for M in base.MS]
    blowup = ([("ogd", 0.0, lr) for lr in base.BLOWUP_LRS]
              + [("snomd", 1e9, lr) for lr in base.BLOWUP_LRS])

    rows: list[dict] = []
    v1_rows, v3_rows = [], []

    for sname, wins in streams.items():
        log(f"\n########## STREAM: {sname} ##########")
        for phase, cfgs, trunc in (("full", capped + blowup, False), ("half", capped, True)):
            for wi, (X, y, wts) in enumerate(wins):
                if trunc:
                    h = len(y) // 2
                    X, y, wts = X[:h], y[:h], wts[:h]
                for mode, cap, lr in cfgs:
                    preds, wmax = base.run_tracked(X, y, wts, mode, cap, lr)
                    d = relative_divergence(y, preds, wts, KAPPA_MAIN)
                    rec = {"stream": sname, "phase": phase, "window": wi, "mode": mode,
                           "cap": cap, "lr": lr, "w_max": wmax,
                           "true_blowup": bool(wmax > BLOWUP_WNORM),
                           "new_div": bool(d["diverged"]),
                           "by_L": bool(d.get("by_L", False)), "by_P": bool(d.get("by_P", False)),
                           "L_ratio": d["L_ratio"], "P_ratio": d["P_ratio"],
                           "jane_div": bool(jane_diverged(y, preds, wts))}
                    for kap in KAPPAS:
                        rec[f"new_div_k{kap:g}"] = bool(
                            relative_divergence(y, preds, wts, kap)["diverged"])
                    # ---- V8: pure change of units on (y, preds) ----
                    for c in V8_SCALES:
                        rec[f"new_div_c{c:g}"] = bool(
                            relative_divergence(y * c, preds * c, wts, KAPPA_MAIN)["diverged"])
                        rec[f"jane_div_c{c:g}"] = bool(jane_diverged(y * c, preds * c, wts))
                    rows.append(rec)
            log(f"  {phase}: done ({time.time()-t0:.0f}s)")

        for wi, (X, y, wts) in enumerate(wins):
            for label, ref in (("zero", np.zeros(len(y))),
                               ("best_constant", np.full(len(y), best_constant(y, wts)))):
                d = relative_divergence(y, ref, wts, KAPPA_MAIN)
                v1_rows.append({"stream": sname, "predictor": label,
                                "new_div": bool(d["diverged"]),
                                "jane_div": bool(jane_diverged(y, ref, wts))})

        for M in base.RAY_MS:
            classes = []
            for P in base.RAY_PS:
                anydiv = False
                for (X, y, wts) in wins:
                    preds, _ = base.run_tracked(X, y, wts, "snomd", M, P / M)
                    if relative_divergence(y, preds, wts, KAPPA_MAIN)["diverged"]:
                        anydiv = True
                        break
                classes.append((P, anydiv))
            st = [p for p, d in classes if not d]
            dv = [p for p, d in classes if d]
            v3_rows.append({"stream": sname, "M": M,
                            "monotone": bool((not st) or (not dv) or max(st) < min(dv))})
        log(f"  rays done ({time.time()-t0:.0f}s)")

    df = pl.DataFrame(rows, strict=False)
    df.write_csv(RES / ("c10c3_probe_smoke.csv" if args.smoke else "c10c3_probe.csv"))
    v1df, v3df = pl.DataFrame(v1_rows), pl.DataFrame(v3_rows)
    full = df.filter(pl.col("phase") == "full")
    cap_full = full.filter((pl.col("mode") == "snomd") & (pl.col("cap") < 1e8))

    log("\n" + "=" * 96)
    log("ACCEPTANCE TESTS  (V4 dropped by user decision -- see registration)")
    log("=" * 96)
    res = {}

    res["V1"] = v1df.filter(pl.col("new_div")).height == 0
    log(f"\nV1 reference sanity: {v1df.filter(pl.col('new_div')).height}/{v1df.height} flagged "
        f"-> {'PASS' if res['V1'] else 'FAIL'}   "
        f"(inherited rule flags {v1df.filter(pl.col('jane_div')).height})")

    tb = full.filter(pl.col("true_blowup"))
    res["V2"] = tb.height > 0 and tb.filter(~pl.col("new_div")).height == 0
    log(f"\nV2 blow-up recall: {tb.height} true blow-ups, "
        f"{tb.filter(~pl.col('new_div')).height} missed -> {'PASS' if res['V2'] else 'FAIL'}")

    res["V3"] = v3df.filter(~pl.col("monotone")).height == 0
    log(f"\nV3 monotone in P: {v3df.height} rays, "
        f"{v3df.filter(~pl.col('monotone')).height} violations -> {'PASS' if res['V3'] else 'FAIL'}")

    v5 = True
    log("")
    for s in cap_full["stream"].unique().to_list():
        sub = cap_full.filter(pl.col("stream") == s)
        a, b, c = (sub[f"new_div_k{k:g}"].to_numpy() for k in KAPPAS)
        frac = float(np.mean((a != b) | (b != c)))
        v5 &= frac < 0.10
        log(f"V5 kappa robustness [{s}]: {frac:.3f} move -> {'ok' if frac < 0.10 else 'TOO SENSITIVE'}")
    res["V5"] = bool(v5)
    log(f"V5 overall -> {'PASS' if res['V5'] else 'FAIL'}")

    v6, v6d = True, {}
    log("")
    for s in cap_full["stream"].unique().to_list():
        f = df.filter((pl.col("stream") == s) & (pl.col("phase") == "full")
                      & (pl.col("mode") == "snomd") & (pl.col("cap") < 1e8)).sort(["window", "lr", "cap"])
        h = df.filter((pl.col("stream") == s) & (pl.col("phase") == "half")).sort(["window", "lr", "cap"])
        an = float(np.mean(f["new_div"].to_numpy() == h["new_div"].to_numpy()))
        aj = float(np.mean(f["jane_div"].to_numpy() == h["jane_div"].to_numpy()))
        ok = an >= aj - V6_MARGIN
        v6 &= ok
        v6d[s] = {"new": an, "jane": aj, "pass": bool(ok)}
        log(f"V6 truncation [{s}]: new={an:.3f} jane={aj:.3f} -> {'ok' if ok else 'WORSE'}")
    res["V6"] = bool(v6)
    log(f"V6 overall -> {'PASS' if res['V6'] else 'FAIL'}")

    # ---------------- V8: scale invariance (NEW, BLIND) ----------------
    log("\nV8 scale invariance (NEW, BLIND -- units change on (y, preds), criterion function):")
    v8, v8d = True, {}
    for s in df["stream"].unique().to_list():
        sub = df.filter(pl.col("stream") == s)
        cols_new = [sub[f"new_div_c{c:g}"].to_numpy() for c in V8_SCALES]
        cols_jane = [sub[f"jane_div_c{c:g}"].to_numpy() for c in V8_SCALES]
        inv_new = float(np.mean((cols_new[0] == cols_new[1]) & (cols_new[1] == cols_new[2])))
        inv_jane = float(np.mean((cols_jane[0] == cols_jane[1]) & (cols_jane[1] == cols_jane[2])))
        ok = inv_new == 1.0
        v8 &= ok
        v8d[s] = {"new": inv_new, "jane": inv_jane, "pass": bool(ok)}
        log(f"   {s:10s} invariant fraction  new={inv_new:.3f}  inherited={inv_jane:.3f}  "
            f"-> {'ok' if ok else 'NOT INVARIANT'}")
    res["V8"] = bool(v8)
    log(f"V8 overall -> {'PASS' if res['V8'] else 'FAIL'}")

    # ---------------- V7: clause necessity (DIAGNOSTIC) ----------------
    log("\nV7 clause necessity (DIAGNOSTIC, not a gate):")
    v7d, p_only_total = {}, 0
    for s in df["stream"].unique().to_list():
        sub = df.filter((pl.col("stream") == s) & pl.col("new_div"))
        p_only = sub.filter(pl.col("by_P") & ~pl.col("by_L")).height
        l_only = sub.filter(pl.col("by_L") & ~pl.col("by_P")).height
        both = sub.filter(pl.col("by_L") & pl.col("by_P")).height
        p_only_total += p_only
        v7d[s] = {"P_only": p_only, "L_only": l_only, "both": both, "divergent": sub.height}
        log(f"   {s:10s} divergent={sub.height:3d}   by P only={p_only:3d}   "
            f"by L only={l_only:3d}   by both={both:3d}")
    reducible = p_only_total == 0
    log(f"   => peak clause changed {p_only_total} decisions across all streams.")
    if reducible:
        log("   => REDUCIBLE: on this evidence the criterion collapses to its aggregate")
        log("      clause alone; the peak machinery and kappa carry no weight, and V5 is")
        log("      vacuous rather than passed. (Consequence fixed in the registration.)")

    accepted = all(res.values())
    log("\n" + "=" * 96)
    log(f"VERDICT: criterion {'ACCEPTED' if accepted else 'REJECTED'}   "
        + "  ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in res.items()))
    if accepted:
        log("QUALIFICATIONS: V1/V2/V3/V5 blind in C10C; V6 blind in C10C2; V8 blind here;")
        log("V4 removed by user decision rather than by evidence.")
        if reducible:
            log("AND: V7 shows the peak clause is inert on this evidence -- see above.")
    log("=" * 96)

    report = {"results": res, "accepted": bool(accepted), "v6": v6d, "v8": v8d,
              "v7": v7d, "v7_reducible": bool(reducible), "jane_rows": args.jane_rows,
              "wallclock_sec": round(time.time() - t0, 1)}
    (RES / ("c10c3_report_smoke.json" if args.smoke else "c10c3_report.json")).write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")
    (RES / ("c10c3_run_smoke.log" if args.smoke else "c10c3_run.log")).write_text(
        "\n".join(lines), encoding="utf-8")
    log(f"\n[saved results/research/c10c3/]  wallclock {report['wallclock_sec']}s")


if __name__ == "__main__":
    main()
