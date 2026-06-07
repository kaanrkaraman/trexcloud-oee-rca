"""What-If: pick a machine-day + intervention -> recomputed OEE, ΔOEE waterfall,
financial card. Pre-fills from an RCA 'Send to What-If' hint when present."""
import sys
import pathlib
sys.path.insert(0, next(str(p) for p in pathlib.Path(__file__).resolve().parents
                        if p.name == "app"))

import pandas as pd
import streamlit as st
from lib import data, charts, state
from trex import whatif, rca

st.set_page_config(page_title="What-If / OEE", page_icon="🎛️", layout="wide")
st.title("🎛️ What-If — OEE simulation & financial impact")

base = data.baseline()
hint = state.get_whatif_hint()
if hint:
    st.info(f"From RCA: {hint['note']}")

SCEN = {"W1 — eliminate top unplanned category": "W1",
        "W2 — reclassify UNPLANNED → PLANNED": "W2",
        "W3 — reduce unplanned stop duration": "W3",
        "W4 — improve performance / cycle": "W4",
        "W5 — simulate scrap (Q)": "W5"}

c = st.columns([1.2, 1, 1, 1])
mlist = data.machines()
m_default = hint["machine"] if hint and hint["machine"] in mlist else "Makine 1"
machine = c[0].selectbox("Machine", mlist, index=mlist.index(m_default))
bm = base[base.machine == machine].sort_values("UnPlannedStop", ascending=False)
if not len(bm):
    st.warning("No baseline rows for this machine."); st.stop()
days = bm.date.astype(str).tolist()
day = c[1].selectbox("Day (high-downtime first)", days, index=0)
scen_label = c[2].selectbox("Scenario", list(SCEN), index=0)
kind = SCEN[scen_label]
pct = c[3].slider("Magnitude %", 0, 100, 50) / 100.0

row = bm[bm.date.astype(str) == day].iloc[0]

# category target for W1/W2/W3 from this machine's pareto
pareto_m = data.stop_pareto(scope="machine")
pareto_m = pareto_m[(pareto_m.machine == machine) &
                    (pareto_m.category.isin(["UNPLANNED_RUNSTOP", "WAITING_WORK"]))]
category = "UNPLANNED_RUNSTOP"
category_ms = float(row.UnPlannedStop)
if kind in ("W1", "W2", "W3"):
    category = st.selectbox("Target category", ["UNPLANNED_RUNSTOP"], index=0)

scrap_base = 0.0
if kind == "W5":
    scrap_base = st.slider("Assumed current scrap % (SIMULATED)", 0, 20, 5) / 100.0

spec = whatif.ScenarioSpec(kind=kind, pct=pct, category=category,
                           scrap_baseline_pct=scrap_base)
res = whatif.run_scenario(row, spec, category_ms=category_ms)

st.divider()
k = st.columns(4)
for col, name in zip(k, ["OEE", "A", "P", "Q"]):
    col.metric(name, f"{res.after[name]:.1%}",
               f"{res.after[name] - res.before[name]:+.1%}")
if res.assumptions_note:
    st.caption("ℹ️ " + res.assumptions_note)

wl, wr = st.columns([1.2, 1])
with wl:
    st.plotly_chart(charts.oee_waterfall(whatif.waterfall_rows(res.before, res.after)),
                    width="stretch")
    st.caption(f"Recovered runtime: {res.recovered_runtime_ms/3.6e6:.2f} h  ·  "
               f"extra pieces: {res.extra_pieces:.0f}")

with wr:
    st.subheader("Financial impact")
    st.caption("⚠️ " + whatif.ASSUMPTION_LABEL)
    a = whatif.FinancialAssumptions()
    a.contribution_margin_per_piece = st.number_input("Margin / piece", value=12.0)
    a.downtime_cost_per_hour = st.number_input("Downtime cost / h", value=80.0)
    a.intervention_cost = st.number_input("Intervention cost", value=300.0)
    a.value_recovered_time_as = st.radio("Value recovered time as",
                                         ["margin", "downtime_cost"], horizontal=True)
    fin = whatif.compute_financials(res, a, period_days=1)
    f1, f2, f3 = st.columns(3)
    f1.metric(f"Gross / {a.horizon_days}d", f"{fin.gross_benefit:,.0f} {a.currency}")
    f2.metric("Net benefit", f"{fin.net_benefit:,.0f} {a.currency}")
    f3.metric("Payback (days)", "—" if fin.payback_days is None else f"{fin.payback_days:.1f}")
    st.json(fin.breakdown, expanded=False)

with st.expander("Baseline components (ms)"):
    st.json({k: res.before[k] for k in ("WorkTotal", "PlannedStop", "UnPlannedStop",
                                        "WorkingTime", "PlannedTime", "ProductSum")})
