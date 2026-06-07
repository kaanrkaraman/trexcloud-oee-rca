"""Cross-machine recurrence: same category in the same time bucket across multiple
machines => systemic/facility fault rather than an isolated machine issue."""
from __future__ import annotations
import pandas as pd
from .. import loaders
from .events import build_event_stream


def find_recurrence(dir=None, *, stream=None, bucket="1h", min_machines=2,
                    categories=("CONNECTIVITY", "AIR_PRESSURE", "EMERGENCY_STOP",
                                "UNPLANNED_RUNSTOP")) -> pd.DataFrame:
    """[bucket_start, category, machines, n_machines, total_hours, systemic_score]."""
    s = stream if stream is not None else build_event_stream(dir)
    s = s[s.category.isin(categories)].copy()
    if not len(s):
        return pd.DataFrame(columns=["bucket_start", "category", "machines",
                                     "n_machines", "total_hours", "systemic_score"])
    s["bucket_start"] = s.start.dt.floor(bucket)
    s["hours"] = loaders.ms_to_hours(s.duration_ms)
    g = (s.groupby(["bucket_start", "category"])
           .agg(machines=("machine", lambda x: sorted(set(x.dropna()))),
                n_machines=("machine", "nunique"),
                total_hours=("hours", "sum")).reset_index())
    g = g[g.n_machines >= min_machines]
    g["systemic_score"] = (g.n_machines * g.total_hours.clip(lower=0.01)).round(2)
    return g.sort_values("systemic_score", ascending=False).reset_index(drop=True)


def correlate_with_offline(recurrence_df: pd.DataFrame, dir=None, *,
                           stream=None) -> pd.DataFrame:
    """Tag systemic candidates with a facility root guess."""
    if not len(recurrence_df):
        return recurrence_df.assign(facility_root=[])
    def root(cat):
        return {"CONNECTIVITY": "FACILITY_NETWORK", "AIR_PRESSURE": "FACILITY_AIR",
                "EMERGENCY_STOP": "FACILITY_POWER_OR_SAFETY"}.get(cat, "MULTI_MACHINE")
    out = recurrence_df.copy()
    out["facility_root"] = out.category.map(root)
    return out
