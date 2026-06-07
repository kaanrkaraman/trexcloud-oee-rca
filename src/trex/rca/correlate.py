"""Temporal correlation: alarm -> stop lag, and pattern classification."""
from __future__ import annotations
import pandas as pd
from .events import load_alert_events, load_stoppage_events


def correlate_alarms_to_stops(machine, dir=None, *, max_lag="10min") -> pd.DataFrame:
    """For each alarm, the nearest following unplanned stop within max_lag."""
    al = load_alert_events(dir=dir)
    al = al[al.machine == machine].sort_values("start")
    ss = load_stoppage_events(dir=dir)
    ss = ss[(ss.machine == machine) & (ss.category == "UNPLANNED_RUNSTOP")].sort_values("start")
    if not len(al) or not len(ss):
        return pd.DataFrame(columns=["alarm_category", "stop_reason", "lag_seconds",
                                     "alarm_start", "stop_start", "matched"])
    left = al[["start", "category"]].rename(columns={"start": "alarm_start",
                                                     "category": "alarm_category"})
    right = ss[["start", "label"]].rename(columns={"start": "stop_start",
                                                   "label": "stop_reason"})
    m = pd.merge_asof(left, right, left_on="alarm_start", right_on="stop_start",
                      direction="forward", tolerance=pd.Timedelta(max_lag))
    m["lag_seconds"] = (m.stop_start - m.alarm_start).dt.total_seconds()
    m["matched"] = m.stop_start.notna()
    return m.reset_index(drop=True)


def classify_pattern(*, has_alarm, lag_seconds=None, has_ad_drift=False,
                     is_connectivity=False) -> str:
    """Categorize the anomaly's causal shape for the root-cause card."""
    if is_connectivity:
        return "CONNECTIVITY"
    if has_alarm and has_ad_drift:
        return "DRIFT_ALARM_STOP"      # telemetry drift preceded the alarm (predictive)
    if has_alarm and lag_seconds is not None and lag_seconds <= 60:
        return "ALARM_CAUSED_STOP"
    if has_alarm:
        return "ALARM_RELATED_STOP"
    return "OPERATIONAL_STOP"          # unplanned stop, no alarm / no offline
