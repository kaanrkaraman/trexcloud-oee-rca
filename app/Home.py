"""trexCloud OEE & RCA dashboard — Overview / Baseline."""
import sys
import pathlib
sys.path.insert(0, next(str(p) for p in pathlib.Path(__file__).resolve().parents
                        if p.name == "app"))

import pandas as pd
import streamlit as st
from lib import data, charts

st.set_page_config(page_title="trexCloud OEE & RCA", page_icon="🏭", layout="wide")

st.title("🏭 trexCloud — OEE What-If & Root Cause Analysis")
st.caption("Anomaly Detection → RCA → What-If → financial impact. "
           "Data: anonymous CNC + laser plant, Aug 2025 – May 2026 (times UTC, ms).")

mm = data.machine_master()
base = data.baseline()
prod_days = base[base.ProductSum > 0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Machines", len(mm), f"{int(mm.has_telemetry.sum())} with telemetry")
c2.metric("Median OEE (prod days)", f"{prod_days.OEE.median():.1%}")
c3.metric("Median A", f"{base.A.median():.1%}")
c4.metric("Median P (prod days)", f"{prod_days.P.median():.1%}")
c5.metric("Quality", "100%", "ScrapeSum=0 (simulate Q)")

st.divider()
left, right = st.columns([1, 1])

with left:
    st.subheader("Machine tiering")
    tiers = mm.copy()
    med = base.groupby("machine").OEE.median().rename("median_OEE")
    tiers = tiers.merge(med, left_on="name", right_index=True, how="left")
    tiers["tier"] = tiers.apply(data.tier, axis=1)
    st.dataframe(
        tiers[["name", "vendor", "tier", "is_enabled", "has_telemetry", "median_OEE"]]
        .sort_values(["has_telemetry", "vendor"], ascending=[False, True])
        .style.format({"median_OEE": "{:.1%}"}),
        width="stretch", hide_index=True)
    st.caption("Rich = Mitsubishi (path/load signals defined); Sparse = Fanuc "
               "(cycle/run only); Blind = no telemetry (TurboCut, ARES). "
               "*temp/power signals are catalog-only (0 rows).")

with right:
    st.subheader("Downtime Pareto")
    by = st.radio("Rank by", ["hours", "events"], horizontal=True, key="pareto_by")
    pareto = data.stop_pareto(scope="machine", by=by)
    tab_all, tab_split = st.tabs(["All", "Faults vs Connectivity"])
    with tab_all:
        st.plotly_chart(charts.pareto_bar(pareto, value=by), width="stretch")
    with tab_split:
        faults = pareto[pareto.category == "UNPLANNED_RUNSTOP"]
        conn = pareto[pareto.category == "CONNECTIVITY"]
        st.plotly_chart(charts.pareto_bar(faults, value=by, n=8), width="stretch")
        st.caption(f"Connectivity (System Offline) total: "
                   f"{conn[by].sum():.0f} {by} — a network/collector issue, not a machine fault.")

st.divider()
st.subheader("OEE / A / P over machine × day")
metric = st.selectbox("Metric", ["OEE", "A", "P"], index=0)
only_prod = st.checkbox("Production days only (ProductSum > 0)", value=True)
b = prod_days if only_prod else base
st.plotly_chart(charts.oee_heatmap(b, metric=metric), width="stretch")
st.caption("P=0 on ~half of machine-days (no counted production) — filter to production "
           "days to read the real performance signal.")
