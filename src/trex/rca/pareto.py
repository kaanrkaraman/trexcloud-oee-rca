"""Alarm/stop Pareto — by downtime hours or event count, planned vs unplanned,
connectivity separated. Reuses the prebuilt downtime_pareto.csv when possible.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from .. import loaders
from .events import load_stoppage_events, load_alert_events

ART = Path("analysis/artifacts")


def stop_pareto(dir=None, *, by="hours", scope="machine", include_planned=False,
                separate_connectivity=True) -> pd.DataFrame:
    """[machine|'PLANT', category, reason, events, hours] ranked by `by`."""
    ev = load_stoppage_events(dir=dir)
    if not include_planned:
        ev = ev[ev.category != "PLANNED_BREAK"]
    if not separate_connectivity:
        ev = ev[ev.category != "CONNECTIVITY"]
    ev = ev.copy()
    ev["hours"] = loaders.ms_to_hours(ev.duration_ms)
    keys = ["machine", "category", "label"] if scope == "machine" else ["category", "label"]
    g = (ev.groupby(keys, dropna=False)
           .agg(events=("source", "size"), hours=("hours", "sum")).reset_index()
           .rename(columns={"label": "reason"}))
    if scope != "machine":
        g.insert(0, "machine", "PLANT")
    sort_col = "hours" if by == "hours" else "events"
    return g.sort_values(sort_col, ascending=False).reset_index(drop=True)


def alarm_pareto(dir=None, *, scope="machine") -> pd.DataFrame:
    """[machine, category, occurrences, machines_affected] — Makine 1 & 2 only."""
    ev = load_alert_events(dir=dir)
    if not len(ev):
        return pd.DataFrame(columns=["machine", "category", "occurrences"])
    keys = ["machine", "category"] if scope == "machine" else ["category"]
    g = (ev.groupby(keys, dropna=False)
           .agg(occurrences=("source", "size"),
                machines_affected=("machine", "nunique")).reset_index())
    if scope != "machine":
        g.insert(0, "machine", "PLANT")
    return g.sort_values("occurrences", ascending=False).reset_index(drop=True)


def category_hours(dir=None, machine=None, category=None) -> float:
    """Total unplanned downtime hours for a (machine, category) — feeds What-If W1."""
    ev = load_stoppage_events(dir=dir)
    if machine is not None:
        ev = ev[ev.machine == machine]
    if category is not None:
        ev = ev[ev.category == category]
    return float(loaders.ms_to_hours(ev.duration_ms).sum())
