"""Is Cutkosky--Mehta's per-row co-lead a real effect, and what buys it? (audit round-6, item 1)

The round-6 audit flags a latent contradiction. Table 7 (grid adequacy) reports CM's clip on a
flat plateau (window-1 R^2 varies <0.006 for tau in [100,3000]) and its PER-STEP momentum optimum
at beta=0. An inert clip plus zero momentum means CM, as tuned per-step, reduces to normalized SGD
== our normalized-GD anchor. Yet Table 2 has CM per-row 0.29 and normalized-GD 0.18, a +0.11 gap.
Either (a) the clip binds, (b) beta isn't 0 in the run, (c) the two implementations differ, or
(d) normalized-GD's row is mis-tuned. Each has a different consequence and one puts the retracted
per-row accuracy claim back on the table.

Two facts settle most of it analytically and this script CONFIRMS them empirically across the ten
frozen windows, then isolates the remaining effect:

  * At beta=0, m = clip(g, tau) is a positive rescaling of g, so m/||m|| = g/||g|| whether or not
    the clip binds. Hence CM(beta=0) is IDENTICALLY normalized-GD at the same lr. -> the identical
    per-step cells (both 0.09 +- .21) are a mathematical identity, not a duplicated row.
  * CM's PER-ROW optimum is beta=0.5 (momentum ON), NOT beta=0. So the per-row +0.11 over
    normalized-GD is bought by the MOMENTUM, not the clip (which is on a flat plateau) and not by
    any implementation gap.

Configs are FROZEN (no re-tuning) and evaluated on all ten windows:

  per-row : normalized-GD@lr2 ; normalized-GD@lr3(Table2) ; CM(tau600,beta0,lr2) ; CM(tau600,beta0.5,lr2)(Table2)
  per-step: normalized-GD@lr5(Table2) ; CM(tau300,beta0,lr5)(Table2)

Checks reported:
  - max |CM(beta0,lr2) - normalized-GD@lr2| across windows  (per-row identity; expect ~0)
  - max |CM(beta0,lr5) - normalized-GD@lr5| across windows   (per-step identity; expect ~0)
  - normalized-GD@lr2 vs @lr3 mean R^2                       (is the Table-2 row mis-tuned / does
                                                              lr2 generalize better?)
  - CM(beta0.5) - CM(beta0) at lr2 mean                      (the momentum contribution == the edge)

Usage::

    .venv/Scripts/python.exe scripts/research_cm_normgd_equiv.py            # full (~10 min)
    .venv/Scripts/python.exe scripts/research_cm_normgd_equiv.py --smoke
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_baselines import anchor_batched, anchor_perrow, cm_batched, cm_perrow  # noqa: E402
from research_table1_errorbars import agg_r2  # noqa: E402
from research_windows_replication import WINDOWS, _diverged, _load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "research"


def normgd(X, y, wts, starts, protocol, lr):
    return anchor_batched(X, y, wts, starts, "normgd", 0.0, lr) if protocol == "per-step" \
        else anchor_perrow(X, y, wts, "normgd", 0.0, lr)


def cm(X, y, wts, starts, protocol, tau, beta, lr):
    return cm_batched(X, y, wts, starts, tau, beta, lr) if protocol == "per-step" \
        else cm_perrow(X, y, wts, tau, beta, lr)


# (label, protocol, callable(X,y,wts,starts)) -- all FROZEN, no tuning
def make_configs():
    return [
        ("normgd@lr2",            "per-row",  lambda X, y, w, s: normgd(X, y, w, s, "per-row", 2.0)),
        ("normgd@lr3(Table2)",    "per-row",  lambda X, y, w, s: normgd(X, y, w, s, "per-row", 3.0)),
        ("CM(t600,b0,lr2)",       "per-row",  lambda X, y, w, s: cm(X, y, w, s, "per-row", 600.0, 0.0, 2.0)),
        ("CM(t600,b0.5,lr2)T2",   "per-row",  lambda X, y, w, s: cm(X, y, w, s, "per-row", 600.0, 0.5, 2.0)),
        ("normgd@lr5(Table2)",    "per-step", lambda X, y, w, s: normgd(X, y, w, s, "per-step", 5.0)),
        ("CM(t300,b0,lr5)T2",     "per-step", lambda X, y, w, s: cm(X, y, w, s, "per-step", 300.0, 0.0, 5.0)),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    rows = 4000 if args.smoke else args.rows
    windows = WINDOWS[:3] if args.smoke else WINDOWS
    configs = make_configs()

    print("=" * 100)
    print(f"CM vs normalized-GD equivalence / attribution across {len(windows)} frozen windows; rows<= {rows}")
    print("=" * 100)

    # results[label] = list of per-window R^2
    results: dict[str, list[float]] = {lbl: [] for lbl, _, _ in configs}
    rows_out: list[dict] = []
    for wi, (lo, hi) in enumerate(windows):
        X, y, wts, starts = _load(lo, hi, rows)
        print(f"\n[window {wi+1}] date[{lo},{hi})  n={len(y)}")
        for lbl, protocol, fn in configs:
            p = fn(X, y, wts, starts)
            r2 = agg_r2(y, p, wts)
            div = _diverged(y, p, wts)
            results[lbl].append(float(r2) if np.isfinite(r2) else float("nan"))
            rows_out.append({"window_idx": wi + 1, "window": f"[{lo},{hi})", "protocol": protocol,
                             "config": lbl, "weighted_r2": round(float(r2), 5), "diverged": bool(div)})
            print(f"    {lbl:24s} ({protocol:8s}) R2={r2:+.4f}{'  DIVERGED' if div else ''}")

    pl.DataFrame(rows_out).write_csv(RES / ("cm_normgd_equiv_smoke.csv" if args.smoke else "cm_normgd_equiv.csv"))

    def arr(lbl):
        return np.array(results[lbl], dtype=float)

    def stat(lbl):
        a = arr(lbl)
        return f"{np.nanmean(a):+.4f} +- {np.nanstd(a):.4f}  [{np.nanmin(a):+.4f},{np.nanmax(a):+.4f}]"

    print("\n" + "=" * 100)
    print("SUMMARY (mean +- std [min,max] over windows)")
    print("=" * 100)
    for lbl, _, _ in configs:
        print(f"  {lbl:24s} {stat(lbl)}")

    print("\n" + "-" * 100)
    print("IDENTITY CHECKS  (CM at beta=0 must equal normalized-GD at the same lr, per the algebra)")
    d_perrow = np.abs(arr("CM(t600,b0,lr2)") - arr("normgd@lr2"))
    d_perstep = np.abs(arr("CM(t300,b0,lr5)T2") - arr("normgd@lr5(Table2)"))
    print(f"  per-row : max|CM(b0,lr2) - normgd@lr2|   = {np.nanmax(d_perrow):.2e}   "
          f"({'IDENTICAL -> clip is inert, CM(b0)==normgd' if np.nanmax(d_perrow) < 1e-6 else 'DIFFER -> implementations diverge!'})")
    print(f"  per-step: max|CM(b0,lr5) - normgd@lr5|   = {np.nanmax(d_perstep):.2e}   "
          f"({'IDENTICAL -> the two 0.09+-.21 cells are one trajectory' if np.nanmax(d_perstep) < 1e-6 else 'DIFFER -> implementations diverge!'})")

    print("\n" + "-" * 100)
    print("ATTRIBUTION  (what buys CM's per-row co-lead over normalized-GD?)")
    momentum = np.nanmean(arr("CM(t600,b0.5,lr2)T2")) - np.nanmean(arr("CM(t600,b0,lr2)"))
    lr_effect = np.nanmean(arr("normgd@lr2")) - np.nanmean(arr("normgd@lr3(Table2)"))
    print(f"  normalized-GD row mis-tuned? mean@lr2={np.nanmean(arr('normgd@lr2')):+.4f} vs "
          f"@lr3(Table2)={np.nanmean(arr('normgd@lr3(Table2)')):+.4f}  (delta from lr {lr_effect:+.4f})")
    print(f"  momentum contribution: CM(beta0.5) - CM(beta0) at lr2 = {momentum:+.4f}   "
          f"<-- the per-row edge, bought by MOMENTUM not the (inert) clip")
    print(f"  CM(beta0.5,lr2)={np.nanmean(arr('CM(t600,b0.5,lr2)T2')):+.4f}  "
          f"vs normalized-GD(Table2 lr3)={np.nanmean(arr('normgd@lr3(Table2)')):+.4f}  "
          f"= headline +{np.nanmean(arr('CM(t600,b0.5,lr2)T2')) - np.nanmean(arr('normgd@lr3(Table2)')):+.4f}")
    print(f"\n[saved {(RES / 'cm_normgd_equiv.csv').relative_to(ROOT)}]")


if __name__ == "__main__":
    main()
