"""Recompute A / P / Q / OEE from oee_summary JSON components.

The stored scalar `oee`/`availability` columns are noisy (A<0 in 12 rows, OEE down
to -64), so we always derive KPIs from the JSON component fields and clip to valid
ranges. This is the trusted baseline table for both challenges.

All JSON time fields are milliseconds.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from . import loaders

A_KEYS = ["A", "WorkTotal", "PlannedStop", "UnPlannedStop", "StopTotal"]
P_KEYS = ["P", "WorkingTime", "PlannedTime", "StopTotal"]
Q_KEYS = ["Q", "ProductSum", "ScrapeSum"]


def _jget(series: pd.Series, key: str) -> pd.Series:
    out = []
    for v in series:
        try:
            out.append(json.loads(v).get(key))
        except Exception:
            out.append(None)
    return pd.to_numeric(pd.Series(out, index=series.index), errors="coerce")


def recompute(work_total, planned_stop, unplanned_stop,
              working_time, planned_time, product_sum, scrape_sum):
    """Vectorizable scalar recompute used by both the baseline build and What-If."""
    wt = np.asarray(work_total, dtype=float)
    ps = np.asarray(planned_stop, dtype=float)
    us = np.asarray(unplanned_stop, dtype=float)
    wkt = np.asarray(working_time, dtype=float)
    pt = np.asarray(planned_time, dtype=float)
    prod = np.asarray(product_sum, dtype=float)
    scrap = np.asarray(scrape_sum, dtype=float)

    scheduled = wt - ps
    run = scheduled - us
    # division-safe: np.where would evaluate the divide on zero denominators (scalars raise)
    A = np.divide(run, scheduled, out=np.zeros(np.broadcast(run, scheduled).shape),
                  where=scheduled > 0)
    # trexCloud rule: no production -> P = 0 regardless of timing (see WHAT_IF doc)
    P = np.divide(wkt, pt, out=np.zeros(np.broadcast(wkt, pt).shape),
                  where=(pt > 0) & (prod > 0))
    Q = np.divide(prod - scrap, prod, out=np.ones(np.broadcast(prod, scrap).shape),
                  where=prod > 0)
    A = np.clip(A, 0.0, 1.0)
    P = np.clip(P, 0.0, 1.0)
    Q = np.clip(Q, 0.0, 1.0)
    return A * P * Q, A, P, Q


def baseline(dir=None, level: int | None = 1) -> pd.DataFrame:
    """Per machine/day (level=1) or plant (level=0) recomputed KPI baseline."""
    oee = loaders.load("trex_mes_oee_summary", dir=dir)
    unit = loaders.load("trex_mes_unit", dir=dir)[["uid", "name"]]
    for k in A_KEYS:
        oee[k] = _jget(oee["availability"], k)
    for k in P_KEYS:
        oee[k if k != "StopTotal" else "StopTotal_P"] = _jget(oee["performance"], k)
    for k in Q_KEYS:
        oee[k] = _jget(oee["quality"], k)

    oee["OEE"], oee["A"], oee["P"], oee["Q"] = recompute(
        oee.WorkTotal, oee.PlannedStop, oee.UnPlannedStop,
        oee.WorkingTime, oee.PlannedTime, oee.ProductSum, oee.ScrapeSum,
    )
    oee = oee.merge(unit, left_on="unit_uid", right_on="uid", how="left")
    oee["date"] = oee["trans_date"].dt.date
    if level is not None:
        oee = oee[oee["level"] == level]
    keep = ["name", "unit_uid", "date", "trans_date", "level", "OEE", "A", "P", "Q",
            "WorkTotal", "PlannedStop", "UnPlannedStop", "WorkingTime", "PlannedTime",
            "ProductSum", "ScrapeSum",
            "oee", "availability", "performance", "quality"]
    out = oee[[c for c in keep if c in oee.columns]].copy()
    out = out.rename(columns={"name": "machine", "oee": "oee_stored"})
    return out.sort_values(["machine", "trans_date"]).reset_index(drop=True)
