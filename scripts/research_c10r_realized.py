"""C10R -- does the REALIZED maximum step locate the boundary better than the nominal one?

Preregistered in ``experiment_matrix.yaml`` (fourth document, direction C10R), committed at
6b46199 BEFORE this script was executed.

``P = lr*M`` is the step the update *could* take; it is attained only when the clip binds,
which for large ``M`` is rare. C-8 proposes the realized maximum
``R = lr * min(r_q, M)``, with ``r_q`` a high quantile of ``r_t = ||g_t||/s_{t-1}``.

C-8 was invented to explain a residual in the Jane thresholds, so Jane cannot test it: a
parameterization invented to fit a residual will fit that residual. Two stages therefore:

  STAGE 1 (FIT, Jane)    pick the quantile level q* from committed C10S/C10M artifacts.
                         No new runs. This is a re-analysis, not a test.
  STAGE 2 (TEST, crypto) repeat the C10S bisection on BTC/USDT, measure that stream's own
                         reference r-quantiles, evaluate R with q* frozen.

Usage::

    python scripts/research_c10r_realized.py            # full run (~2 min)
    python scripts/research_c10r_realized.py --smoke    # fast sanity check
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
from research_c10m_binding import instrumented_perrow  # noqa: E402
from research_crypto_algorithms import diverged as crypto_diverged  # noqa: E402
from research_crypto_mechanism import load_features  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import _diverged as jane_diverged  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research" / "c10r"

# ---- preregistered design (experiment_matrix.yaml doc 4) --------------------------
Q_GRID = ["p50", "p90", "p99", "max"]
Q_COL = {"p50": "r_p50", "p90": "r_p90", "p99": "r_p99", "max": "r_max"}
M_RAYS = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
P_LO, P_HI = 0.5, 128.0
N_BISECT = 10
REF_LADDER = [(0.5, 8.0), (0.2, 8.0), (0.1, 8.0)]
WIN, N_WIN = 6000, 10


def spread(vals):
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], float)
    return float(v.max() / v.min()) if v.size >= 2 else float("nan")


# ============================ STAGE 1 : FIT ON JANE ============================
def stage1(log):
    log("\n" + "=" * 96)
    log("STAGE 1 -- FIT on Jane (re-analysis of committed artifacts; NOT a test)")
    log("=" * 96)

    c10s = json.loads((ROOT / "results/research/c10s/c10s_report.json").read_text("utf-8"))
    rays = [r for r in c10s["protocols"]["per-row"]["rays"] if r["status"] == "ok"]
    P_star = {r["M"]: r["threshold"] for r in rays}
    log(f"  Jane per-row thresholds: " + "  ".join(f"M={m:g}:{p:.3f}" for m, p in P_star.items()))

    # reference r-quantiles at the registered reference config, pooled over held-out windows
    binding = pl.read_csv(ROOT / "results/research/c10m/c10m_binding.csv")
    ref = None
    for lr, M in REF_LADDER:
        sel = binding.filter((pl.col("protocol") == "per-row") & (pl.col("lr") == lr)
                             & (pl.col("M") == M) & (pl.col("window_idx") > 1))
        if sel.height and not bool(sel["diverged"].any()):
            ref = (lr, M, sel)
            break
    if ref is None:
        raise SystemExit("HALT: no reference configuration in the ladder is stable on Jane.")
    lr_ref, M_ref, sel = ref
    r_q = {q: float(sel[Q_COL[q]].mean()) for q in Q_GRID}
    log(f"  reference config (lr={lr_ref:g}, M={M_ref:g}), pooled over {sel.height} held-out windows")
    log(f"  Jane reference r-quantiles: " + "  ".join(f"{q}={v:.3f}" for q, v in r_q.items()))

    spread_P = spread(list(P_star.values()))
    log(f"\n  spread of P* (nominal, no free parameter) = {spread_P:.4f}")
    fits = {}
    for q in Q_GRID:
        R = {M: (P / M) * min(r_q[q], M) for M, P in P_star.items()}
        fits[q] = spread(list(R.values()))
        log(f"    q={q:<4s} r_q={r_q[q]:7.3f}   spread of R* = {fits[q]:.4f}"
            f"   {'(no better than P)' if fits[q] >= spread_P else ''}")
    q_star = min(fits, key=fits.get)
    degenerate = fits[q_star] >= spread_P
    log(f"\n  q* = {q_star}   (Jane spread {fits[q_star]:.4f} vs P's {spread_P:.4f})")
    if degenerate:
        log("  STAGE-1 DEGENERACY: no q in the grid improves on P. C-8 fails on its own")
        log("  generating data. Registered rule: stage 2 still runs with the argmin q*.")
    return {"P_star_jane": P_star, "r_q_jane": r_q, "spread_P_jane": spread_P,
            "fits": fits, "q_star": q_star, "stage1_degenerate": bool(degenerate),
            "ref_config": {"lr": lr_ref, "M": M_ref}}


# ========================= STAGE 2 : TEST ON CRYPTO =========================
def load_crypto(smoke):
    X, y, w, day_id, dt, cols = load_features()
    y = y / float(np.std(y))              # constant rescale, as research_crypto_algorithms does
    n = len(y)
    win = 1500 if smoke else WIN
    nw = 3 if smoke else N_WIN
    gap = (n - nw * win) // max(1, nw - 1)
    wins = [(i * (win + gap), i * (win + gap) + win) for i in range(nw)]
    return [(X[a:b], y[a:b], w[a:b]) for a, b in wins], n, dt


def evaluate(P, M, data, crit):
    lr = P / M
    n_div = 0
    for (Xw, yw, ww) in data:
        preds = anchor_perrow(Xw, yw, ww, "snomd", M, lr)
        if crit(yw, preds, ww):
            n_div += 1
    return {"P": P, "M": M, "lr": lr, "n_div": n_div, "n_windows": len(data),
            "any_div": n_div > 0, "frac_div": n_div / len(data)}


def bisect_ray(M, data, crit, n_bisect, log):
    visited = []

    def ev(P):
        rec = evaluate(P, M, data, crit)
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
    monotone = max(stable) < min(divergent)
    return {"M": M, "status": "ok" if monotone else "non_monotone",
            "threshold": float(np.sqrt(lo * hi)), "bracket": [lo, hi],
            "max_stable": max(stable), "min_divergent": min(divergent), "visited": visited}


def crypto_reference_r(data, log):
    """Reference r-quantiles on the held-out stream, via the registered fallback ladder."""
    for lr, M in REF_LADDER:
        per_win, ok = [], True
        for (Xw, yw, ww) in data:
            preds, diag = instrumented_perrow(Xw, yw, ww, M, lr)
            if crypto_diverged(yw, preds, ww) or diag["n_steps"] == 0:
                ok = False
                break
            per_win.append(diag)
        if ok:
            r_q = {q: float(np.mean([d[Q_COL[q]] for d in per_win])) for q in Q_GRID}
            log(f"  crypto reference config (lr={lr:g}, M={M:g}) stable on all windows")
            log(f"  crypto reference r-quantiles: "
                + "  ".join(f"{q}={v:.3f}" for q, v in r_q.items())
                + f"   bind_rate={np.mean([d['bind_rate'] for d in per_win]):.4f}")
            return r_q, {"lr": lr, "M": M}
    raise SystemExit("HALT: no reference configuration in the ladder is stable on crypto.")


def analyse(rays, r_q, q_star, label, log):
    usable = [r for r in rays if r["status"] == "ok"]
    censored = [r for r in rays if "censored" in r["status"]]
    nonmono = [r for r in rays if r["status"] == "non_monotone"]
    log(f"\n  --- {label} ---")
    for r in rays:
        if r["status"] == "ok":
            log(f"    M={r['M']:<6g} P* = {r['threshold']:8.4f}  "
                f"bracket [{r['bracket'][0]:.4f}, {r['bracket'][1]:.4f}]")
        else:
            log(f"    M={r['M']:<6g} {r['status'].upper()} -- excluded")
    out = {"n_usable": len(usable), "n_censored": len(censored),
           "n_non_monotone": len(nonmono),
           "thresholds": {r["M"]: r["threshold"] for r in usable}}
    if len(censored) >= 2 or len(usable) < 2:
        log(f"  SPREAD VOID (censored={len(censored)}, usable={len(usable)})")
        out["verdict"] = "VOID"
        return out
    P_star = {r["M"]: r["threshold"] for r in usable}
    sP = spread(list(P_star.values()))
    R_star = {M: (P / M) * min(r_q[q_star], M) for M, P in P_star.items()}
    sR = spread(list(R_star.values()))
    lr_star = {M: P / M for M, P in P_star.items()}
    sLR = spread(list(lr_star.values()))
    ratio = sR / sP
    log(f"    R* (q*={q_star}, r_q={r_q[q_star]:.3f}): "
        + "  ".join(f"M={m:g}:{v:.3f}" for m, v in R_star.items()))
    log(f"    spread_P  = {sP:.4f}   (nominal max step, no free parameter)")
    log(f"    spread_R  = {sR:.4f}   (realized max step, q* fitted on Jane)")
    log(f"    spread_lr = {sLR:.4f}   (pure rate, reference point)")
    log(f"    ratio = spread_R / spread_P = {ratio:.4f}")
    verdict = ("H5 SURVIVED (ratio <= 0.769)" if ratio <= 0.769 else
               "H5 FALSIFIED (ratio >= 1.00)" if ratio >= 1.00 else
               "H5 INCONCLUSIVE (0.769 < ratio < 1.00)")
    log(f"    REGISTERED VERDICT: {verdict}")
    out.update({"spread_P": sP, "spread_R": sR, "spread_lr": sLR,
                "ratio": ratio, "verdict": verdict, "R_star": R_star})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    global M_RAYS, N_BISECT
    if args.smoke:
        M_RAYS = [0.5, 4.0, 32.0]
        N_BISECT = 3
        print(">>> SMOKE MODE <<<")

    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    lines: list[str] = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

    log("=" * 96)
    log("C10R -- realized vs nominal maximum step, tested on a held-out stream")
    log("=" * 96)

    s1 = stage1(log)
    q_star = s1["q_star"]

    log("\n" + "=" * 96)
    log("STAGE 2 -- TEST on crypto (BTC/USDT 1h), q* frozen from stage 1")
    log("=" * 96)
    data, n, dt = load_crypto(args.smoke)
    log(f"  n={n} bars {str(dt[0])[:10]}..{str(dt[-1])[:10]}   "
        f"{len(data)} windows x {len(data[0][1])} bars")
    r_q_crypto, ref_used = crypto_reference_r(data, log)

    report = {"stage1": s1, "crypto_r_q": r_q_crypto, "crypto_ref_config": ref_used,
              "M_RAYS": M_RAYS, "P_bracket": [P_LO, P_HI], "n_bisect": N_BISECT,
              "criteria": {}}
    all_rows = []
    for label, crit in (("primary: crypto peak>1e3", crypto_diverged),
                        ("secondary: Jane _diverged", jane_diverged)):
        log(f"\n  [bisecting under {label}]")
        rays = [bisect_ray(M, data, crit, N_BISECT, log) for M in M_RAYS]
        for r in rays:
            for v in r["visited"]:
                all_rows.append({"criterion": label, "ray_M": r["M"], **v})
        report["criteria"][label] = analyse(rays, r_q_crypto, q_star, label, log)

    pl.DataFrame(all_rows).write_csv(
        RES / ("c10r_crypto_smoke.csv" if args.smoke else "c10r_crypto.csv"))
    report["wallclock_sec"] = round(time.time() - t0, 1)
    (RES / ("c10r_report_smoke.json" if args.smoke else "c10r_report.json")).write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    (RES / ("c10r_run_smoke.log" if args.smoke else "c10r_run.log")).write_text(
        "\n".join(lines), encoding="utf-8")
    log(f"\n[saved results/research/c10r/]  wallclock {report['wallclock_sec']}s")


if __name__ == "__main__":
    main()
