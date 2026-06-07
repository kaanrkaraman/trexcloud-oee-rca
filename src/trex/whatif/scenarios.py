"""What-If scenario engine. Every scenario mutates the raw ms/count components of one
oee.baseline row and re-runs oee.recompute — identical math to the trusted baseline.

W1 eliminate top unplanned category by %   (A)
W2 reclassify UNPLANNED -> PLANNED         (A)
W3 reduce unplanned stop duration by %     (A)
W4 improve performance/cycle by %          (P)  -- inert when ProductSum==0
W5 simulate scrap rate then recover        (Q)  -- SIMULATED (Q=1 in real data)
"""
from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd
from .. import oee


@dataclass
class ScenarioSpec:
    kind: str                       # "W1".."W5"
    pct: float = 0.0                # 0..1 magnitude
    category: str | None = None     # target stop category (W1/W2/W3)
    abs_ms: float | None = None     # absolute ms to act on (e.g. from RCA WhatIfHint)
    scrap_baseline_pct: float = 0.0  # W5: assumed current scrap level before improvement


@dataclass
class ScenarioResult:
    machine: str
    date: object
    before: dict
    after: dict
    delta: dict
    recovered_runtime_ms: float
    extra_pieces: float
    spec: ScenarioSpec
    assumptions_note: str = ""


def _components(row) -> dict:
    return {k: float(row.get(k, 0) or 0) for k in
            ("WorkTotal", "PlannedStop", "UnPlannedStop", "WorkingTime",
             "PlannedTime", "ProductSum", "ScrapeSum")}


def _kpis(c) -> dict:
    oeev, a, p, q = oee.recompute(c["WorkTotal"], c["PlannedStop"], c["UnPlannedStop"],
                                  c["WorkingTime"], c["PlannedTime"],
                                  c["ProductSum"], c["ScrapeSum"])
    runtime = c["WorkTotal"] - c["PlannedStop"] - c["UnPlannedStop"]
    return {"OEE": float(oeev), "A": float(a), "P": float(p), "Q": float(q),
            "runtime_ms": max(0.0, runtime), **c}


def run_scenario(baseline_row, spec: ScenarioSpec, *, category_ms: float | None = None
                 ) -> ScenarioResult:
    """baseline_row: a Series/dict from oee.baseline(level=1). category_ms: the targeted
    category's unplanned ms for this scope (from rca.pareto) — required for W1/W3 honesty."""
    row = baseline_row.to_dict() if hasattr(baseline_row, "to_dict") else dict(baseline_row)
    c0 = _components(row)
    before = _kpis(dict(c0))
    c = dict(c0)
    note = ""

    if spec.kind in ("W1", "W3"):
        available = min(
            c0["UnPlannedStop"],
            max(0.0, category_ms) if category_ms is not None else c0["UnPlannedStop"],
        )
        target = spec.abs_ms if spec.abs_ms is not None else \
            spec.pct * available
        reduce_by = min(max(0.0, target), available)
        c["UnPlannedStop"] = max(0.0, c0["UnPlannedStop"] - reduce_by)
        note = ("Eliminate" if spec.kind == "W1" else "Shorten") + \
            f" {spec.category or 'top unplanned'} by {spec.pct*100:.0f}% "
    elif spec.kind == "W2":
        available = min(
            c0["UnPlannedStop"],
            max(0.0, category_ms) if category_ms is not None else c0["UnPlannedStop"],
        )
        move = spec.abs_ms if spec.abs_ms is not None else \
            spec.pct * available
        move = min(max(0.0, move), available)
        c["UnPlannedStop"] = c0["UnPlannedStop"] - move
        c["PlannedStop"] = c0["PlannedStop"] + move
        note = f"Reclassify {move/3.6e6:.1f}h of {spec.category or 'unplanned'} -> planned"
    elif spec.kind == "W4":
        if c0["ProductSum"] <= 0:
            note = "P lever INERT: ProductSum=0 (no production this scope)"
        else:
            c["WorkingTime"] = min(c0["WorkingTime"] * (1 + spec.pct), c0["PlannedTime"]) \
                if c0["PlannedTime"] > 0 else c0["WorkingTime"] * (1 + spec.pct)
            c["ProductSum"] = c0["ProductSum"] * (1 + spec.pct)
            note = f"Improve performance/cycle by {spec.pct*100:.0f}%"
    elif spec.kind == "W5":
        base_scrap = spec.scrap_baseline_pct * c0["ProductSum"]
        c0_sim = dict(c0); c0_sim["ScrapeSum"] = base_scrap
        before = _kpis(c0_sim)                       # 'before' = simulated current scrap
        c = dict(c0_sim); c["ScrapeSum"] = base_scrap * (1 - spec.pct)
        note = (f"SIMULATED: assume {spec.scrap_baseline_pct*100:.0f}% scrap, "
                f"reduce by {spec.pct*100:.0f}% (Q is 1.0 in real data)")
    else:
        raise ValueError(f"unknown scenario kind {spec.kind!r}")

    after = _kpis(c)
    delta = {f"d{k}": round(after[k] - before[k], 4) for k in ("OEE", "A", "P", "Q")}
    recovered = after["runtime_ms"] - before["runtime_ms"]
    cyc = (before["WorkingTime"] / before["ProductSum"]) if before["ProductSum"] > 0 else None
    extra = (recovered / cyc) if cyc else (after["ProductSum"] - before["ProductSum"])
    return ScenarioResult(row.get("machine"), row.get("date"), before, after, delta,
                          float(recovered), float(max(0.0, extra)), spec, note)


def run_scenario_range(baseline_df: pd.DataFrame, spec: ScenarioSpec, *,
                       category_ms_by_machine: dict | None = None) -> pd.DataFrame:
    """Apply a scenario across many machine-days; return a tidy summary frame."""
    rows = []
    for _, r in baseline_df.iterrows():
        cms = (category_ms_by_machine or {}).get(r.get("machine"))
        res = run_scenario(r, spec, category_ms=cms)
        rows.append({"machine": res.machine, "date": res.date,
                     "OEE_before": res.before["OEE"], "OEE_after": res.after["OEE"],
                     **res.delta, "recovered_h": res.recovered_runtime_ms / 3.6e6,
                     "extra_pieces": res.extra_pieces})
    return pd.DataFrame(rows)
