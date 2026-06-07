"""Pure plotly chart builders (df -> fig). No data access here."""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CAT_COLORS = {
    "UNPLANNED_RUNSTOP": "#e45756", "CONNECTIVITY": "#9c9c9c",
    "WAITING_WORK": "#f2b701", "PLANNED_BREAK": "#54a24b",
    "ALARM": "#b279a2", "ANOMALY": "#4c78a8",
}
SRC_COLORS = {"alert": "#b279a2", "stoppage": "#e45756", "offline": "#9c9c9c",
              "ad_window": "#4c78a8"}


def oee_heatmap(baseline: pd.DataFrame, metric="OEE") -> go.Figure:
    piv = baseline.pivot_table(index="machine", columns="date", values=metric,
                               aggfunc="mean")
    fig = px.imshow(piv, color_continuous_scale="RdYlGn", zmin=0, zmax=1, aspect="auto",
                    labels=dict(color=metric))
    fig.update_layout(title=f"{metric} by machine × day", height=380,
                      margin=dict(l=10, r=10, t=40, b=10))
    return fig


def pareto_bar(pareto: pd.DataFrame, value="hours", n=12) -> go.Figure:
    d = pareto.copy()
    if "category" in d:
        d["label"] = d.get("reason", d.get("category"))
        d["row"] = d["machine"].astype(str) + " · " + d["category"].astype(str)
    else:
        d["row"] = d.iloc[:, 0].astype(str)
    d = d.sort_values(value, ascending=True).tail(n)
    color = d["category"] if "category" in d else None
    fig = px.bar(d, x=value, y="row", orientation="h", color=color,
                 color_discrete_map=CAT_COLORS)
    fig.update_layout(title=f"Downtime Pareto (top {n} by {value})", height=420,
                      margin=dict(l=10, r=10, t=40, b=10), yaxis_title="")
    return fig


def event_gantt(events: pd.DataFrame, window) -> go.Figure:
    if not len(events):
        return go.Figure().update_layout(title="No events in window")
    d = events.copy()
    d["end_plot"] = d["end"].fillna(pd.Timestamp(window[1]))
    d["end_plot"] = d["end_plot"].clip(upper=pd.Timestamp(window[1]))
    fig = px.timeline(d, x_start="start", x_end="end_plot", y="source", color="category",
                      color_discrete_map=CAT_COLORS, hover_data=["label", "duration_ms"])
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(title="Event timeline", height=260,
                      margin=dict(l=10, r=10, t=40, b=10))
    fig.add_vrect(x0=window[0], x1=window[1], fillcolor="LightGray", opacity=0.15,
                  line_width=0)
    return fig


def telemetry_overlay(tel: pd.DataFrame) -> go.Figure:
    if not len(tel):
        return go.Figure().update_layout(title="No telemetry in window")
    fig = go.Figure()
    for role, g in tel.sort_values("time").groupby("canonical_role"):
        fig.add_trace(go.Scatter(x=g["time"], y=g["value"], name=str(role), mode="lines+markers",
                                 marker=dict(size=3)))
    fig.update_layout(title="Telemetry overlay (±window)", height=320,
                      margin=dict(l=10, r=10, t=40, b=10), legend_title="role")
    return fig


def oee_waterfall(rows) -> go.Figure:
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    measure = ["absolute"] + ["relative"] * (len(rows) - 2) + ["total"]
    fig = go.Figure(go.Waterfall(
        x=labels, y=vals, measure=measure,
        text=[f"{v:+.3f}" if m == "relative" else f"{v:.3f}" for v, m in zip(vals, measure)],
        connector={"line": {"color": "rgb(180,180,180)"}}))
    fig.update_layout(title="OEE impact waterfall (ΔA / ΔP / ΔQ)", height=360,
                      margin=dict(l=10, r=10, t=40, b=10), yaxis_title="OEE")
    return fig


def risk_timeline(hourly: pd.DataFrame, threshold: float, stops=None,
                  window=None) -> go.Figure:
    """hourly: [ts, risk]. stops: iterable of actual significant-stop timestamps."""
    fig = go.Figure()
    if len(hourly):
        fig.add_trace(go.Scatter(x=hourly["ts"], y=hourly["risk"], mode="lines",
                                 name="predicted stop-risk", line=dict(color="#4c78a8")))
    fig.add_hline(y=threshold, line_dash="dot", line_color="#e45756",
                  annotation_text=f"alert threshold {threshold:.2f}")
    if stops is not None and len(stops):
        s = list(stops)
        fig.add_trace(go.Scatter(x=s, y=[threshold] * len(s), mode="markers",
                                 name="actual significant stop",
                                 marker=dict(color="#e45756", symbol="x", size=9)))
    if window is not None:
        fig.add_vrect(x0=window[0], x1=window[1], fillcolor="#f2b701", opacity=0.25,
                      line_width=0, annotation_text="selected episode")
    fig.update_layout(title="Predicted stop-risk over the held-out future (hourly peak)",
                      height=320, margin=dict(l=10, r=10, t=40, b=10),
                      yaxis_title="risk", yaxis_range=[0, 1], legend_title="")
    return fig


def recurrence_heatmap(rec: pd.DataFrame) -> go.Figure:
    if not len(rec):
        return go.Figure().update_layout(title="No systemic recurrence found")
    d = rec.copy()
    fig = px.scatter(d, x="bucket_start", y="category", size="n_machines",
                     color="total_hours", color_continuous_scale="OrRd",
                     hover_data=["machines", "facility_root"], size_max=30)
    fig.update_layout(title="Cross-machine recurrence (size = #machines)", height=340,
                      margin=dict(l=10, r=10, t=40, b=10))
    return fig
