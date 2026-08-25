"""C10C -- acceptance tests for the C-10 relative divergence criterion.

Registered in ``experiment_matrix.yaml`` (sixth document) at commit a55b599 BEFORE this
script was executed. The criterion itself is in ``research_divergence.py``.

Five pass/fail tests, all properties of the INSTRUMENT rather than of any threshold it
locates. No threshold search is run here; that is deliberately the next direction, so the
instrument is fixed before it is pointed at the questions it was built for.

    V1  reference sanity     -- zero and best-constant predictors are never divergent
    V2  detects true blowup  -- 100% recall against max||w|| > 1e6, an INDEPENDENT ground
                                truth (genuinely reachable only for uncapped methods)
    V3  monotone in P        -- no stable P above a divergent P on a ray; bisection needs it
    V4  non-vacuous          -- both classes present on every stream
    V5  kappa robustness     -- <10% of classifications move across kappa in {5, 10, 20}

Accepted only if all five pass on all three streams. On failure the criterion is REJECTED
and reported as such, not patched -- patching against a failed acceptance test with the
thresholds already known is how an instrument gets fitted to the answers.

Usage::

    python scripts/research_c10c_validate.py            # full run (~9 min)
    python scripts/research_c10c_validate.py --smoke    # fast sanity check
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

from research_baselines import anchor_perrow  # noqa: E402
from research_batched_check import group_boundaries  # noqa: E402
from research_c10t_synthetic import make_stream  # noqa: E402
from research_crypto_algorithms import diverged as crypto_diverged  # noqa: E402
from research_crypto_mechanism import load_features  # noqa: E402
from research_divergence import best_constant, relative_divergence  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS, _diverged as jane_diverged  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research" / "c10c"

# ---- registered design (experiment_matrix.yaml doc 6) ----------------------------
LRS = [0.5, 1.0, 2.0, 4.0, 8.0]
MS = [0.5, 2.0, 8.0, 32.0]
BLOWUP_LRS = [0.01, 0.1, 1.0, 4.0]
RAY_MS = [0.5, 2.0, 8.0, 32.0]
RAY_PS = list(np.geomspace(0.5, 128.0, 12))
KAPPAS = [5.0, 10.0, 20.0]
KAPPA_MAIN = 10.0
BLOWUP_WNORM = 1e6
GATE_TOL = 1e-9
DECAY, WINSOR = 0.99, 8.0


def run_tracked(X, y, wts, mode, cap, lr):
    """anchor_perrow's update, mirrored, plus max ||w||. Gate-checked before use."""
    d = X.shape[1]
    w = np.zeros(d)
    s = None
    k = 0
    preds = np.empty(len(y))
    wmax = 0.0
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i])
            preds[i] = pred
            k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0:
            continue
        if mode == "ogd":
            w = w - (lr / np.sqrt(k)) * g
        elif mode == "normgd":
            w = w - (lr / np.sqrt(k)) * (g / gn)
        else:
            sc = max(s if s is not None else gn, 1e-8)
            s = gn if s is None else DECAY * s + (1 - DECAY) * min(gn, WINSOR * s)
            ghat = g / sc
            gnn = float(np.linalg.norm(ghat))
            if gnn > cap:
                ghat = ghat * (cap / gnn)
            w = w - (lr / np.sqrt(k)) * ghat
        wn = float(np.linalg.norm(w))
        if not np.isfinite(wn):
            return preds, float("inf")
        wmax = max(wmax, wn)
    return preds, wmax


def gate(streams, log):
    log("\n" + "=" * 96)
    log("INSTRUMENTATION GATE (tracked runner vs anchor_perrow)")
    log("=" * 96)
    X, y, wts = streams[0]
    worst = 0.0
    for mode, cap, lr in [("snomd", 0.5, 0.5), ("snomd", 8.0, 2.0),
                          ("ogd", 0.0, 0.01), ("snomd", 1e9, 0.1)]:
        mine, _ = run_tracked(X, y, wts, mode, cap, lr)
        theirs = anchor_perrow(X, y, wts, mode, cap, lr)
        a, b = agg_r2(y, mine, wts), agg_r2(y, theirs, wts)
        diff = abs(float(a) - float(b))
        worst = max(worst, diff)
        log(f"  {mode:7s} cap={cap:<8g} lr={lr:<6g} diff={diff:.2e}")
    if not (worst <= GATE_TOL):
        raise SystemExit(f"HALT: gate FAILED (worst {worst:.3e}).")
    log(f"  GATE PASSED (worst {worst:.2e} <= {GATE_TOL:.0e})")


def load_streams(smoke, jane_rows):
    out = {}
    idx = [0, 4, 8]
    n_jane_rows = 20000 if smoke else jane_rows
    jane = []
    for i in idx:
        lo, hi = WINDOWS[i]
        ds = JaneStreetDataset(date_range=(lo, hi), max_rows=n_jane_rows, standardize=True)
        jane.append((ds.X, ds.y, ds.weights))
    out["jane"] = jane

    X, y, w, day_id, dt, cols = load_features()
    y = y / float(np.std(y))
    n = len(y)
    win, nw = 6000, 10
    gap = (n - nw * win) // (nw - 1)
    wins = [(i * (win + gap), i * (win + gap) + win) for i in range(nw)]
    out["crypto"] = [(X[a:b], y[a:b], w[a:b]) for a, b in (wins[i] for i in idx)]

    T = 4000 if smoke else 20000
    out["synthetic"] = [make_stream(s, 1.5, T=T) for s in (1000, 1004, 1008)]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    # Registered design says 150000. Amendment 2026-08-23 (see experiment_matrix.yaml
    # doc 6, amendments) allows a reduced Jane row cap on COST grounds only; V1-V5 are
    # pass/fail properties of the instrument and do not depend on window length.
    ap.add_argument("--jane-rows", type=int, default=150000)
    args = ap.parse_args()
    global LRS, MS, RAY_MS, RAY_PS, BLOWUP_LRS
    if args.smoke:
        LRS, MS = [0.5, 4.0], [0.5, 8.0]
        RAY_MS, RAY_PS = [0.5, 8.0], list(np.geomspace(0.5, 128.0, 4))
        BLOWUP_LRS = [0.1, 4.0]
        print(">>> SMOKE MODE <<<")

    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    lines: list[str] = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

    log("=" * 96)
    log("C10C -- acceptance tests for the C-10 relative divergence criterion")
    log(f"jane_rows={args.jane_rows}" + ("  (REDUCED -- registered amendment, cost grounds)" if args.jane_rows != 150000 else ""))
    log("=" * 96)
    streams = load_streams(args.smoke, args.jane_rows)
    gate(streams["synthetic"], log)

    rows: list[dict] = []
    report: dict = {"kappa_main": KAPPA_MAIN, "kappas": KAPPAS, "streams": {}}

    for sname, wins in streams.items():
        log(f"\n########## STREAM: {sname}  ({len(wins)} windows) ##########")
        # ---- capped probe grid + blow-up probes ----
        configs = [("snomd", M, lr) for lr in LRS for M in MS]
        configs += [("ogd", 0.0, lr) for lr in BLOWUP_LRS]
        configs += [("snomd", 1e9, lr) for lr in BLOWUP_LRS]
        for wi, (X, y, wts) in enumerate(wins):
            for mode, cap, lr in configs:
                preds, wmax = run_tracked(X, y, wts, mode, cap, lr)
                rec = {"stream": sname, "window": wi, "mode": mode, "cap": cap, "lr": lr,
                       "P": lr * cap if mode == "snomd" and cap < 1e8 else None,
                       "w_max": wmax, "true_blowup": bool(wmax > BLOWUP_WNORM),
                       "jane_div": bool(jane_diverged(y, preds, wts)),
                       "crypto_div": bool(crypto_diverged(y, preds, wts))}
                for kap in KAPPAS:
                    d = relative_divergence(y, preds, wts, kap)
                    rec[f"new_div_k{kap:g}"] = bool(d["diverged"])
                    if kap == KAPPA_MAIN:
                        rec.update({"L_ratio": d["L_ratio"], "P_ratio": d["P_ratio"]})
                rows.append(rec)
            log(f"  window {wi}: {len(configs)} configs done ({time.time()-t0:.0f}s)")

        # ---- V1 reference predictors ----
        v1 = []
        for wi, (X, y, wts) in enumerate(wins):
            for label, ref in (("zero", np.zeros(len(y))),
                               ("best_constant", np.full(len(y), best_constant(y, wts)))):
                d = relative_divergence(y, ref, wts, KAPPA_MAIN)
                v1.append({"stream": sname, "window": wi, "predictor": label,
                           "new_div": bool(d["diverged"]),
                           "jane_div": bool(jane_diverged(y, ref, wts)),
                           "L_ratio": d["L_ratio"], "P_ratio": d["P_ratio"]})
        report.setdefault("v1_rows", []).extend(v1)

        # ---- V3 rays ----
        v3 = []
        for M in RAY_MS:
            classes = []
            for P in RAY_PS:
                lr = P / M
                anydiv = False
                for (X, y, wts) in wins:
                    preds, _ = run_tracked(X, y, wts, "snomd", M, lr)
                    if relative_divergence(y, preds, wts, KAPPA_MAIN)["diverged"]:
                        anydiv = True
                        break
                classes.append((P, anydiv))
            stable = [p for p, dv in classes if not dv]
            div = [p for p, dv in classes if dv]
            ok = (not stable) or (not div) or (max(stable) < min(div))
            v3.append({"stream": sname, "M": M, "monotone": bool(ok),
                       "n_stable": len(stable), "n_div": len(div)})
            log(f"  V3 ray M={M:<5g} stable={len(stable):2d} divergent={len(div):2d}  "
                f"{'OK' if ok else 'VIOLATION'}")
        report.setdefault("v3_rows", []).extend(v3)

    df = pl.DataFrame(rows, strict=False)
    df.write_csv(RES / ("c10c_probe_smoke.csv" if args.smoke else "c10c_probe.csv"))

    # ================= acceptance evaluation =================
    log("\n" + "=" * 96)
    log("ACCEPTANCE TESTS")
    log("=" * 96)
    v1df = pl.DataFrame(report["v1_rows"])
    v3df = pl.DataFrame(report["v3_rows"])
    results = {}

    bad1 = v1df.filter(pl.col("new_div"))
    results["V1"] = bad1.height == 0
    log(f"\nV1 reference sanity: {v1df.height} reference runs, "
        f"{bad1.height} wrongly flagged divergent -> {'PASS' if results['V1'] else 'FAIL'}")
    jb = v1df.filter(pl.col("jane_div")).height
    log(f"   (for contrast, the inherited Jane rule flags {jb}/{v1df.height} of them)")

    tb = df.filter(pl.col("true_blowup"))
    missed = tb.filter(~pl.col(f"new_div_k{KAPPA_MAIN:g}"))
    results["V2"] = tb.height > 0 and missed.height == 0
    log(f"\nV2 detects true blow-up: {tb.height} runs with max||w||>1e6, "
        f"{missed.height} missed -> {'PASS' if results['V2'] else 'FAIL'}")
    for s in df["stream"].unique().to_list():
        n = tb.filter(pl.col("stream") == s).height
        log(f"   {s}: {n} true blow-ups")

    viol = v3df.filter(~pl.col("monotone"))
    results["V3"] = viol.height == 0
    log(f"\nV3 monotone in P: {v3df.height} rays, {viol.height} violations "
        f"-> {'PASS' if results['V3'] else 'FAIL'}")

    v4ok = True
    capped = df.filter((pl.col("mode") == "snomd") & (pl.col("cap") < 1e8))
    for s in capped["stream"].unique().to_list():
        sub = capped.filter(pl.col("stream") == s)
        both = sub[f"new_div_k{KAPPA_MAIN:g}"].any() and (~sub[f"new_div_k{KAPPA_MAIN:g}"]).any()
        v4ok &= bool(both)
        log(f"\nV4 non-vacuous [{s}]: divergent={sub[f'new_div_k{KAPPA_MAIN:g}'].sum()}"
            f"/{sub.height}  -> {'both classes' if both else 'ONE CLASS ONLY'}")
    results["V4"] = bool(v4ok)
    log(f"V4 overall -> {'PASS' if results['V4'] else 'FAIL'}")

    v5ok = True
    log("")
    for s in capped["stream"].unique().to_list():
        sub = capped.filter(pl.col("stream") == s)
        a = sub["new_div_k5"].to_numpy()
        b = sub["new_div_k10"].to_numpy()
        c = sub["new_div_k20"].to_numpy()
        frac = float(np.mean((a != b) | (b != c)))
        v5ok &= frac < 0.10
        log(f"V5 kappa robustness [{s}]: {frac:.3f} of {sub.height} classifications move "
            f"across kappa in {{5,10,20}} -> {'ok' if frac < 0.10 else 'TOO SENSITIVE'}")
    results["V5"] = bool(v5ok)
    log(f"V5 overall -> {'PASS' if results['V5'] else 'FAIL'}")

    accepted = all(results.values())
    log("\n" + "=" * 96)
    log(f"VERDICT: criterion {'ACCEPTED' if accepted else 'REJECTED'}   "
        + "  ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in results.items()))
    log("=" * 96)

    # descriptive: agreement with the inherited criteria
    log("\nDescriptive -- agreement with inherited criteria on the capped grid:")
    for s in capped["stream"].unique().to_list():
        sub = capped.filter(pl.col("stream") == s)
        n = sub.height
        new = sub[f"new_div_k{KAPPA_MAIN:g}"].to_numpy()
        log(f"  {s:10s} new={new.sum():3d}/{n}  jane={sub['jane_div'].sum():3d}/{n}  "
            f"crypto={sub['crypto_div'].sum():3d}/{n}   "
            f"agree(new,jane)={np.mean(new == sub['jane_div'].to_numpy()):.2f}  "
            f"agree(new,crypto)={np.mean(new == sub['crypto_div'].to_numpy()):.2f}")

    report["results"] = results
    report["accepted"] = bool(accepted)
    report["wallclock_sec"] = round(time.time() - t0, 1)
    (RES / ("c10c_report_smoke.json" if args.smoke else "c10c_report.json")).write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")
    (RES / ("c10c_run_smoke.log" if args.smoke else "c10c_run.log")).write_text(
        "\n".join(lines), encoding="utf-8")
    log(f"\n[saved results/research/c10c/]  wallclock {report['wallclock_sec']}s")


if __name__ == "__main__":
    main()
