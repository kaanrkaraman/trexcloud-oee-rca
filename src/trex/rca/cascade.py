"""ALERT_ARRAY cascade analysis: group simultaneous Fanuc alarms and order them
causally (lowest CAUSAL_PRECEDENCE rank = most upstream = likely root)."""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from .events import load_alert_events
from . import rules


@dataclass
class AlarmCascade:
    machine: str
    timestamp: pd.Timestamp
    alarms: list           # raw alarm texts, ordered upstream -> downstream
    categories: list       # matching categories in the same order
    root_alarm: str        # most-upstream alarm text
    root_category: str
    raw_indices: list


def group_alarm_arrays(machine, dir=None, *, ts_tol="2s",
                       min_size=2) -> list[AlarmCascade]:
    al = load_alert_events(dir=dir)
    al = al[al.machine == machine].copy()
    if not len(al):
        return []
    al = al.sort_values("start")
    bucket = al.start.dt.floor(ts_tol)
    out = []
    for ts, g in al.groupby(bucket):
        if len(g) < min_size:
            continue
        g = g.assign(rank=g.category.map(rules.CAUSAL_PRECEDENCE).fillna(99))
        g = g.sort_values("rank")
        idx = [m.get("index") for m in g.meta]
        out.append(AlarmCascade(
            machine=machine, timestamp=pd.Timestamp(ts),
            alarms=list(g.label), categories=list(g.category),
            root_alarm=g.label.iloc[0], root_category=g.category.iloc[0],
            raw_indices=idx))
    return out
