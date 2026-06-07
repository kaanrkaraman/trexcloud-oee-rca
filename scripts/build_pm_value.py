"""Build the held-out Fanuc prediction -> OEE -> EUR attribution artifact."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from trex import whatif
from trex.rca import crossmachine

ART = Path("analysis/artifacts")
REP = Path("analysis/reports")


def _fmt(value, digits=1):
    return f"{value:,.{digits}f}"


def write_report(payload):
    d = payload["deployed"]
    o = d["oee"]
    fin = d["financial"]
    opt = payload["sensitivity"]["economic_optimum"]
    lines = [
        "# Prediction to OEE and Financial Value",
        "",
        "This report connects the deployed supervised Fanuc stop predictor to attributable "
        "OEE and financial value on the held-out future. AD remains a separate unsupervised "
        "RCA evidence layer.",
        "",
        "## Audited deployed operating point",
        "",
        f"- Threshold: **{d['threshold']:.4f}** (unchanged deployed threshold)",
        f"- Model: ROC-AUC **{payload['model']['ROC_AUC']:.3f}**, PR-AUC "
        f"**{payload['model']['PR_AUC']:.3f}**, lift **{payload['model']['lift']:.2f}x**",
        f"- Significant stops caught: **{d['caught_stops']}/{d['significant_stops']}** "
        f"(event recall **{d['recall']:.1%}**)",
        f"- Alert episodes: **{d['episodes']}**; episode precision **{d['episode_precision']:.1%}**; "
        f"false-alarm episodes **{d['false_alarm_episodes']}**",
        f"- Caught downtime: **{_fmt(d['caught_downtime_h'])} h**; attributable prevented time "
        f"at e={payload['assumptions']['pm']['intervention_effectiveness']:.0%}: "
        f"**{_fmt(d['prevented_h'])} h**",
        f"- Attributable delta: **+{o['delta']['dA'] * 100:.2f} pp A**, "
        f"**+{o['delta']['dOEE'] * 100:.2f} pp OEE**; delta P/Q = 0",
        f"- Observed net: **EUR {_fmt(fin['observed']['net_eur'], 0)}**; "
        f"annualized projection: **{_fmt(fin['annualized']['prevented_h'])} h**, "
        f"**EUR {_fmt(fin['annualized']['net_eur'], 0)} net**",
        "",
        f"> {payload['assumptions']['label']}",
        "",
        "## Per-machine held-out results",
        "",
        "| Machine | Stops | Caught | Recall | Caught h | Prevented h | Episodes | Ep. precision | dOEE pp |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in d["per_machine"]:
        lines.append(
            f"| {row['machine']} | {row['significant_stops']} | {row['caught_stops']} | "
            f"{row['recall']:.1%} | {row['caught_downtime_h']:.1f} | {row['prevented_h']:.1f} | "
            f"{row['episodes']} | {row['episode_precision']:.1%} | "
            f"{row['oee']['delta']['dOEE'] * 100:.2f} |")
    lines += [
        "",
        "## Economic threshold sensitivity",
        "",
        "The following optimum is selected retrospectively on the held-out window and is not "
        "presented as the deployed result.",
        "",
        f"- Net-EUR optimum threshold: **{opt['threshold']:.4f}**",
        f"- Recall: **{opt['recall']:.1%}**; episodes: **{opt['episodes']}**; "
        f"annualized net: **EUR {_fmt(opt['annualized_net_eur'], 0)}**",
        "",
        "## Headline",
        "",
        f"> {payload['headline']}",
        "",
    ]
    (REP / "08_PM_VALUE.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    meta = json.loads((ART / "fanuc_model_meta.json").read_text(encoding="utf-8"))
    scored = pd.read_parquet(ART / "fanuc_risk.parquet")
    scored["ts"] = pd.to_datetime(scored["ts"], utc=True)
    audited_episodes = pd.read_csv(ART / "fanuc_risk_episodes.csv")
    baseline = pd.read_parquet(ART / "oee_baseline.parquet")
    stops = crossmachine.significant_unplanned()

    pm_assm = whatif.PMValueAssumptions(
        intervention_effectiveness=0.35, horizon_min=60, annual_days=365)
    fin_assm = whatif.FinancialAssumptions(
        contribution_margin_per_piece=12.0,
        downtime_cost_per_hour=80.0,
        intervention_cost=300.0,
        horizon_days=30,
        currency="EUR",
        value_recovered_time_as="downtime_cost",
    )
    deployed = whatif.evaluate_operating_point(
        scored, stops, baseline, meta["threshold"], pm_assm, fin_assm,
        episodes_override=audited_episodes)
    sensitivity = whatif.threshold_sensitivity(
        scored, stops, baseline, meta["threshold"], pm_assm, fin_assm,
        deployed_episodes=audited_episodes)
    annual = deployed["financial"]["annualized"]
    headline = (
        "AI kestirimci bakım (Fanuc, yıllık projeksiyon) -> "
        f"~{annual['prevented_h']:.0f} saat geri kazanım, "
        f"+{deployed['oee']['delta']['dOEE'] * 100:.2f} puan OEE, "
        f"~EUR {annual['net_eur']:,.0f} net (varsayımlar etiketli)."
    )
    payload = {
        "scope": {
            "machines": meta["machines"],
            "prediction": "supervised Fanuc predictor only",
            "exclusions": "Mitsubishi and telemetry-blind machines remain in RCA/OEE What-If only",
        },
        "model": {k: meta[k] for k in (
            "ROC_AUC", "PR_AUC", "base_rate", "lift", "threshold",
            "test_start", "test_end", "n_episodes", "episode_precision")},
        "audit_note": (
            "Deployed episode count/precision come from the committed held-out episode artifact; "
            "strict stop catches are recomputed from fanuc_risk.parquet."),
        "assumptions": whatif.pmvalue.assumptions_dict(pm_assm, fin_assm),
        "deployed": deployed,
        "sensitivity": sensitivity,
        "headline": headline,
    }
    ART.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    (ART / "pm_value.json").write_text(
        json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(f"deployed threshold={deployed['threshold']:.4f} stops="
          f"{deployed['caught_stops']}/{deployed['significant_stops']} "
          f"episodes={deployed['episodes']} dOEE={deployed['oee']['delta']['dOEE']:.4f}")
    print("wrote analysis/artifacts/pm_value.json")
    print("wrote analysis/reports/08_PM_VALUE.md")


if __name__ == "__main__":
    main()
