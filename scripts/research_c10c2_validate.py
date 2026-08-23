"""C10C2 -- corrected acceptance suite for the C-10 relative divergence criterion.

Registered in ``experiment_matrix.yaml`` (seventh document) at commit 08bd66f BEFORE this
script was executed. The criterion in ``research_divergence.py`` is **unchanged**; only the
suite moves.

Read the provenance disclosure in the registration. In short: the corrected V4 is expected
to pass and re-running it is bookkeeping, not evidence. The evidential weight is **V6**,
which is new and which the criterion has never faced.

    V1  reference sanity      unchanged (blind in C10C, passed)
    V2  blow-up recall        unchanged (blind in C10C, passed)
    V3  monotone in P         unchanged (blind in C10C, passed)
    V4  non-vacuity           RESPECIFIED -- conditional on the capped grid containing a
                              ground-truth blow-up, decided by max||w|| so the criterion
                              cannot influence its own exemption
    V5  kappa robustness      unchanged (blind in C10C, passed)
    V6  truncation stability  NEW AND BLIND -- comparative against the inherited rule, since
                              halving T genuinely changes the trajectory and an absolute bar
                              would measure the algorithm rather than the criterion

Usage::

    python scripts/research_c10c2_validate.py --jane-rows 40000
    python scripts/research_c10c2_validate.py --smoke
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
from research_divergence import best_constant, relative_divergence  # noqa: E402
from research_windows_replication import _diverged as jane_diverged  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research" / "c10c2"

KAPPA_MAIN = base.KAPPA_MAIN
KAPPAS = base.KAPPAS
BLOWUP_WNORM = base.BLOWUP_WNORM
V6_MARGIN = 0.05


def classify_grid(wins, configs, kappa=KAPPA_MAIN, truncate=False):
    """Run every config on every window; return one record per (config, window)."""
    out = []
    for wi, (X, y, wts) in enumerate(wins):
        if truncate:
            h = len(y) // 2
            X, y, wts = X[:h], y[:h], wts[:h]
        for mode, cap, lr in configs:
            preds, wmax = base.run_tracked(X, y, wts, mode, cap, lr)
            d = relative_divergence(y, preds, wts, kappa)
            rec = {"window": wi, "mode": mode, "cap": cap, "lr": lr,
                   "w_max": wmax, "true_blowup": bool(wmax > BLOWUP_WNORM),
                   "new_div": bool(d["diverged"]), "L_ratio": d["L_ratio"],
                   "P_ratio": d["P_ratio"],
                   "jane_div": bool(jane_diverged(y, preds, wts))}
            for kap in KAPPAS:
                rec[f"new_div_k{kap:g}"] = bool(
                    relative_divergence(y, preds, wts, kap)["diverged"])
            out.append(rec)
    return out


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
    log("C10C2 -- corrected acceptance suite (criterion itself UNCHANGED)")
    log(f"jane_rows={args.jane_rows}   V4 respecified, V6 new and blind")
    log("=" * 96)
    streams = base.load_streams(args.smoke, args.jane_rows)
    base.gate(streams["synthetic"], log)

    capped = [("snomd", M, lr) for lr in base.LRS for M in base.MS]
    blowup = ([("ogd", 0.0, lr) for lr in base.BLOWUP_LRS]
              + [("snomd", 1e9, lr) for lr in base.BLOWUP_LRS])

    report: dict = {"kappa_main": KAPPA_MAIN, "jane_rows": args.jane_rows, "streams": {}}
    rows: list[dict] = []
    v1_rows, v3_rows = [], []

    for sname, wins in streams.items():
        log(f"\n########## STREAM: {sname} ##########")
        full = classify_grid(wins, capped + blowup)
        for r in full:
            rows.append({"stream": sname, "phase": "full", **r})
        log(f"  full grid: {len(full)} runs ({time.time()-t0:.0f}s)")

        half = classify_grid(wins, capped, truncate=True)
        for r in half:
            rows.append({"stream": sname, "phase": "half", **r})
        log(f"  truncated grid: {len(half)} runs ({time.time()-t0:.0f}s)")

        for wi, (X, y, wts) in enumerate(wins):
            for label, ref in (("zero", np.zeros(len(y))),
                               ("best_constant", np.full(len(y), best_constant(y, wts)))):
                d = relative_divergence(y, ref, wts, KAPPA_MAIN)
                v1_rows.append({"stream": sname, "window": wi, "predictor": label,
                                "new_div": bool(d["diverged"]),
                                "jane_div": bool(jane_diverged(y, ref, wts))})

        for M in base.RAY_MS:
            classes = []
            for P in base.RAY_PS:
                lr = P / M
                anydiv = False
                for (X, y, wts) in wins:
                    preds, _ = base.run_tracked(X, y, wts, "snomd", M, lr)
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
    df.write_csv(RES / ("c10c2_probe_smoke.csv" if args.smoke else "c10c2_probe.csv"))
    v1df, v3df = pl.DataFrame(v1_rows), pl.DataFrame(v3_rows)

    # ======================== acceptance ========================
    log("\n" + "=" * 96)
    log("ACCEPTANCE TESTS")
    log("=" * 96)
    res = {}
    full_df = df.filter(pl.col("phase") == "full")
    cap_full = full_df.filter((pl.col("mode") == "snomd") & (pl.col("cap") < 1e8))

    res["V1"] = v1df.filter(pl.col("new_div")).height == 0
    log(f"\nV1 reference sanity: {v1df.filter(pl.col('new_div')).height}/{v1df.height} "
        f"wrongly flagged -> {'PASS' if res['V1'] else 'FAIL'}  "
        f"(inherited Jane rule flags {v1df.filter(pl.col('jane_div')).height})")

    tb = full_df.filter(pl.col("true_blowup"))
    missed = tb.filter(~pl.col("new_div")).height
    res["V2"] = tb.height > 0 and missed == 0
    log(f"\nV2 blow-up recall: {tb.height} true blow-ups, {missed} missed "
        f"-> {'PASS' if res['V2'] else 'FAIL'}")

    res["V3"] = v3df.filter(~pl.col("monotone")).height == 0
    log(f"\nV3 monotone in P: {v3df.height} rays, "
        f"{v3df.filter(~pl.col('monotone')).height} violations "
        f"-> {'PASS' if res['V3'] else 'FAIL'}")

    log("\nV4 non-vacuity (RESPECIFIED -- applicability from max||w||>1e6, not the criterion):")
    v4_applicable, v4_ok = [], True
    for s in cap_full["stream"].unique().to_list():
        sub = cap_full.filter(pl.col("stream") == s)
        gt = sub.filter(pl.col("true_blowup")).height
        if gt == 0:
            log(f"   {s:10s} capped grid contains 0 ground-truth blow-ups "
                f"(max||w||={sub['w_max'].max():.1f}) -> NOT APPLICABLE")
            continue
        v4_applicable.append(s)
        both = bool(sub["new_div"].any() and (~sub["new_div"]).any())
        v4_ok &= both
        log(f"   {s:10s} {gt} ground-truth blow-ups in the capped grid; "
            f"criterion divergent={sub['new_div'].sum()}/{sub.height} "
            f"-> {'both classes' if both else 'ONE CLASS ONLY'}")
    res["V4"] = bool(v4_ok and v4_applicable)
    log(f"   applicable on {v4_applicable or 'NO STREAM'} -> "
        f"{'PASS' if res['V4'] else 'FAIL'}")

    v5_ok = True
    log("")
    for s in cap_full["stream"].unique().to_list():
        sub = cap_full.filter(pl.col("stream") == s)
        a, b, c = (sub[f"new_div_k{k:g}"].to_numpy() for k in KAPPAS)
        frac = float(np.mean((a != b) | (b != c)))
        v5_ok &= frac < 0.10
        log(f"V5 kappa robustness [{s}]: {frac:.3f} move -> {'ok' if frac < 0.10 else 'TOO SENSITIVE'}")
    res["V5"] = bool(v5_ok)
    log(f"V5 overall -> {'PASS' if res['V5'] else 'FAIL'}")

    log("\nV6 truncation stability (NEW, BLIND -- comparative against the inherited rule):")
    v6_ok = True
    v6_detail = {}
    for s in cap_full["stream"].unique().to_list():
        f = df.filter((pl.col("stream") == s) & (pl.col("phase") == "full")
                      & (pl.col("mode") == "snomd") & (pl.col("cap") < 1e8)) \
              .sort(["window", "lr", "cap"])
        h = df.filter((pl.col("stream") == s) & (pl.col("phase") == "half")) \
              .sort(["window", "lr", "cap"])
        agree_new = float(np.mean(f["new_div"].to_numpy() == h["new_div"].to_numpy()))
        agree_jane = float(np.mean(f["jane_div"].to_numpy() == h["jane_div"].to_numpy()))
        ok = agree_new >= agree_jane - V6_MARGIN
        v6_ok &= ok
        v6_detail[s] = {"agree_new": agree_new, "agree_jane": agree_jane, "pass": bool(ok)}
        log(f"   {s:10s} agreement new={agree_new:.3f}  jane={agree_jane:.3f}  "
            f"(new >= jane-{V6_MARGIN}) -> {'ok' if ok else 'WORSE THAN INHERITED'}")
    res["V6"] = bool(v6_ok)
    log(f"V6 overall -> {'PASS' if res['V6'] else 'FAIL'}")

    accepted = all(res.values())
    log("\n" + "=" * 96)
    log(f"VERDICT: criterion {'ACCEPTED' if accepted else 'REJECTED'}   "
        + "  ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in res.items()))
    if accepted:
        log("QUALIFIED: V4 was corrected with knowledge of the failure it corrects, so the")
        log("blind evidence is V1/V2/V3/V5 from C10C plus V6 from here.")
    log("=" * 96)

    report.update({"results": res, "accepted": bool(accepted), "v4_applicable": v4_applicable,
                   "v6": v6_detail, "wallclock_sec": round(time.time() - t0, 1)})
    (RES / ("c10c2_report_smoke.json" if args.smoke else "c10c2_report.json")).write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")
    (RES / ("c10c2_run_smoke.log" if args.smoke else "c10c2_run.log")).write_text(
        "\n".join(lines), encoding="utf-8")
    log(f"\n[saved results/research/c10c2/]  wallclock {report['wallclock_sec']}s")


if __name__ == "__main__":
    main()
