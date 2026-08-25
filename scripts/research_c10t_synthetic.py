"""C10T -- the clean test of C-8 on the synthetic suite.

Preregistered in ``experiment_matrix.yaml`` (fifth document, direction C10T), committed at
4cdd9d3 BEFORE this script was executed. Read the provenance disclosure there first: the
frozen level ``q* = p99`` came from a post-hoc computation in C10R, and the synthetic suite
is the only stream left that played no part in generating C-8.

Two things are new relative to C10R and both were required by its postmortem.

* The divergence criterion is **state-based**: non-finite iterate norm, or
  ``max_t ||w_t|| > 1e8``. That is the quantity ``thm:stability`` bounds. It needs no
  per-stream calibration, which is exactly what made the inherited loss-based criteria
  non-comparable (ledger C-9). Jane's ``_diverged`` is reported alongside.
* The streams are ten **independent replicates**, not disjoint slices of one record.

Usage::

    python scripts/research_c10t_synthetic.py            # full run (~12 min)
    python scripts/research_c10t_synthetic.py --smoke    # fast sanity check
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
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import _diverged as jane_diverged  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research" / "c10t"

# ---- preregistered design (experiment_matrix.yaml doc 5) --------------------------
D, T, SIGMA = 5, 20000, 1.0
SEEDS = list(range(1000, 1010))
TAILS_PRIMARY = 1.5
TAILS = [1.3, 1.5, 2.0]
M_RAYS = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
P_LO, P_HI = 0.5, 128.0
N_BISECT = 10
Q_FROZEN = "p99"
REF_LADDER = [(0.5, 8.0), (0.2, 8.0), (0.1, 8.0)]
WNORM_LIMIT = 1e8
GATE_TOL = 1e-9
DECAY, WINSOR = 0.99, 8.0          # mirrored from research_batched_check._step


def make_stream(seed, p, T=T, d=D):
    """Canonical synthetic stream: y = <u,x> + sigma * t_p noise, static comparator."""
    rng = np.random.default_rng(seed)
    u = rng.standard_normal(d)
    u /= np.linalg.norm(u)
    X = rng.standard_normal((T, d))
    eps = SIGMA * rng.standard_t(df=p, size=T)
    y = X @ u + eps
    return X, y, np.ones(T)


def instrumented(X, y, wts, cap, lr):
    """research_batched_check._step snomd branch, plus ||w|| tracking and r quantiles."""
    d = X.shape[1]
    w = np.zeros(d)
    s = None
    k = 0
    preds = np.empty(len(y))
    ratios: list[float] = []
    wmax = 0.0
    nonfinite = False
    for i in range(len(y)):
        with np.errstate(over="ignore", invalid="ignore"):
            pred = float(w @ X[i])
            preds[i] = pred
            k += 1
            g = 2.0 * wts[i] * (pred - y[i]) * X[i]
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0:
            continue
        sc = max(s if s is not None else gn, 1e-8)
        s = gn if s is None else DECAY * s + (1 - DECAY) * min(gn, WINSOR * s)
        ghat = g / sc
        gnn = float(np.linalg.norm(ghat))
        if gnn > cap:
            ghat = ghat * (cap / gnn)
        if np.isfinite(gnn):
            ratios.append(gnn)
        w = w - (lr / np.sqrt(k)) * ghat
        wn = float(np.linalg.norm(w))
        if not np.isfinite(wn):
            nonfinite = True
            wmax = float("inf")
            break
        wmax = max(wmax, wn)
    r = np.asarray(ratios, float)
    q = {}
    if r.size:
        q = {"p50": float(np.percentile(r, 50)), "p90": float(np.percentile(r, 90)),
             "p99": float(np.percentile(r, 99)), "max": float(r.max())}
    return preds, {"w_max": wmax, "nonfinite": nonfinite, "n_steps": int(r.size), **q}


def state_diverged(diag):
    """Preregistered primary criterion: the iterate norm blows up."""
    return diag["nonfinite"] or not np.isfinite(diag["w_max"]) or diag["w_max"] > WNORM_LIMIT


def validity_gate(streams, log):
    log("\n" + "=" * 96)
    log("INSTRUMENTATION VALIDITY GATE (vs anchor_perrow / _step)")
    log("=" * 96)
    X, y, wts = streams[0]
    worst = 0.0
    for lr, M in [(0.5, 0.5), (2.0, 2.0), (3.0, 5.0), (8.0, 16.0)]:
        mine, _ = instrumented(X, y, wts, M, lr)
        theirs = anchor_perrow(X, y, wts, "snomd", M, lr)
        a, b = agg_r2(y, mine, wts), agg_r2(y, theirs, wts)
        diff = abs(float(a) - float(b))
        worst = max(worst, diff)
        log(f"  lr={lr:<4g} M={M:<5g} instrumented={a:+.10f} harness={b:+.10f} diff={diff:.2e}")
    if not (worst <= GATE_TOL):
        raise SystemExit(f"HALT: instrumentation gate FAILED (worst {worst:.3e}).")
    log(f"  GATE PASSED (worst diff {worst:.2e} <= {GATE_TOL:.0e})")


def spread(vals):
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], float)
    return float(v.max() / v.min()) if v.size >= 2 else float("nan")


def evaluate(P, M, streams, crit_name):
    lr = P / M
    n_div = 0
    for (X, y, wts) in streams:
        preds, diag = instrumented(X, y, wts, M, lr)
        div = state_diverged(diag) if crit_name == "state" else jane_diverged(y, preds, wts)
        n_div += int(bool(div))
    return {"P": P, "M": M, "lr": lr, "n_div": n_div, "any_div": n_div > 0,
            "frac_div": n_div / len(streams)}


def bisect_ray(M, streams, crit_name, n_bisect):
    visited = []

    def ev(P):
        rec = evaluate(P, M, streams, crit_name)
        visited.append(rec)
        return rec["any_div"]

    lo_div, hi_div = ev(P_LO), ev(P_HI)
    if not lo_div and not hi_div:
        return {"M": M, "status": "right_censored", "threshold": None, "visited": visited}
    if lo_div and hi_div:
        return {"M": M, "status": "left_censored", "threshold": None, "visited": visited}
    lo, hi = P_LO, P_HI
    for _ in range(n_bisect):
        mid = float(np.sqrt(lo * hi))
        if ev(mid):
            hi = mid
        else:
            lo = mid
    stable = [v["P"] for v in visited if not v["any_div"]]
    divergent = [v["P"] for v in visited if v["any_div"]]
    return {"M": M, "status": "ok" if max(stable) < min(divergent) else "non_monotone",
            "threshold": float(np.sqrt(lo * hi)), "bracket": [lo, hi], "visited": visited}


def reference_r(streams, log):
    for lr, M in REF_LADDER:
        diags, ok = [], True
        for (X, y, wts) in streams:
            _, d = instrumented(X, y, wts, M, lr)
            if state_diverged(d) or d["n_steps"] == 0:
                ok = False
                break
            diags.append(d)
        if ok:
            rq = {q: float(np.mean([d[q] for d in diags])) for q in ("p50", "p90", "p99", "max")}
            log(f"    reference (lr={lr:g}, M={M:g}) stable; r-quantiles: "
                + "  ".join(f"{k}={v:.3f}" for k, v in rq.items()))
            return rq
    raise SystemExit("HALT: no reference configuration in the ladder is stable.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    global M_RAYS, N_BISECT, TAILS, SEEDS
    Tn = T
    if args.smoke:
        M_RAYS, N_BISECT, TAILS = [0.5, 4.0, 32.0], 3, [1.5]
        SEEDS = SEEDS[:3]
        Tn = 3000
        print(">>> SMOKE MODE <<<")

    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    lines: list[str] = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

    log("=" * 96)
    log(f"C10T -- clean test of C-8 on synthetic streams (q frozen = {Q_FROZEN})")
    log(f"tails {TAILS}, {len(SEEDS)} independent streams, T={Tn}, d={D}, "
        f"{len(M_RAYS)} rays, bracket [{P_LO}, {P_HI}]")
    log("=" * 96)

    report = {"q_frozen": Q_FROZEN, "tails": TAILS, "seeds": SEEDS, "T": Tn, "d": D,
              "M_RAYS": M_RAYS, "wnorm_limit": WNORM_LIMIT, "results": {}}
    all_rows = []
    gated = False

    for p in TAILS:
        streams = [make_stream(s, p, T=Tn) for s in SEEDS]
        if not gated:
            validity_gate(streams, log)
            gated = True
        log(f"\n########## TAIL INDEX p = {p} ##########")
        rq = reference_r(streams, log)
        report["results"][str(p)] = {"r_q": rq, "criteria": {}}

        for crit_name, crit_label in (("state", "primary: state-based max||w||>1e8"),
                                      ("jane", "secondary: Jane _diverged")):
            rays = [bisect_ray(M, streams, crit_name, N_BISECT) for M in M_RAYS]
            for r in rays:
                for v in r["visited"]:
                    all_rows.append({"tail_p": p, "criterion": crit_name,
                                     "ray_M": r["M"], **v})
            usable = [r for r in rays if r["status"] == "ok"]
            cens = [r for r in rays if "censored" in r["status"]]
            nonm = [r for r in rays if r["status"] == "non_monotone"]
            log(f"\n  --- p={p}  {crit_label} ---")
            for r in rays:
                if r["status"] == "ok":
                    log(f"    M={r['M']:<6g} P* = {r['threshold']:9.4f}")
                else:
                    log(f"    M={r['M']:<6g} {r['status'].upper()} -- excluded")
            entry = {"n_usable": len(usable), "n_censored": len(cens),
                     "n_non_monotone": len(nonm),
                     "thresholds": {r["M"]: r["threshold"] for r in usable}}
            if len(cens) >= 2 or len(usable) < 2:
                log(f"    SPREAD VOID (censored={len(cens)}, usable={len(usable)})")
                entry["verdict"] = "VOID"
            else:
                Ps = {r["M"]: r["threshold"] for r in usable}
                sP = spread(list(Ps.values()))
                Rs = {M: (Pv / M) * min(rq[Q_FROZEN], M) for M, Pv in Ps.items()}
                sR = spread(list(Rs.values()))
                sLR = spread([Pv / M for M, Pv in Ps.items()])
                ratio = sR / sP
                log(f"    spread_P = {sP:.4f}   spread_R = {sR:.4f}   "
                    f"spread_lr = {sLR:.4f}   ratio = {ratio:.4f}")
                verdict = ("H6 SURVIVED (ratio <= 0.769)" if ratio <= 0.769 else
                           "H6 FALSIFIED (ratio >= 1.00)" if ratio >= 1.00 else
                           "H6 INCONCLUSIVE (0.769 < ratio < 1.00)")
                log(f"    {'PRIMARY ' if (p == TAILS_PRIMARY and crit_name == 'state') else ''}"
                    f"REGISTERED VERDICT: {verdict}")
                entry.update({"spread_P": sP, "spread_R": sR, "spread_lr": sLR,
                              "ratio": ratio, "verdict": verdict, "R_star": Rs})
            report["results"][str(p)]["criteria"][crit_name] = entry

    # registered sanity expectation + H7
    log("\n" + "=" * 96)
    log("REGISTERED SANITY EXPECTATION AND H7")
    log("=" * 96)
    rq99 = {p: report["results"][str(p)]["r_q"]["p99"] for p in TAILS}
    log("  reference r_p99 by tail: " + "  ".join(f"p={p}:{v:.3f}" for p, v in rq99.items()))
    if len(TAILS) == 3:
        ordered = rq99[1.3] > rq99[1.5] > rq99[2.0]
        log(f"  expected ordering r_p99(1.3) > r_p99(1.5) > r_p99(2.0): "
            f"{'HOLDS' if ordered else 'FAILS -- interpretation weakened'}")
        report["sanity_r99_ordering_holds"] = bool(ordered)
        ratios = {p: report["results"][str(p)]["criteria"]["state"].get("ratio") for p in TAILS}
        log("  state-criterion ratios: "
            + "  ".join(f"p={p}:{'VOID' if v is None else f'{v:.4f}'}" for p, v in ratios.items()))
        vals = [v for v in ratios.values() if v is not None]
        if len(vals) == 3:
            h7 = ("H7 SUPPORTED (all three clear 0.769)" if all(v <= 0.769 for v in vals)
                  else "H7 FALSIFIED (at least one secondary >= 1.00)"
                  if any(v >= 1.00 for v in vals) else "H7 PARTIAL (mixed)")
            log(f"  {h7}")
            report["verdict_H7"] = h7

    pl.DataFrame(all_rows).write_csv(
        RES / ("c10t_synth_smoke.csv" if args.smoke else "c10t_synth.csv"))
    report["wallclock_sec"] = round(time.time() - t0, 1)
    (RES / ("c10t_report_smoke.json" if args.smoke else "c10t_report.json")).write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    (RES / ("c10t_run_smoke.log" if args.smoke else "c10t_run.log")).write_text(
        "\n".join(lines), encoding="utf-8")
    log(f"\n[saved results/research/c10t/]  wallclock {report['wallclock_sec']}s")


if __name__ == "__main__":
    main()
