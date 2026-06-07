"""Run the cross-machine detectors, compare against the old recurrence method, write metrics
+ report. Run: uv run python scripts/build_crossmachine.py
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from trex.rca import crossmachine as cm, recurrence

ART = Path("analysis/artifacts")
REP = Path("analysis/reports")


def main():
    print("=" * 78, "\n[1] OLD method: recurrence.find_recurrence (no null model)\n", "=" * 78)
    old = recurrence.find_recurrence(bucket="1h")
    old_top = old.head(6)[["category", "n_machines", "total_hours", "systemic_score"]]
    print(old_top.to_string(index=False))
    conn_rank = (old.category.values.tolist().index("CONNECTIVITY")
                 if "CONNECTIVITY" in old.category.values else None)
    print(f"\n-> CONNECTIVITY appears at rank {conn_rank} of {len(old)} (it is the fanned-out "
          "instance-offline row = tautology).")

    print("\n" + "=" * 78, "\n[2] NEW: synchronization test (significant unplanned stops)\n", "=" * 78)
    sync = cm.synchronization_test()
    print(f"machines={sync['n_machines']}  co-stop hours observed={sync['observed_co_stop_hours']}")
    for k in ("free", "daily"):
        s = sync[k]
        print(f"  null[{s['null']:>16}]: exp {s['exp']:>6} ± {s['sd']:<5}  "
              f"z={s['z']:+.2f}  p={s['p']:.3f}")
    print(f"  hour-of-day: top-3 hours hold {sync['top3_hour_share']:.0%} of co-stops "
          f"(busiest UTC hours {sync['busiest_hours']})")
    print(f"  reason granularity: {sync['n_distinct_reasons']} distinct unplanned-stop reason(s) "
          f"-> concordance is {sync['reason_note']}")

    print("\n" + "=" * 78, "\n[3] NEW: anomaly-score coupling (cluster detection)\n", "=" * 78)
    cp = cm.coupling()
    for mode in ("all", "live", "running"):
        d = cp[mode]
        print(f"[{mode:>7}] LEVELS  median_off={d['median_off']:+.3f}  max={d['max_off']:+.3f}  "
              f"clusters(r>=0.5)={d['clusters']}")
        print(f"          DETREND median_off={d['median_off_diff']:+.3f}  "
              f"max={d['max_off_diff']:+.3f}  clusters={d['clusters_diff'] or 'NONE'}")
    print("  -> LEVELS cluster but NO detrended cluster = shared SLOW envelope (operating "
          "rhythm), NOT synchronized acute anomalies.")

    print("\n" + "=" * 78, "\n[4] NEW: data-regime / comparability map\n", "=" * 78)
    rm = cm.regime_map()
    print("availability (non-null buckets per role):")
    print(rm["availability"].sort_values("live_buckets", ascending=False).to_string(index=False))
    print("\nderived regimes (machines grouped by identical feature availability):")
    for pat, ms in rm["regimes"].items():
        print(f"  [{pat}] -> {ms}")
    print("\nshared-role comparability (raw scale across machines):")
    print(rm["comparability"].to_string(index=False))

    # ---- persist
    metrics = {
        "old_recurrence_top": old_top.to_dict("records"),
        "old_connectivity_rank": conn_rank,
        "synchronization": {k: v for k, v in sync.items() if k != "machines"},
        "coupling": {m: {"median_off": cp[m]["median_off"], "max_off": cp[m]["max_off"],
                         "clusters": cp[m]["clusters"], "top_pairs": cp[m]["top_pairs"]}
                     for m in cp},
        "regimes": rm["regimes"],
        "comparability": rm["comparability"].to_dict("records"),
        "availability": rm["availability"].to_dict("records"),
    }
    (ART / "crossmachine_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    _report(old_top, conn_rank, sync, cp, rm)
    print("\nwrote crossmachine_metrics.json + 04_CROSSMACHINE.md")


def _report(old_top, conn_rank, sync, cp, rm):
    free, daily = sync["free"], sync["daily"]
    run = cp["running"]
    L = ["# trexCloud — Cross-Machine Pattern Detection (honest method audit)\n",
         "Replaces naive co-occurrence binning with null-model-backed detectors. Every claim "
         "states what would also fire by chance or by shared schedule.\n",
         "## 0. The old method was a tautology\n",
         f"`recurrence.find_recurrence` ranks **CONNECTIVITY at rank {conn_rank}** — but that is a "
         "single instance-level *System Offline* row fanned out to every machine on the same "
         "`instance_id` (identical start/end). It is systemic *by construction*, not detected. It "
         "also has **no null model**, so chance co-occurrence scores as 'systemic'.\n",
         "## 1. Synchronization of significant unplanned stops (≥15 min)\n",
         f"- Observed 1-h windows with ≥2 machines co-initiating a significant stop: "
         f"**{sync['observed_co_stop_hours']}** (of {sync['n_co_stop_buckets']} multi-stop windows).",
         f"- **Free-shift null** (any alignment): exp {free['exp']}±{free['sd']} → "
         f"**z={free['z']:+.2f}, p={free['p']:.3f}**.",
         f"- **Daily-preserving null** (keeps each machine's hour-of-day, tests alignment BEYOND "
         f"shared shift rhythm): exp {daily['exp']}±{daily['sd']} → **z={daily['z']:+.2f}, "
         f"p={daily['p']:.3f}**.",
         f"- Hour-of-day concentration: top-3 hours hold **{sync['top3_hour_share']:.0%}** of "
         f"co-stops (busiest UTC hours {sync['busiest_hours']}).",
         f"- Reason granularity: **{sync['n_distinct_reasons']} distinct reason(s)** for all "
         f"significant unplanned stops → same-reason concordance is **{sync['reason_note']}**. "
         "The MES stop stream cannot corroborate a shared root; only the alarm stream (Makine 1 & 2 "
         "only) or telemetry can.\n",
         "> Interpretation: synchronization beyond chance is "
         + ("**confirmed**" if daily["p"] < 0.05 else "**only at the shared-schedule level**") +
         ". The daily-preserving null controls for each machine's hour-of-day rhythm, so the "
         "residual is not 'everyone breaks at shift change'. **Caveat:** it does *not* control for "
         "shared weekly / production-campaign scheduling (machines busy the same weeks), so part of "
         "the residual may be a shared production calendar rather than acute facility events. With "
         "only one stop reason (`Duruş`) the MES data cannot resolve which.\n",
         "## 2. Anomaly-score coupling (which machines move together)\n",
         f"- **Levels** (running-only): median pairwise r = **{run['median_off']:+.3f}** (most "
         f"pairs independent), max r = **{run['max_off']:+.3f}**; cluster at r≥0.5 = "
         f"**{run['clusters'] or 'none'}** (selective — Makine 5 is same regime but anti-correlates).",
         f"- **Detrended** (first-difference, event timescale): median r = "
         f"**{run['median_off_diff']:+.3f}**, max r = **{run['max_off_diff']:+.3f}**, cluster = "
         f"**{run['clusters_diff'] or 'NONE'}**.\n",
         "> **Honest reading:** the cluster exists only in *levels*, and collapses to ~0 once "
         "detrended. So {Makine 1,2,3,9} share a **slow common envelope** (a multi-week operating / "
         "load rhythm), but they do **NOT** spike together — this is a shared operating regime, "
         "**not** fault propagation or synchronized acute anomalies. Claiming the latter would be "
         "false.\n",
         "## 3. Data-regime / comparability map (can we even model cross-machine?)\n",
         "Derived from feature availability, not the vendor catalog:\n",
         "| regime (shared streaming roles) | machines |", "|---|---|"]
    for pat, ms in rm["regimes"].items():
        L.append(f"| {pat or '(blind — no telemetry)'} | {', '.join(ms)} |")
    L += ["\n**Shared-role comparability (raw scale):**\n",
          "| role | machines | median min | median max | spread |", "|---|--:|--:|--:|--:|"]
    for r in rm["comparability"].itertuples():
        L.append(f"| {r.role} | {r.machines} | {r.median_min:.0f} | {r.median_max:.0f} | "
                 f"{r.spread_x}× |")
    L += ["\n> Vendor families share almost no feature columns; even the shared `cycle_time` "
          "spans several-× in scale → cross-machine modeling is valid only **within a regime, "
          "after per-machine normalization**. A single pooled feature matrix is half-empty.\n"]
    (REP / "04_CROSSMACHINE.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
