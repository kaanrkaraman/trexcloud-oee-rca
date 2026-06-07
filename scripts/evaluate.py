"""Consolidated evaluation pipeline.

Produces:
  analysis/artifacts/eval_metrics.json     machine-readable metrics
  analysis/reports/02_EVALUATION.md         human-readable report
  analysis/reports/figures/*.html           standalone interactive figures

Covers AD (lead-time, precision/recall, coverage), RCA (cascade/correlation/recurrence),
and What-If (sanity checks + portfolio impact at default financial assumptions).

Run: uv run python scripts/evaluate.py
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

from trex import loaders, oee, rca, whatif
from trex.ad import labels, eval as adeval

ART = Path("analysis/artifacts")
REP = Path("analysis/reports")
FIG = REP / "figures"


def _exists(p):
    return (ART / p).exists()


def evaluate_ad(metrics):
    if not _exists("ad_scores.parquet"):
        metrics["ad"] = {"status": "not built — run scripts/build_ad.py"}
        return None, None, None
    sc = pd.read_parquet(ART / "ad_scores.parquet")
    sc["ts"] = pd.to_datetime(sc["ts"], utc=True)
    w = pd.read_parquet(ART / "ad_anomaly_windows.parquet")
    lab = labels.anomaly_label_windows()
    off = labels.offline_windows()

    summ = adeval.summarize(sc, lab, off, thresh=90.0)
    pr = adeval.event_precision_recall(adeval._drop_offline(sc, off), lab)
    cov = (sc.groupby("machine")
             .agg(buckets=("ts", "size"),
                  flagged_pct=("score", lambda s: float((s >= 90).mean() * 100)),
                  offline_pct=("is_offline", lambda s: float(s.mean() * 100)))
             .reset_index())
    metrics["ad"] = {
        "machines_scored": int(sc.machine.nunique()),
        "score_buckets": int(len(sc)),
        "anomaly_windows": int(len(w)),
        "lead_time_per_machine": summ.to_dict(orient="records"),
        "precision_recall": pr.round(3).to_dict(orient="records"),
        "median_lead_min_overall": float(np.nanmedian(summ.median_lead_min)),
        "mean_pct_with_warning": float(summ.pct_with_warning.mean()),
    }
    return summ, pr, cov


def evaluate_rca(metrics):
    stream = rca.build_event_stream(
        ad_df=(pd.read_parquet(ART / "ad_anomaly_windows.parquet")
               if _exists("ad_anomaly_windows.parquet") else None))
    alarms = rca.alarm_pareto()
    stops = rca.stop_pareto(scope="plant", by="hours")
    # cascades across alarm machines
    casc = sum((rca.group_alarm_arrays(m) for m in ["Makine 1", "Makine 2"]), [])
    rec = rca.correlate_with_offline(rca.find_recurrence(stream=stream))
    # alarm->stop match rate (Makine 1 & 2)
    corr = pd.concat([rca.correlate_alarms_to_stops(m) for m in ["Makine 1", "Makine 2"]],
                     ignore_index=True)
    match_rate = float(corr.matched.mean()) if len(corr) else float("nan")
    metrics["rca"] = {
        "event_stream_rows": int(len(stream)),
        "events_by_source": {k: int(v) for k, v in stream.source.value_counts().items()},
        "alarms_total": int(alarms.occurrences.sum()) if len(alarms) else 0,
        "alarm_categories": alarms.to_dict(orient="records"),
        "alarm_cascades": len(casc),
        "cascade_examples": [{"machine": c.machine, "ts": str(c.timestamp),
                              "root": c.root_category, "chain": " -> ".join(c.alarms)}
                             for c in casc[:5]],
        "alarm_to_stop_match_rate": round(match_rate, 3),
        "systemic_events": int(len(rec)),
        "top_systemic": (rec.head(5).assign(machines=lambda d: d.machines.apply(len))
                         [["bucket_start", "category", "facility_root", "n_machines",
                           "total_hours"]].astype({"bucket_start": str})
                         .to_dict(orient="records")),
        "plant_downtime_top": stops.head(5).round(1).to_dict(orient="records"),
    }
    return stream, rec, stops


def evaluate_whatif(metrics):
    base = oee.baseline(level=1)
    # sanity: documented Makine 1 2025-11-05 W1 50% -> A ~0.50; decompose residual 0
    rr = base[(base.machine == "Makine 1") & (base.date.astype(str) == "2025-11-05")]
    sanity = {}
    if len(rr):
        r = rr.iloc[0]
        res = whatif.run_scenario(r, whatif.ScenarioSpec("W1", 0.5),
                                  category_ms=r.UnPlannedStop)
        d = whatif.decompose_oee(res.before, res.after)
        sanity = {"doc_case_A_before": round(res.before["A"], 3),
                  "doc_case_A_after_W1_50": round(res.after["A"], 3),
                  "decompose_residual": d["residual"]}

    # portfolio: reduce each machine-day's unplanned downtime 30% (W1), aggregate impact
    port = whatif.run_scenario_range(base, whatif.ScenarioSpec("W1", 0.30))
    a = whatif.FinancialAssumptions()
    total_recovered_h = float(port.recovered_h.sum())
    total_extra_pieces = float(port.extra_pieces.sum())
    gross = total_extra_pieces * a.contribution_margin_per_piece
    metrics["whatif"] = {
        "sanity": sanity,
        "portfolio_W1_30pct": {
            "machine_days": int(len(port)),
            "total_recovered_hours": round(total_recovered_h, 1),
            "total_extra_pieces": round(total_extra_pieces, 0),
            "mean_dOEE_pp": round(float(port.dOEE.mean()) * 100, 3),
            "gross_benefit_margin_basis": round(gross, 0),
            "assumptions": {"margin_per_piece": a.contribution_margin_per_piece,
                            "currency": a.currency},
        },
    }
    return base, port


def make_figures(summ, pr, cov, rec, stops, base, port):
    FIG.mkdir(parents=True, exist_ok=True)
    import plotly.express as px
    import plotly.graph_objects as go
    figs = {}

    if pr is not None:
        f = go.Figure()
        f.add_trace(go.Scatter(x=pr.recall, y=pr.precision, mode="lines+markers",
                               text=pr.thresh, name="PR"))
        f.update_layout(title="AD precision–recall vs threshold (offline-excluded)",
                        xaxis_title="recall", yaxis_title="precision")
        figs["ad_precision_recall"] = f

        f2 = px.bar(summ.dropna(subset=["median_lead_min"]), x="machine",
                    y="median_lead_min", color="pct_with_warning",
                    title="AD median lead-time to labeled event (min)")
        figs["ad_lead_time"] = f2

    f3 = px.bar(stops.head(8), x="hours", y="reason", color="category", orientation="h",
                title="Plant downtime Pareto (top reasons, hours)")
    f3.update_layout(yaxis_title="")
    figs["downtime_pareto"] = f3

    if len(rec):
        f4 = px.scatter(rec.head(40), x="bucket_start", y="category", size="n_machines",
                        color="total_hours", color_continuous_scale="OrRd",
                        title="Cross-machine recurrence (systemic faults)")
        figs["recurrence"] = f4

    # What-If example waterfall for the best-impact producing machine-day
    prod = base[(base.ProductSum > 0) & (base.UnPlannedStop > 0)]
    if len(prod):
        r = prod.sort_values("UnPlannedStop", ascending=False).iloc[0]
        res = whatif.run_scenario(r, whatif.ScenarioSpec("W1", 0.5), category_ms=r.UnPlannedStop)
        rows = whatif.waterfall_rows(res.before, res.after)
        meas = ["absolute"] + ["relative"] * (len(rows) - 2) + ["total"]
        f5 = go.Figure(go.Waterfall(x=[x[0] for x in rows], y=[x[1] for x in rows],
                                    measure=meas))
        f5.update_layout(title=f"What-If W1 50% — {r.machine} {r.date} (ΔOEE waterfall)")
        figs["whatif_waterfall"] = f5

    for name, fig in figs.items():
        fig.write_html(str(FIG / f"{name}.html"), include_plotlyjs="cdn")
    return list(figs)


def write_report(metrics, fignames):
    REP.mkdir(parents=True, exist_ok=True)
    ad = metrics.get("ad", {})
    rc = metrics.get("rca", {})
    wi = metrics.get("whatif", {})
    lines = []
    P = lines.append
    P("# trexCloud — Evaluation Report\n")
    P("Generated by `scripts/evaluate.py`. Metrics JSON: `analysis/artifacts/eval_metrics.json`. "
      "Interactive figures: `analysis/reports/figures/*.html`. Interactive demo: "
      "`uv run streamlit run app/Home.py`.\n")

    P("## 1. Anomaly Detection\n")
    if "status" in ad:
        P(f"_{ad['status']}_\n")
    else:
        P(f"- Machines scored: **{ad['machines_scored']}** · score buckets: "
          f"{ad['score_buckets']:,} · flagged anomaly windows: {ad['anomaly_windows']:,}")
        P(f"- Overall median lead-time to a labeled event: **{ad['median_lead_min_overall']:.0f} min** · "
          f"mean events with early warning: **{ad['mean_pct_with_warning']:.0f}%**\n")
        P("**Lead-time per machine** (warning before the labeled unplanned event):\n")
        P("| machine | events | median lead (min) | % with warning |")
        P("|---|--:|--:|--:|")
        for r in ad["lead_time_per_machine"]:
            P(f"| {r['machine']} | {r['n_events']} | "
              f"{'' if r['median_lead_min']!=r['median_lead_min'] else round(r['median_lead_min'])} | "
              f"{'' if r['pct_with_warning']!=r['pct_with_warning'] else round(r['pct_with_warning'])} |")
        P("\n**Precision / Recall vs score threshold** (offline windows excluded):\n")
        P("| thresh | precision | recall | flags |")
        P("|--:|--:|--:|--:|")
        for r in ad["precision_recall"]:
            P(f"| {r['thresh']} | {r['precision']} | {r['recall']} | {int(r['flags'])} |")
        P("\n> Labels are dense weak labels (unplanned stops), so precision is bounded by label "
          "density; the **lead-time** metric is the headline (did the score rise *before* the event).\n")

    P("\n## 2. Root Cause Analysis\n")
    P(f"- Unified event stream: **{rc['event_stream_rows']:,}** events "
      f"({rc['events_by_source']}).")
    P(f"- Alarms classified: **{rc['alarms_total']}** · alarm cascades detected: "
      f"**{rc['alarm_cascades']}** · alarm→stop match rate: **{rc['alarm_to_stop_match_rate']}**.")
    P(f"- Systemic (cross-machine) events: **{rc['systemic_events']}**.\n")
    P("**Alarm cascades (examples):**\n")
    for c in rc["cascade_examples"]:
        P(f"- {c['machine']} {c['ts']} — root `{c['root']}`: {c['chain']}")
    P("\n**Top systemic events:**\n")
    P("| time | category | facility root | machines | hours |")
    P("|---|---|---|--:|--:|")
    for r in rc["top_systemic"]:
        P(f"| {r['bucket_start']} | {r['category']} | {r['facility_root']} | "
          f"{r['n_machines']} | {round(r['total_hours'],1)} |")

    P("\n## 3. What-If / OEE\n")
    s = wi.get("sanity", {})
    if s:
        P(f"- Sanity (doc case Makine 1 2025-11-05, W1 50%): A "
          f"{s['doc_case_A_before']} → **{s['doc_case_A_after_W1_50']}** (doc expects ~0.50); "
          f"ΔOEE decomposition residual = {s['decompose_residual']} (exact).")
    pf = wi.get("portfolio_W1_30pct", {})
    if pf:
        P(f"- **Portfolio scenario** — reduce every machine-day's unplanned downtime by 30% (W1):")
        P(f"  - machine-days: {pf['machine_days']:,} · recovered runtime: "
          f"**{pf['total_recovered_hours']:,} h** · extra pieces: {pf['total_extra_pieces']:,.0f}")
        P(f"  - mean ΔOEE: {pf['mean_dOEE_pp']} pp · gross benefit (margin basis): "
          f"**{pf['gross_benefit_margin_basis']:,.0f} {pf['assumptions']['currency']}** "
          f"@ {pf['assumptions']['margin_per_piece']}/piece")
        P(f"  - ⚠️ {whatif.ASSUMPTION_LABEL}")

    P("\n## 4. Figures\n")
    for n in fignames:
        P(f"- [`{n}.html`](figures/{n}.html)")
    P("")
    (REP / "02_EVALUATION.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    metrics = {}
    summ, pr, cov = evaluate_ad(metrics)
    stream, rec, stops = evaluate_rca(metrics)
    base, port = evaluate_whatif(metrics)
    figs = make_figures(summ, pr, cov, rec, stops, base, port)
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "eval_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    write_report(metrics, figs)
    print("wrote analysis/artifacts/eval_metrics.json")
    print("wrote analysis/reports/02_EVALUATION.md")
    print(f"wrote {len(figs)} figures to analysis/reports/figures/")
    print("\n--- headline metrics ---")
    if "median_lead_min_overall" in metrics.get("ad", {}):
        print(f"AD: {metrics['ad']['machines_scored']} machines, "
              f"median lead {metrics['ad']['median_lead_min_overall']:.0f} min, "
              f"{metrics['ad']['mean_pct_with_warning']:.0f}% events warned")
    print(f"RCA: {metrics['rca']['alarm_cascades']} cascades, "
          f"{metrics['rca']['systemic_events']} systemic events")
    pf = metrics["whatif"]["portfolio_W1_30pct"]
    print(f"What-If W1 30%: {pf['total_recovered_hours']:,} h recovered, "
          f"{pf['gross_benefit_margin_basis']:,.0f} TRY gross")


if __name__ == "__main__":
    main()
