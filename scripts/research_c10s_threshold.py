"""C10S -- locate the stability threshold P* and test whether P = lr*M governs it.

Preregistered in ``experiment_matrix.yaml`` (third document, direction C10S), committed at
44f6fa1 BEFORE this script was executed. Provenance is disclosed there: the hypothesis
comes from the exploratory C-7 observation, so this is a confirmation attempt on new
configurations, not a re-analysis of the ones that produced it.

The step is ``(lr/sqrt(k)) * min(r_t, M)`` with ``r_t = ||g_t||/s_{t-1}``, so ``P = lr*M``
bounds the step but says nothing about the typical one. Six rays hold ``M`` fixed and set
``lr = P/M``; at a given ``P`` they differ in typical step size by more than an order of
magnitude. If the divergence boundary turns at the same ``P`` on all six, the maximum step
is what controls stability. If it does not, ``P`` is the wrong parameterization.

Search is deterministic log-space bisection, fixed in advance: endpoints, then exactly five
bisections, final bracket a factor of 1.044. Two registered guards -- censoring and a
monotonicity check -- decide when a ray's threshold may be quoted at all.

Usage::

    python scripts/research_c10s_threshold.py            # full run (~17 min)
    python scripts/research_c10s_threshold.py --smoke    # fast sanity check
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

from research_baselines import anchor_batched, anchor_perrow  # noqa: E402
from research_batched_check import group_boundaries  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS, _diverged  # noqa: E402

from dfsl import JaneStreetDataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research" / "c10s"

# ---- preregistered design (experiment_matrix.yaml doc 3) --------------------------
M_RAYS = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
P_LO, P_HI = 6.0, 24.0
N_BISECT = 5


def _load(lo, hi, rows):
    ds = JaneStreetDataset(date_range=(lo, hi), max_rows=rows, standardize=True)
    return ds.X, ds.y, ds.weights, group_boundaries(ds.meta)


def evaluate(P, M, data, protocol):
    """Run one (lr=P/M, M) configuration on every window. Returns the divergence record."""
    lr = P / M
    n_div, r2s = 0, []
    for (Xw, yw, ww, sw) in data:
        if protocol == "per-row":
            preds = anchor_perrow(Xw, yw, ww, "snomd", M, lr)
        else:
            preds = anchor_batched(Xw, yw, ww, sw, "snomd", M, lr)
        r2 = agg_r2(yw, preds, ww)
        r2s.append(float(r2) if np.isfinite(r2) else float("nan"))
        if _diverged(yw, preds, ww):
            n_div += 1
    return {"P": P, "M": M, "lr": lr, "n_div": n_div, "n_windows": len(data),
            "any_div": n_div > 0, "frac_div": n_div / len(data),
            "mean_r2": float(np.nanmean(r2s)) if np.any(np.isfinite(r2s)) else float("nan")}


def bisect_ray(M, data, protocol, log):
    """Registered deterministic log-space bisection. Returns the ray record."""
    visited = []

    def ev(P):
        rec = evaluate(P, M, data, protocol)
        visited.append(rec)
        log(f"    M={M:<5g} P={P:>7.3f} lr={rec['lr']:>8.3f}  "
            f"div={rec['n_div']}/{rec['n_windows']}  meanR2={rec['mean_r2']:+.4f}  "
            f"{'DIVERGENT' if rec['any_div'] else 'stable'}")
        return rec["any_div"]

    lo_div, hi_div = ev(P_LO), ev(P_HI)
    if not lo_div and not hi_div:
        return {"M": M, "status": "right_censored", "visited": visited,
                "threshold": None, "bracket": [P_HI, None]}
    if lo_div and hi_div:
        return {"M": M, "status": "left_censored", "visited": visited,
                "threshold": None, "bracket": [None, P_LO]}

    lo, hi = P_LO, P_HI
    for _ in range(N_BISECT):
        mid = float(np.sqrt(lo * hi))
        if ev(mid):
            hi = mid
        else:
            lo = mid

    # registered monotonicity check: every stable P below every divergent P
    stable = [v["P"] for v in visited if not v["any_div"]]
    divergent = [v["P"] for v in visited if v["any_div"]]
    monotone = max(stable) < min(divergent)
    status = "ok" if monotone else "non_monotone"
    return {"M": M, "status": status, "visited": visited,
            "threshold": float(np.sqrt(lo * hi)), "bracket": [lo, hi],
            "max_stable": max(stable), "min_divergent": min(divergent)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    rows, windows = args.rows, WINDOWS
    global M_RAYS, N_BISECT
    if args.smoke:
        rows, windows = 4000, WINDOWS[:3]
        M_RAYS = [0.5, 4.0, 16.0]
        N_BISECT = 2
        print(">>> SMOKE MODE <<<")

    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    lines: list[str] = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

    log("=" * 96)
    log(f"C10S -- stability threshold: {len(M_RAYS)} rays x {2 + N_BISECT} evaluations "
        f"x {len(windows)} windows x 2 protocols, rows<={rows}")
    log("=" * 96)

    log(f"\n[preloading {len(windows)} windows]")
    data = []
    for lo, hi in windows:
        data.append(_load(lo, hi, rows))
    log(f"  loaded in {time.time()-t0:.0f}s")

    report = {"M_RAYS": M_RAYS, "P_bracket": [P_LO, P_HI], "n_bisect": N_BISECT,
              "rows_per_window": rows, "n_windows": len(windows), "protocols": {}}
    all_rows: list[dict] = []

    for protocol in ("per-row", "per-step"):
        log(f"\n########## PROTOCOL: {protocol} ##########")
        rays = []
        for M in M_RAYS:
            log(f"  ray M={M:g}  (lr = P/M)")
            r = bisect_ray(M, data, protocol, log)
            rays.append(r)
            for v in r["visited"]:
                all_rows.append({"protocol": protocol, "ray_M": M, **v})

        usable = [r for r in rays if r["status"] == "ok"]
        censored = [r for r in rays if "censored" in r["status"]]
        nonmono = [r for r in rays if r["status"] == "non_monotone"]

        log(f"\n  --- {protocol} rays ---")
        for r in rays:
            if r["status"] == "ok":
                log(f"    M={r['M']:<5g} P* = {r['threshold']:.3f}   "
                    f"bracket [{r['bracket'][0]:.3f}, {r['bracket'][1]:.3f}]   "
                    f"(max stable {r['max_stable']:.3f}, min divergent "
                    f"{r['min_divergent']:.3f})")
            else:
                log(f"    M={r['M']:<5g} {r['status'].upper()} -- excluded")

        entry = {"rays": rays, "n_usable": len(usable),
                 "n_censored": len(censored), "n_non_monotone": len(nonmono)}
        if len(censored) >= 2:
            log(f"  SPREAD STATISTIC VOID: {len(censored)} censored rays (registered rule: "
                f"two or more voids it)")
            entry["spread"] = None
            entry["verdict"] = "VOID (>=2 censored rays)"
        elif len(usable) < 2:
            log(f"  SPREAD STATISTIC VOID: only {len(usable)} usable ray(s)")
            entry["spread"] = None
            entry["verdict"] = "VOID (<2 usable rays)"
        else:
            th = np.array([r["threshold"] for r in usable])
            spread = float(th.max() / th.min())
            phat = float(np.exp(np.mean(np.log(th))))
            entry["spread"] = spread
            entry["P_hat"] = phat
            entry["thresholds"] = {r["M"]: r["threshold"] for r in usable}
            log(f"\n  P*_hat (geometric mean over {len(usable)} usable rays) = {phat:.3f}")
            log(f"  per-ray range [{th.min():.3f}, {th.max():.3f}]   spread = {spread:.4f}")
            if protocol == "per-row":
                verdict = ("H4 SURVIVED (spread <= 1.25)" if spread <= 1.25 else
                           "H4 FALSIFIED (spread >= 2.00)" if spread >= 2.00 else
                           "H4 INCONCLUSIVE (1.25 < spread < 2.00)")
                log(f"  REGISTERED VERDICT (primary, per-row): {verdict}")
                entry["verdict"] = verdict
                report["verdict"] = verdict
        report["protocols"][protocol] = entry

    df = pl.DataFrame(all_rows)
    out_csv = RES / ("c10s_threshold_smoke.csv" if args.smoke else "c10s_threshold.csv")
    df.write_csv(out_csv)
    report["wallclock_sec"] = round(time.time() - t0, 1)
    out_json = RES / ("c10s_report_smoke.json" if args.smoke else "c10s_report.json")
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (RES / ("c10s_run_smoke.log" if args.smoke else "c10s_run.log")).write_text(
        "\n".join(lines), encoding="utf-8")
    log(f"\n[saved {out_csv.relative_to(ROOT)} and {out_json.relative_to(ROOT)}]  "
        f"wallclock {report['wallclock_sec']}s")


if __name__ == "__main__":
    main()
