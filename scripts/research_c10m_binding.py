"""C10M -- does the cap act through the effective max step, or through binding frequency?

Preregistered in ``experiment_matrix.yaml`` (second document, direction C10M), committed
at a0fc908 BEFORE this script was executed. Provenance is disclosed there: the hypothesis
was generated after seeing the C10/Q6 result and is not independent of it.

The cap enters the SN-OMD update only through the step magnitude

    ||dw_t|| = (lr / sqrt(k)) * min(r_t, M),      r_t = ||g_t|| / s_{t-1}

and the clip BINDS when r_t > M. Two mechanisms make different predictions:

  H2  product sufficiency  -- the cap only bounds the step, so held-out performance is a
      function of P = lr*M alone.
  H3  binding-rate mediation -- what matters is the fraction b of steps routed through the
      scale-free branch (magnitude exactly lr*M/sqrt(k), independent of tracker error)
      rather than the scale-normalized branch (magnitude lr*r_t/sqrt(k), which inherits
      the tracker's estimation error).

Nothing is tuned here. Every configuration is evaluated directly on every window, so there
is no selection step -- and correspondingly NO CONFIGURATION FOUND HERE MAY BE REPORTED AS
A RECOMMENDED SETTING, since choosing one would be selection on evaluation data.

Usage::

    python scripts/research_c10m_binding.py            # full run (~20 min)
    python scripts/research_c10m_binding.py --smoke    # fast sanity check
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
RES = ROOT / "results" / "research" / "c10m"

# ---- preregistered grids (experiment_matrix.yaml doc 2: design.grids) -------------
LR_DYADIC = [0.5, 1.0, 2.0, 4.0, 8.0]
M_DYADIC = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
ANCHORS = [(2.0, 5.0, "published"), (3.0, 2.0, "matched")]

# _step's constants -- mirrored, not re-chosen. See research_batched_check._step.
DECAY, WINSOR = 0.99, 8.0
GATE_TOL = 1e-9  # instrumentation_validity_gate


def instrumented_perrow(X, y, wts, cap, lr):
    """Byte-for-byte the snomd branch of research_batched_check._step, plus diagnostics.

    Any divergence from that function invalidates every number in this run, which is why
    the validity gate below checks it against the shared harness rather than trusting it.
    """
    d = X.shape[1]
    w = np.zeros(d)
    s = None
    k = 0
    preds = np.empty(len(y))
    ratios: list[float] = []
    disps: list[float] = []
    n_bind = 0
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
        gnn = float(np.linalg.norm(ghat))          # gnn == r_t
        bound = gnn > cap
        if bound:
            ghat = ghat * (cap / gnn)
            n_bind += 1
        if np.isfinite(gnn):
            ratios.append(gnn)
            disps.append((lr / np.sqrt(k)) * min(gnn, cap))
        w = w - (lr / np.sqrt(k)) * ghat
    return preds, _diag(ratios, disps, n_bind)


def instrumented_batched(X, y, wts, starts, cap, lr):
    d = X.shape[1]
    w = np.zeros(d)
    s = None
    ends = np.append(starts[1:], len(y))
    preds = np.empty(len(y))
    ratios: list[float] = []
    disps: list[float] = []
    n_bind = 0
    for k, (a, b) in enumerate(zip(starts, ends), start=1):
        with np.errstate(over="ignore", invalid="ignore"):
            p = X[a:b] @ w
            preds[a:b] = p
            g = 2.0 * (X[a:b] * (wts[a:b] * (p - y[a:b]))[:, None]).sum(axis=0)
        gn = float(np.linalg.norm(g))
        if not np.isfinite(gn) or gn == 0:
            continue
        sc = max(s if s is not None else gn, 1e-8)
        s = gn if s is None else DECAY * s + (1 - DECAY) * min(gn, WINSOR * s)
        ghat = g / sc
        gnn = float(np.linalg.norm(ghat))
        bound = gnn > cap
        if bound:
            ghat = ghat * (cap / gnn)
            n_bind += 1
        if np.isfinite(gnn):
            ratios.append(gnn)
            disps.append((lr / np.sqrt(k)) * min(gnn, cap))
        w = w - (lr / np.sqrt(k)) * ghat
    return preds, _diag(ratios, disps, n_bind)


def _diag(ratios, disps, n_bind):
    r = np.asarray(ratios, dtype=float)
    dd = np.asarray(disps, dtype=float)
    if r.size == 0:
        return {"n_steps": 0, "n_bind": 0, "bind_rate": float("nan")}
    return {
        "n_steps": int(r.size),
        "n_bind": int(n_bind),
        "bind_rate": float(n_bind) / float(r.size),
        "r_p50": float(np.percentile(r, 50)),
        "r_p90": float(np.percentile(r, 90)),
        "r_p99": float(np.percentile(r, 99)),
        "r_max": float(r.max()),
        "disp_mean": float(dd.mean()),
        "disp_max": float(dd.max()),
    }


def _load(lo, hi, rows):
    ds = JaneStreetDataset(date_range=(lo, hi), max_rows=rows, standardize=True)
    return ds.X, ds.y, ds.weights, group_boundaries(ds.meta)


def validity_gate(X, y, wts, starts) -> None:
    """Instrumented runner must match the shared harness to GATE_TOL, or we HALT."""
    print("\n" + "=" * 96)
    print("INSTRUMENTATION VALIDITY GATE (vs research_batched_check._step)")
    print("=" * 96)
    checks = [(0.5, 0.5), (2.0, 2.0), (3.0, 5.0), (8.0, 16.0)]
    worst = 0.0
    for lr, M in checks:
        for proto in ("per-row", "per-step"):
            if proto == "per-row":
                mine, _ = instrumented_perrow(X, y, wts, M, lr)
                theirs = anchor_perrow(X, y, wts, "snomd", M, lr)
            else:
                mine, _ = instrumented_batched(X, y, wts, starts, M, lr)
                theirs = anchor_batched(X, y, wts, starts, "snomd", M, lr)
            a, b = agg_r2(y, mine, wts), agg_r2(y, theirs, wts)
            diff = abs(float(a) - float(b))
            worst = max(worst, diff)
            print(f"  lr={lr:<4g} M={M:<5g} {proto:9s} instrumented={a:+.10f} "
                  f"harness={b:+.10f}  diff={diff:.2e}")
    if not (worst <= GATE_TOL):
        raise SystemExit(
            f"\nHALT: instrumentation validity gate FAILED (worst diff {worst:.3e} > "
            f"{GATE_TOL:.0e}). The instrumented runner does not reproduce the measured "
            f"algorithm; no result from it would be trustworthy."
        )
    print(f"  GATE PASSED (worst diff {worst:.2e} <= {GATE_TOL:.0e})")


def _spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    if a.size < 3:
        return float("nan")
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    den = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / den) if den > 0 else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    rows, windows = args.rows, WINDOWS
    global LR_DYADIC, M_DYADIC
    if args.smoke:
        rows, windows = 4000, WINDOWS[:3]
        LR_DYADIC = [0.5, 2.0, 8.0]
        M_DYADIC = [0.5, 2.0, 8.0]
        print(">>> SMOKE MODE <<<")

    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    configs = [(lr, M, "grid") for lr in LR_DYADIC for M in M_DYADIC]
    if not args.smoke:
        configs += [(lr, M, lab) for lr, M, lab in ANCHORS]
    print("=" * 96)
    print(f"C10M -- clip-binding mechanism probe: {len(configs)} configs x {len(windows)} "
          f"windows x 2 protocols, rows<={rows}")
    print("=" * 96)

    X1, y1, w1, s1 = _load(*windows[0], rows)
    validity_gate(X1, y1, w1, s1)

    out_rows: list[dict] = []
    for protocol in ("per-row", "per-step"):
        print(f"\n########## PROTOCOL: {protocol} ##########")
        for wi, (lo, hi) in enumerate(windows):
            if wi == 0:
                Xw, yw, ww, sw = X1, y1, w1, s1
            else:
                Xw, yw, ww, sw = _load(lo, hi, rows)
            print(f"[window {wi+1}] date[{lo},{hi})  n={len(yw)}")
            for lr, M, kind in configs:
                if protocol == "per-row":
                    preds, diag = instrumented_perrow(Xw, yw, ww, M, lr)
                else:
                    preds, diag = instrumented_batched(Xw, yw, ww, sw, M, lr)
                r2 = agg_r2(yw, preds, ww)
                out_rows.append({
                    "protocol": protocol, "window_idx": wi + 1, "window": f"[{lo},{hi})",
                    "kind": kind, "lr": lr, "M": M, "P": lr * M,
                    "weighted_r2": float(r2) if np.isfinite(r2) else float("nan"),
                    "diverged": bool(_diverged(yw, preds, ww)),
                    **diag,
                })
            print(f"  {len(configs)} configs done  ({time.time()-t0:.0f}s elapsed)")

    df = pl.DataFrame(out_rows)
    out_csv = RES / ("c10m_binding_smoke.csv" if args.smoke else "c10m_binding.csv")
    df.write_csv(out_csv)
    print(f"\n[saved {out_csv.relative_to(ROOT)}]")

    # ------------------- preregistered analysis -------------------
    report = {"grids": {"LR_DYADIC": LR_DYADIC, "M_DYADIC": M_DYADIC},
              "anchors": [{"lr": a, "M": b, "label": c} for a, b, c in ANCHORS],
              "protocols": {}}
    print("\n" + "=" * 96)
    print("PREREGISTERED ANALYSIS")
    print("=" * 96)

    for protocol in ("per-row", "per-step"):
        d = df.filter((pl.col("protocol") == protocol) & (pl.col("window_idx") > 1))
        agg = (d.group_by(["kind", "lr", "M", "P"])
                 .agg(pl.col("weighted_r2").mean().alias("r2"),
                      pl.col("bind_rate").mean().alias("b"),
                      pl.col("diverged").any().alias("any_div"),
                      pl.col("r_p99").mean().alias("r_p99"),
                      pl.col("disp_max").mean().alias("disp_max"))
                 .sort(["lr", "M"]))
        grid = agg.filter(pl.col("kind") == "grid")
        clean = grid.filter(~pl.col("any_div"))
        n_excl = grid.height - clean.height

        def eta2(frame):
            r2v = frame["r2"].to_numpy()
            if r2v.size < 2:
                return float("nan")
            ss_tot = float(((r2v - r2v.mean()) ** 2).sum())
            ss_in = 0.0
            for p in frame["P"].unique().to_list():
                v = frame.filter(pl.col("P") == p)["r2"].to_numpy()
                ss_in += float(((v - v.mean()) ** 2).sum())
            return float("nan") if ss_tot == 0 else 1.0 - ss_in / ss_tot

        prim = eta2(clean)
        floored = grid.with_columns(pl.col("r2").clip(lower_bound=-1.0))
        sec = eta2(floored)

        r2v = clean["r2"].to_numpy()
        cands = {"logP": np.log(clean["P"].to_numpy()),
                 "b": clean["b"].to_numpy(),
                 "log_lr": np.log(clean["lr"].to_numpy()),
                 "log_M": np.log(clean["M"].to_numpy())}
        rho2 = {k: _spearman(r2v, v) ** 2 for k, v in cands.items()}

        print(f"\n--- {protocol} ---")
        print(f"  configs on grid: {grid.height}   non-diverged: {clean.height}   "
              f"excluded: {n_excl}")
        print(f"  iso-P groups (non-diverged): {clean['P'].n_unique()}")
        print(f"  eta2_P primary (non-diverged) = {prim:.4f}")
        print(f"  eta2_P secondary (all, floored at -1) = {sec:.4f}")
        for k, v in sorted(rho2.items(), key=lambda kv: -kv[1]):
            print(f"    rho2[{k:>6s}] = {v:.4f}")
        margin = rho2["b"] - rho2["logP"]
        print(f"  rho2_b - rho2_logP = {margin:+.4f}")

        if protocol == "per-row":
            v2 = ("H2 SURVIVED (eta2_P >= 0.80)" if prim >= 0.80 else
                  "H2 FALSIFIED (eta2_P <= 0.50)" if prim <= 0.50 else
                  "H2 INCONCLUSIVE (0.50 < eta2_P < 0.80)")
            v3 = ("H3 SURVIVED (rho2_b - rho2_logP >= 0.05)" if margin >= 0.05 else
                  "H3 FALSIFIED (rho2_b - rho2_logP <= -0.05)" if margin <= -0.05 else
                  "H3 INCONCLUSIVE (|difference| < 0.05)")
            print(f"  REGISTERED VERDICT (primary, per-row): {v2}")
            print(f"  REGISTERED VERDICT (primary, per-row): {v3}")
            report["verdict_H2"], report["verdict_H3"] = v2, v3

        anch = agg.filter(pl.col("kind") != "grid")
        if anch.height:
            print("  anchors (held-out means, descriptive -- not in the variance analysis):")
            for r in anch.iter_rows(named=True):
                print(f"    {r['kind']:>9s}  lr={r['lr']:<4g} M={r['M']:<4g} P={r['P']:<5g}"
                      f"  R2={r['r2']:+.4f}  bind_rate={r['b']:.4f}"
                      f"  r_p99={r['r_p99']:.3f}  disp_max={r['disp_max']:.4f}")

        report["protocols"][protocol] = {
            "eta2_P_primary": prim, "eta2_P_secondary_floored": sec,
            "rho2": rho2, "margin_b_minus_logP": float(margin),
            "n_grid": grid.height, "n_clean": clean.height, "n_excluded": n_excl,
            "anchors": anch.to_dicts(),
            "surface": clean.to_dicts(),
        }

    report["wallclock_sec"] = round(time.time() - t0, 1)
    out_json = RES / ("c10m_report_smoke.json" if args.smoke else "c10m_report.json")
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[saved {out_json.relative_to(ROOT)}]  wallclock {report['wallclock_sec']}s")


if __name__ == "__main__":
    main()
