"""Cached data access for the dashboard. Three tiers:
  1. prebuilt artifacts (instant)         -> baseline, pareto, signal map, AD outputs
  2. cached library calls over MES tables -> event stream, recurrence
  3. bounded live telemetry (RCA overlay) -> cache-keyed on (machine, window, roles)
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st

from trex import loaders, oee, rca

ART = Path("analysis/artifacts")


@st.cache_data(show_spinner=False)
def machine_master() -> pd.DataFrame:
    return loaders.machine_master()


@st.cache_data(show_spinner=False)
def baseline() -> pd.DataFrame:
    p = ART / "oee_baseline.parquet"
    df = pd.read_parquet(p) if p.exists() else oee.baseline(level=1)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


@st.cache_data(show_spinner=False)
def downtime_pareto() -> pd.DataFrame:
    p = ART / "downtime_pareto.csv"
    return pd.read_csv(p) if p.exists() else rca.stop_pareto()


@st.cache_data(show_spinner=False)
def signal_map() -> pd.DataFrame:
    p = ART / "signal_map.csv"
    return pd.read_csv(p)


@st.cache_data(show_spinner=False)
def ad_windows() -> pd.DataFrame:
    p = ART / "ad_anomaly_windows.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    for c in ("window_start", "window_end"):
        df[c] = pd.to_datetime(df[c], utc=True)
    return df


@st.cache_data(show_spinner=False)
def ad_scores() -> pd.DataFrame:
    p = ART / "ad_scores.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df


@st.cache_data(show_spinner=False)
def event_stream() -> pd.DataFrame:
    return rca.build_event_stream(ad_df=ad_windows() if len(ad_windows()) else None)


@st.cache_data(show_spinner=False)
def stop_pareto(scope="machine", by="hours", include_planned=False) -> pd.DataFrame:
    return rca.stop_pareto(scope=scope, by=by, include_planned=include_planned)


@st.cache_data(show_spinner=False)
def alarm_pareto() -> pd.DataFrame:
    return rca.alarm_pareto()


@st.cache_data(show_spinner=False)
def recurrence(bucket="1h", min_machines=2) -> pd.DataFrame:
    return rca.correlate_with_offline(
        rca.find_recurrence(stream=event_stream(), bucket=bucket, min_machines=min_machines))


@st.cache_data(show_spinner="Loading telemetry window…")
def timeline(machine: str, start, end, with_telemetry=True):
    """Bounded RCA overlay. Cache-keyed on args; window kept tight by callers."""
    tl = rca.build_event_timeline(machine, start, end, stream=event_stream(),
                                  ad_df=ad_windows() if len(ad_windows()) else None,
                                  with_telemetry=with_telemetry)
    return tl.events, tl.telemetry, tl.has_telemetry


@st.cache_data(show_spinner=False)
def predict_metrics() -> dict:
    import json
    p = ART / "predict_metrics.json"
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data(show_spinner=False)
def fanuc_risk() -> pd.DataFrame:
    p = ART / "fanuc_risk.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df


@st.cache_data(show_spinner=False)
def fanuc_episodes() -> pd.DataFrame:
    p = ART / "fanuc_risk_episodes.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    for c in ("start", "end"):
        df[c] = pd.to_datetime(df[c], utc=True)
    return df


@st.cache_data(show_spinner=False)
def fanuc_meta() -> dict:
    import json
    p = ART / "fanuc_model_meta.json"
    return json.loads(p.read_text()) if p.exists() else {}


def machines(telemetry_only=False) -> list[str]:
    mm = machine_master()
    if telemetry_only:
        mm = mm[mm.has_telemetry]
    return sorted(mm.name.tolist())


TIERS = {"Mitsubishi": "Rich", "Fanuc": "Sparse", "Nukon": "Blind"}


def tier(row) -> str:
    if not row.has_telemetry:
        return "Blind (MES-only)"
    return "Rich (temp/load*)" if row.vendor == "Mitsubishi" else "Sparse (cycle/run)"
