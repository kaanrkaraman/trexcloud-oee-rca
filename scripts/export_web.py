"""Export a single curated bundle.json for the React dashboard (static, no backend).

Bundles: machine/regime map, recomputed OEE + raw components (for client-side What-If),
downtime Pareto (faults vs connectivity), the deployed Fanuc risk timeline + episodes + honest
metrics, the NEW cross-machine detectors (synchronization null, regime map, coupling), the
honest regime-model comparison, and a default flagship RCA case (Makine 1 alarm cascade with a
bounded telemetry overlay) so the app shows real working data out of the box.

Run: uv run python scripts/export_web.py
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from trex import loaders, oee, rca
from trex.rca import crossmachine

ART = Path("analysis/artifacts")
OUT = Path("web/public/data")
FANUC = ["Makine 1", "Makine 2", "Makine 3", "Makine 5", "Makine 9"]
MITS = ["Makine 7", "Makine 8"]


def _j(p):
    return json.loads((ART / p).read_text()) if (ART / p).exists() else {}


def regime_of(name):
    if name in FANUC:
        return "Fanuc cell (predictable)"
    if name in MITS:
        return "Mitsubishi (RCA/OEE only)"
    return "Telemetry-blind (MES only)"


def machines_block():
    mm = loaders.machine_master()
    base = pd.read_parquet(ART / "oee_baseline.parquet")
    comp = ["WorkTotal", "PlannedStop", "UnPlannedStop", "WorkingTime", "PlannedTime",
            "ProductSum", "ScrapeSum"]
    rows = []
    for _, r in mm.iterrows():
        name = r["name"]
        bm = base[base.machine == name]
        agg = {c: float(bm[c].sum()) if c in bm else 0.0 for c in comp}
        o, a, p, q = oee.recompute(agg["WorkTotal"], agg["PlannedStop"], agg["UnPlannedStop"],
                                   agg["WorkingTime"], agg["PlannedTime"], agg["ProductSum"],
                                   agg["ScrapeSum"])
        rows.append({"name": name, "vendor": r["vendor"], "regime": regime_of(name),
                     "has_telemetry": bool(r["has_telemetry"]),
                     "oee": round(float(o), 4), "A": round(float(a), 4),
                     "P": round(float(p), 4), "Q": round(float(q), 4),
                     "components": {k: round(v, 1) for k, v in agg.items()},
                     "down_h": round(agg["UnPlannedStop"] / 3.6e6, 1)})
    return sorted(rows, key=lambda x: -x["down_h"])


def pareto_block():
    df = pd.read_csv(ART / "downtime_pareto.csv")
    df["kind"] = np.where(df.reason.str.contains("Offline|Connect", case=False, na=False),
                          "connectivity", "fault")
    df = df.sort_values("hours", ascending=False).head(14)
    return [{"machine": r.machine, "reason": r.reason, "hours": round(float(r.hours), 1),
             "events": int(r.events), "kind": r.kind} for r in df.itertuples()]


def fanuc_block():
    meta = _j("fanuc_model_meta.json")
    risk = pd.read_parquet(ART / "fanuc_risk.parquet")
    risk["ts"] = pd.to_datetime(risk["ts"], utc=True)
    by = {}
    for m, g in risk.groupby("machine"):
        h = g.set_index("ts")["risk"].resample("3h").max().dropna()
        by[m] = [{"t": t.strftime("%Y-%m-%d %H:%M"), "r": round(float(v), 3)}
                 for t, v in h.items()]
    ep = pd.read_csv(ART / "fanuc_risk_episodes.csv")
    for c in ("start", "end"):
        ep[c] = pd.to_datetime(ep[c], utc=True)
    episodes = {}
    for m, g in ep.groupby("machine"):
        episodes[m] = [{"start": r.start.strftime("%Y-%m-%d %H:%M"),
                        "end": r.end.strftime("%Y-%m-%d %H:%M"),
                        "peak": round(float(r.peak_risk), 3), "hit": bool(r.hit)}
                       for r in g.sort_values("peak_risk", ascending=False).head(8).itertuples()]
    # actual significant stops within the test window (timeline markers)
    sig = crossmachine.significant_unplanned()
    t0 = pd.to_datetime(meta.get("test_start"), utc=True)
    stops = {}
    for m in FANUC:
        s = sig[(sig.machine == m) & (sig.start >= t0)]
        stops[m] = [t.strftime("%Y-%m-%d %H:%M") for t in s.start.head(60)]
    return {"meta": meta, "risk": by, "episodes": episodes, "stops": stops}


def rca_demo_block():
    """Flagship Makine 1 alarm cascade + bounded telemetry overlay."""
    try:
        casc = rca.group_alarm_arrays("Makine 1")
    except Exception:
        casc = []
    if not casc:
        return {}
    best = max(casc, key=lambda c: len(getattr(c, "alarms", [])))
    t = pd.Timestamp(best.timestamp)
    start, end = t - pd.Timedelta("30min"), t + pd.Timedelta("30min")
    tl = rca.build_event_timeline("Makine 1", start, end, with_telemetry=True)
    ev = tl.events.copy()
    events = [{"source": r.source, "category": r.category, "label": str(r.label)[:60],
               "start": pd.Timestamp(r.start).strftime("%H:%M:%S"),
               "end": (pd.Timestamp(r.end).strftime("%H:%M:%S") if pd.notna(r.end) else None)}
              for r in ev.itertuples()]
    tel = []
    if len(tl.telemetry):
        td = tl.telemetry.dropna(subset=["value"])
        for role, g in td.groupby("canonical_role"):
            g = g.sort_values("time")
            step = max(1, len(g) // 300)
            pts = [{"t": pd.Timestamp(x.time).strftime("%H:%M:%S"), "v": float(x.value)}
                   for x in g.iloc[::step].itertuples()]
            tel.append({"role": str(role), "points": pts})
    card = rca.build_root_cause_card("Makine 1", start, end).to_dict()
    deviation = _deviation_breakdown("Makine 1", t)
    return {"machine": "Makine 1",
            "window": [start.strftime("%Y-%m-%d %H:%M"), end.strftime("%H:%M")],
            "event_time": t.strftime("%Y-%m-%d %H:%M:%S"),
            "events": events, "telemetry": tel, "card": card, "deviation": deviation}


def _deviation_breakdown(machine, t):
    """Multi-signal baseline-deviation signature (robust-z) at the event — the Gold evidence.
    AD `top_roles` is stored as a repr string → parse with literal_eval."""
    import ast
    try:
        sc = pd.read_parquet(ART / "ad_scores.parquet")
        sc["ts"] = pd.to_datetime(sc["ts"], utc=True)
        w = sc[(sc.machine == machine) & (sc.ts >= t - pd.Timedelta("30min")) &
               (sc.ts <= t + pd.Timedelta("10min"))]
        agg = {}
        for cell in w["top_roles"].dropna():
            lst = ast.literal_eval(cell) if isinstance(cell, str) else cell
            for d in lst:
                agg.setdefault(d["role"], []).append((float(d["dev_score"]), d["direction"]))
        out = []
        for role, vals in agg.items():
            dev = float(np.mean([v[0] for v in vals]))
            dirs = [v[1] for v in vals]
            out.append({"role": role, "dev": round(dev, 2),
                        "dir": max(set(dirs), key=dirs.count)})
        out = [d for d in out if d["dev"] > 0.05]
        return sorted(out, key=lambda x: -x["dev"])[:5]
    except Exception:
        return []


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cm = _j("crossmachine_metrics.json")
    bundle = {
        "meta": {"title": "trexCloud — Predictive OEE & RCA",
                 "note": "Static export; What-If recomputed client-side."},
        "machines": machines_block(),
        "regimes": cm.get("regimes", {}),
        "pareto": pareto_block(),
        "fanuc": fanuc_block(),
        "crossmachine": {"synchronization": cm.get("synchronization", {}),
                         "coupling": cm.get("coupling", {}),
                         "regimes": cm.get("regimes", {}),
                         "comparability": cm.get("comparability", []),
                         "old_connectivity_rank": cm.get("old_connectivity_rank")},
        "regime_models": _j("regime_metrics.json"),
        "rca_demo": rca_demo_block(),
        "whatif_assumptions": {"margin_per_piece": 12.0, "downtime_cost_per_hour": 80.0,
                               "intervention_cost": 300.0, "horizon_days": 30, "currency": "TRY"},
    }
    (OUT / "bundle.json").write_text(json.dumps(bundle, default=str))
    kb = (OUT / "bundle.json").stat().st_size / 1024
    print(f"wrote {OUT/'bundle.json'} ({kb:.0f} KB)")
    print(f"  machines={len(bundle['machines'])}  pareto={len(bundle['pareto'])}  "
          f"fanuc_machines={len(bundle['fanuc']['risk'])}  "
          f"rca_events={len(bundle['rca_demo'].get('events', []))}  "
          f"rca_tel_roles={len(bundle['rca_demo'].get('telemetry', []))}")


if __name__ == "__main__":
    main()
