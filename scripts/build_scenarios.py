"""Build a compact, inspectable OEE/financial scenario catalog."""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pandas as pd

from trex import loaders, oee, whatif

ART = Path("analysis/artifacts")
REP = Path("analysis/reports")
COMPONENTS = ("WorkTotal", "PlannedStop", "UnPlannedStop", "WorkingTime",
              "PlannedTime", "ProductSum", "ScrapeSum")


def aggregate_machine(base, machine):
    group = base[base["machine"] == machine]
    comp = {c: float(group[c].fillna(0).sum()) for c in COMPONENTS}
    ov, a, p, q = oee.recompute(*(comp[c] for c in COMPONENTS))
    return {
        "machine": machine,
        "date": f"{group['date'].min()}..{group['date'].max()}",
        **comp, "OEE": float(ov), "A": float(a), "P": float(p), "Q": float(q),
    }, max(1, (pd.Timestamp(group["date"].max()) -
               pd.Timestamp(group["date"].min())).days + 1)


def scenario_row(sid, name, machine, scope, owner, result, financial, period_days,
                 schedule_recovered_h=0.0, note=None):
    return {
        "id": sid,
        "scenario": name,
        "machine": machine,
        "scope": scope,
        "owner": owner,
        "kind": result.spec.kind,
        "period_days": period_days,
        "delta_A": result.delta["dA"],
        "delta_P": result.delta["dP"],
        "delta_Q": result.delta["dQ"],
        "delta_OEE": result.delta["dOEE"],
        "delta_A_pp": round(result.delta["dA"] * 100, 3),
        "delta_P_pp": round(result.delta["dP"] * 100, 3),
        "delta_Q_pp": round(result.delta["dQ"] * 100, 3),
        "delta_OEE_pp": round(result.delta["dOEE"] * 100, 3),
        "recovered_runtime_h": round(result.recovered_runtime_ms / 3.6e6, 3),
        "recovered_schedule_h": round(float(schedule_recovered_h), 3),
        "extra_pieces": round(result.extra_pieces, 1),
        "gross_eur": financial.gross_benefit,
        "net_eur": financial.net_benefit,
        "roi": financial.roi,
        "payback_days": financial.payback_days,
        "note": note or result.assumptions_note,
    }


def connectivity_row():
    status = loaders.load("trex_mes_status")
    offline = status[status["is_online"].eq(False).fillna(False)].copy()
    keys = [c for c in ("instance_id", "started_on", "ended_on", "duration_milliseconds")
            if c in offline]
    offline = offline.drop_duplicates(keys)
    recovered = float(pd.to_numeric(
        offline["duration_milliseconds"], errors="coerce").fillna(0).sum() / 3.6e6)
    return {
        "id": "S4",
        "scenario": "Tesis genelinde bağlantı düzeltildi",
        "machine": "PLANT",
        "scope": f"{len(offline)} tekilleştirilmiş collector offline penceresi",
        "owner": "IT / ağ",
        "kind": "CONNECTIVITY",
        "period_days": None,
        "delta_A": 0.0, "delta_P": 0.0, "delta_Q": 0.0, "delta_OEE": 0.0,
        "delta_A_pp": 0.0, "delta_P_pp": 0.0, "delta_Q_pp": 0.0, "delta_OEE_pp": 0.0,
        "recovered_runtime_h": 0.0,
        "recovered_schedule_h": round(recovered, 3),
        "extra_pieces": 0.0,
        "gross_eur": 0.0, "net_eur": 0.0, "roi": None, "payback_days": None,
        "note": ("Bağlantı düzeltmesi veri ve program görünürlüğünü geri getirir. Bu bir IT "
                 "aksiyonudur; makine OEE'sine veya kestirimci bakım değerine yazılmaz."),
    }


def write_report(payload):
    rows = payload["rows"]
    lines = [
        "# Inspectable Scenario Catalog",
        "",
        "Each machine scenario is recomputed from raw OEE components. Connectivity is "
        "short-circuited because System Offline is an IT/collector issue, not machine downtime.",
        "",
        "| ID | Scenario | Scope | Owner | dA pp | dP pp | dQ pp | dOEE pp | Runtime h | Schedule h | Extra pieces | Gross EUR | Net EUR | Payback d |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        payback = "-" if r["payback_days"] is None else f"{r['payback_days']:.1f}"
        lines.append(
            f"| {r['id']} | {r['scenario']} | {r['machine']} / {r['scope']} | {r['owner']} | "
            f"{r['delta_A_pp']:.2f} | {r['delta_P_pp']:.2f} | {r['delta_Q_pp']:.2f} | "
            f"{r['delta_OEE_pp']:.2f} | {r['recovered_runtime_h']:.1f} | "
            f"{r['recovered_schedule_h']:.1f} | {r['extra_pieces']:.0f} | "
            f"{r['gross_eur']:,.0f} | {r['net_eur']:,.0f} | {payback} |")
    lines += ["", "## Interpretation", ""]
    for r in rows:
        lines.append(f"- **{r['id']}**: {r['note']}")
    lines += ["", f"> {payload['assumption_label']}", ""]
    (REP / "07_SCENARIOS.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    base = pd.read_parquet(ART / "oee_baseline.parquet")
    pareto = pd.read_csv(ART / "downtime_pareto.csv")
    assumptions = whatif.FinancialAssumptions(
        contribution_margin_per_piece=12.0,
        downtime_cost_per_hour=80.0,
        intervention_cost=300.0,
        horizon_days=30,
        currency="EUR",
        value_recovered_time_as="downtime_cost",
    )
    rows = []

    m1, days1 = aggregate_machine(base, "Makine 1")
    m1_top = pareto[(pareto["machine"] == "Makine 1") &
                    ~pareto["reason"].str.contains("Offline|Connect", case=False, na=False)] \
        .sort_values("hours", ascending=False).iloc[0]
    r1 = whatif.run_scenario(
        m1, whatif.ScenarioSpec("W1", 0.30, str(m1_top["reason"])),
        category_ms=float(m1_top["hours"]) * 3.6e6)
    f1 = whatif.compute_financials(r1, assumptions, period_days=days1)
    rows.append(scenario_row(
        "S1", "En büyük plansız duruş kalemi -%30", "Makine 1",
        f"{m1_top['reason']} / tüm OEE baseline dönemi", "Bakım", r1, f1, days1,
        note=f"{m1_top['reason']} süresi %30 azaltılır; etki A ve OEE üzerinden hesaplanır."))

    m2, days2 = aggregate_machine(base, "Makine 2")
    r2 = whatif.run_scenario(
        m2, whatif.ScenarioSpec("W2", category="Duruş", abs_ms=8 * 3.6e6),
        category_ms=8 * 3.6e6)
    f2 = whatif.compute_financials(r2, assumptions, period_days=days2)
    rows.append(scenario_row(
        "S2", "8 saat plansız -> planlı bakım", "Makine 2",
        "Tüm OEE baseline dönemi; sınıflandırma/program değişikliği", "Bakım planlama",
        r2, f2, days2,
        note="8 saat plansız duruş planlı bakıma taşınır; A yükselir fakat runtime kazanılmaz."))

    m4, days4 = aggregate_machine(base, "Makine 4")
    r3 = whatif.run_scenario(m4, whatif.ScenarioSpec("W4", 0.10))
    f3 = whatif.compute_financials(r3, assumptions, period_days=days4)
    rows.append(scenario_row(
        "S3", "Performans/çevrim +%10", "Makine 4",
        "Tüm OEE baseline dönemi; ProductSum=0", "Proses mühendisliği", r3, f3, days4,
        note="ProductSum=0 olduğu için P kolu inerttir; OEE veya finansal fayda üretmez."))

    rows.append(connectivity_row())
    payload = {
        "assumption_label": whatif.ASSUMPTION_LABEL,
        "assumptions": asdict(assumptions),
        "rows": rows,
    }
    ART.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    (ART / "scenarios.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print("wrote analysis/artifacts/scenarios.json")
    print("wrote analysis/reports/07_SCENARIOS.md")


if __name__ == "__main__":
    main()
