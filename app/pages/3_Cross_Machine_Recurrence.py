"""Cross-machine recurrence: systemic/facility faults where the same category hits
multiple machines in the same time bucket."""
import sys
import pathlib
sys.path.insert(0, next(str(p) for p in pathlib.Path(__file__).resolve().parents
                        if p.name == "app"))

import streamlit as st
from lib import data, charts

st.set_page_config(page_title="Cross-Machine Recurrence", page_icon="🌐", layout="wide")
st.title("🌐 Cross-Machine Recurrence — systemic faults")
st.caption("Same fault category across multiple machines in one time bucket ⇒ a facility "
           "issue (network/air/power), not an isolated machine fault.")

c = st.columns([1, 1, 2])
bucket = c[0].selectbox("Time bucket", ["1h", "30min", "2h", "1D"], index=0)
min_m = c[1].slider("Min machines", 2, 8, 2)
rec = data.recurrence(bucket=bucket, min_machines=min_m)

st.plotly_chart(charts.recurrence_heatmap(rec), width="stretch")

st.subheader("Top systemic events")
if len(rec):
    show = rec.head(15).copy()
    show["machines"] = show["machines"].apply(lambda xs: ", ".join(xs))
    st.dataframe(show[["bucket_start", "category", "facility_root", "n_machines",
                       "total_hours", "systemic_score"]]
                 .style.format({"total_hours": "{:.1f}", "systemic_score": "{:.1f}"}),
                 width="stretch", hide_index=True)
    top = rec.iloc[0]
    st.success(f"Largest systemic event: **{top.category}** ({top.facility_root}) hit "
               f"**{top.n_machines} machines** at {top.bucket_start} "
               f"({top.total_hours:.0f} machine-hours). "
               + ("Connectivity — fix collector/network; not machine OEE."
                  if top.category == "CONNECTIVITY"
                  else "Investigate the shared facility cause."))
else:
    st.write("No recurrence at this threshold.")
