"""RCA Event Explorer: pick a machine + window -> timeline, telemetry overlay,
alarm cascade, root-cause card. 'Send to What-If' hands off a recoverable-downtime hint."""
import sys
import pathlib
sys.path.insert(0, next(str(p) for p in pathlib.Path(__file__).resolve().parents
                        if p.name == "app"))

import pandas as pd
import streamlit as st
from lib import data, charts, state
from trex import rca

st.set_page_config(page_title="RCA Event Explorer", page_icon="🔎", layout="wide")
st.title("🔎 RCA Event Explorer")

mm = data.machine_master()
adw = data.ad_windows()

c = st.columns([1.2, 1, 1, 1])
machine = c[0].selectbox("Machine", data.machines(),
                         index=data.machines().index("Makine 1"))
has_tel = bool(mm[mm.name == machine].has_telemetry.iloc[0])

# anchor presets: known flagship event + top AD anomalies for this machine
presets = {"Makine 1 — AIR PRESSURE (2026-01-12 04:47)": ("Makine 1", "2026-01-12 04:40", "2026-01-12 05:00"),
           "Makine 2 — EMERGENCY STOP (2026-01-12 04:59)": ("Makine 2", "2026-01-12 04:50", "2026-01-12 05:10")}
preset = c[1].selectbox("Preset event", ["(custom)"] + list(presets), index=0)

if preset != "(custom)":
    machine, ds, de = presets[preset]
    start, end = pd.Timestamp(ds, tz="UTC"), pd.Timestamp(de, tz="UTC")
else:
    mwin = adw[adw.machine == machine].sort_values("peak_score", ascending=False)
    default_day = (mwin.window_start.iloc[0].date() if len(mwin)
                   else pd.Timestamp("2026-01-12").date())
    day = c[1].date_input("Day", value=default_day)
    hour = c[2].slider("Hour (UTC)", 0, 23, 4)
    span = c[3].slider("Span (min)", 10, 120, 30)
    start = pd.Timestamp(f"{day} {hour:02d}:00", tz="UTC")
    end = start + pd.Timedelta(minutes=span)

st.caption(f"Window: {start} → {end}  ·  machine **{machine}** "
           f"({'telemetry' if has_tel else 'MES-only — no telemetry'})")

show_tel = st.toggle("Load telemetry overlay (bounded read)", value=has_tel,
                     disabled=not has_tel)
events, tel, has_telemetry = data.timeline(machine, start, end, with_telemetry=show_tel)

st.plotly_chart(charts.event_gantt(events, (start - pd.Timedelta("15min"),
                                            end + pd.Timedelta("5min"))),
                width="stretch")

if has_tel and show_tel:
    st.plotly_chart(charts.telemetry_overlay(tel), width="stretch")
elif not has_tel:
    st.info(f"{machine} has no Nightwatch telemetry — RCA relies on MES events only.")

col_l, col_r = st.columns([1, 1])
with col_l:
    st.subheader("Alarm cascade")
    casc = [c for c in rca.group_alarm_arrays(machine)
            if start - pd.Timedelta("30min") <= c.timestamp <= end + pd.Timedelta("30min")]
    if casc:
        cc = casc[0]
        st.markdown(f"**{cc.timestamp}** — root: `{cc.root_category}`")
        st.markdown(" → ".join(f"**{a}**" if a == cc.root_alarm else a for a in cc.alarms))
        st.caption("Ordered by causal precedence (upstream → downstream); "
                   "root = most-upstream, not lowest array index.")
    else:
        st.write("No multi-alarm cascade in this window.")

with col_r:
    st.subheader("Root cause card")
    card = rca.build_root_cause_card(machine, start, end,
                                     ad_df=adw if len(adw) else None,
                                     stream=data.event_stream())
    st.markdown(f"**Trigger:** {card.trigger}")
    st.markdown(f"**Pattern:** `{card.pattern}`  ·  **Linked downtime:** "
                f"{card.linked_downtime_hours} h"
                + ("  ·  ⚠️ connectivity" if card.is_connectivity else ""))
    st.markdown("**Evidence:**")
    for e in card.evidence:
        st.markdown(f"- {e}")
    st.markdown("**Ranked hypotheses:**")
    for h in card.hypotheses[:3]:
        st.markdown(f"- *{h['cause']}* — likelihood {h['likelihood']:.0%}  \n"
                    f"  ↳ {h['recommended_action']}")

hint = rca.to_whatif_bridge(card)
if st.button("➡️ Send to What-If", type="primary"):
    state.set_whatif_hint({"machine": hint.machine, "category": hint.category,
                           "recoverable_ms": hint.recoverable_ms,
                           "scenario": hint.target_scenario, "note": hint.note})
    st.success(f"Sent: {hint.note}  → open the What-If page.")
