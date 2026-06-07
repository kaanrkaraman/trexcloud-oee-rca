"""Weak anomaly labels for VALIDATION ONLY (never training targets).

- anomaly_label_windows: unplanned stoppages + alerts, EXCLUDING System Offline & planned.
- offline_windows: connectivity windows (status offline + 'System Offline' slices) -> the
  exclude mask applied to both fitting and scoring (no telemetry exists during offline).
"""
from __future__ import annotations
import pandas as pd
from .. import loaders

OFFLINE_TEXT = "System Offline"


def _reason_lookup(dir=None) -> pd.DataFrame:
    rd = loaders.load("trex_mes_reading_def", dir=dir)[["uid", "display_text"]]
    return rd.drop_duplicates("uid").rename(columns={"uid": "reading_def_uid"})


def anomaly_label_windows(dir=None) -> pd.DataFrame:
    """[machine, started_on, ended_on, source, label_text, dur_h] — unplanned faults only."""
    mm = loaders.machine_master(dir=dir)[["unit_uid", "name"]]
    out = []

    ss = loaders.load("trex_mes_stoppage_slice", dir=dir)
    ss = ss[ss.is_planned.eq(False).fillna(False)]
    ss = ss.merge(_reason_lookup(dir=dir), on="reading_def_uid", how="left") \
           .merge(mm, on="unit_uid", how="left")
    ss = ss[~ss.display_text.fillna("").str.contains(OFFLINE_TEXT, case=False)]
    s1 = pd.DataFrame({
        "machine": ss.name, "started_on": ss.started_on, "ended_on": ss.ended_on,
        "source": "stoppage", "label_text": ss.display_text,
        "dur_h": loaders.ms_to_hours(ss.duration_milliseconds),
    })
    out.append(s1)

    al = loaders.load("trex_mes_alert", dir=dir).merge(mm, on="unit_uid", how="left")
    a1 = pd.DataFrame({
        "machine": al.name, "started_on": al.started_on, "ended_on": al.ended_on,
        "source": "alert", "label_text": al.value.astype("string").str.strip(),
        "dur_h": loaders.ms_to_hours(al.duration_milliseconds),
    })
    out.append(a1)

    df = pd.concat(out, ignore_index=True).dropna(subset=["machine", "started_on"])
    return df.sort_values(["machine", "started_on"]).reset_index(drop=True)


def offline_windows(dir=None) -> pd.DataFrame:
    """[machine|None, started_on, ended_on, source] connectivity windows to EXCLUDE."""
    mm = loaders.machine_master(dir=dir)[["unit_uid", "name"]]
    out = []

    ss = loaders.load("trex_mes_stoppage_slice", dir=dir).merge(
        _reason_lookup(dir=dir), on="reading_def_uid", how="left").merge(
        mm, on="unit_uid", how="left")
    so = ss[ss.display_text.fillna("").str.contains(OFFLINE_TEXT, case=False)]
    out.append(pd.DataFrame({"machine": so.name, "started_on": so.started_on,
                             "ended_on": so.ended_on, "source": "stoppage_offline"}))

    st = loaders.load("trex_mes_status", dir=dir)
    st = st[st.is_online.eq(False).fillna(False)]
    out.append(pd.DataFrame({"machine": pd.NA, "started_on": st.started_on,
                             "ended_on": st.ended_on, "source": "status_offline",
                             "instance_id": st.instance_id}))

    df = pd.concat(out, ignore_index=True).dropna(subset=["started_on"])
    return df.reset_index(drop=True)
