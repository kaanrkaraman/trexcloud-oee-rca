"""Economic attribution for the deployed Fanuc stop predictor.

The model metrics and stop catches are measured on the held-out future. Currency,
intervention effectiveness, and annualization are assumptions and are kept separate
from the measured operating-point statistics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import numpy as np
import pandas as pd

from .. import oee
from ..predict import fanuc
from .financials import ASSUMPTION_LABEL, FinancialAssumptions
from .scenarios import ScenarioSpec, run_scenario

COMPONENTS = ("WorkTotal", "PlannedStop", "UnPlannedStop", "WorkingTime",
              "PlannedTime", "ProductSum", "ScrapeSum")


@dataclass
class PMValueAssumptions:
    intervention_effectiveness: float = 0.35
    horizon_min: int = 60
    annual_days: int = 365


def _utc(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def scored_windows(scored: pd.DataFrame, horizon_min: int = 60) -> pd.DataFrame:
    """Actual per-machine scored test intervals, extended by the label horizon."""
    d = scored.copy()
    d["ts"] = pd.to_datetime(d["ts"], utc=True)
    rows = []
    for machine, group in d.groupby("machine"):
        start = group["ts"].min()
        score_end = group["ts"].max()
        end = score_end + pd.Timedelta(minutes=horizon_min)
        rows.append({
            "machine": machine,
            "start": start,
            "score_end": score_end,
            "end": end,
            "observed_days": (end - start).total_seconds() / 86400.0,
        })
    return pd.DataFrame(rows).sort_values("machine").reset_index(drop=True)


def scope_significant_stops(stops: pd.DataFrame, windows: pd.DataFrame,
                            machines=fanuc.FANUC) -> pd.DataFrame:
    """Fanuc significant stops inside each machine's scored test interval.

    Exact duplicate event rows are removed and durations are clipped to the RCA
    contract's 24-hour maximum before any value is attributed.
    """
    cols = ["machine", "start", "duration_ms"]
    optional = [c for c in ("end", "label") if c in stops]
    d = stops[[*cols, *optional]].copy()
    d["start"] = pd.to_datetime(d["start"], utc=True)
    d["duration_ms"] = pd.to_numeric(d["duration_ms"], errors="coerce").clip(0, 24 * 3.6e6)
    d = d[d["machine"].isin(machines)].dropna(subset=["machine", "start", "duration_ms"])
    d = d.sort_values("duration_ms", ascending=False).drop_duplicates(["machine", "start"])
    w = windows[["machine", "start", "end"]].rename(
        columns={"start": "window_start", "end": "window_end"})
    d = d.merge(w, on="machine", how="inner")
    d = d[(d["start"] > d["window_start"]) & (d["start"] <= d["window_end"])]
    return d.sort_values(["machine", "start"]).reset_index(drop=True)


def match_stops(scored: pd.DataFrame, stops: pd.DataFrame, threshold: float,
                horizon_min: int = 60) -> pd.DataFrame:
    """Match each stop once to risk buckets strictly inside (stop-H, stop)."""
    risk = scored[["machine", "ts", "risk"]].copy()
    risk["ts"] = pd.to_datetime(risk["ts"], utc=True)
    risk["risk"] = pd.to_numeric(risk["risk"], errors="coerce")
    out = []
    horizon = pd.Timedelta(minutes=horizon_min)
    for machine, group in stops.groupby("machine"):
        rg = risk[risk["machine"] == machine].sort_values("ts")
        ts = rg["ts"].to_numpy(dtype="datetime64[ns]")
        values = rg["risk"].to_numpy(float)
        for row in group.itertuples(index=False):
            stop_ts = _utc(row.start)
            lo = np.searchsorted(ts, np.datetime64((stop_ts - horizon).to_datetime64()),
                                 side="right")
            hi = np.searchsorted(ts, np.datetime64(stop_ts.to_datetime64()), side="left")
            prior = values[lo:hi]
            caught = bool(len(prior) and np.nanmax(prior) >= threshold)
            max_risk = float(np.nanmax(prior)) if len(prior) else float("nan")
            out.append({
                "machine": machine,
                "start": stop_ts,
                "duration_ms": float(row.duration_ms),
                "caught": caught,
                "max_prior_risk": max_risk,
            })
    return pd.DataFrame(out, columns=[
        "machine", "start", "duration_ms", "caught", "max_prior_risk"])


def aggregate_oee_window(baseline: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    """Prorate daily OEE components to each machine's actual test interval."""
    rows = []
    for w in windows.itertuples(index=False):
        group = baseline[baseline["machine"] == w.machine].copy()
        if "trans_date" in group:
            row_start = pd.to_datetime(group["trans_date"], utc=True, errors="coerce")
        else:
            row_start = pd.to_datetime(group["date"], utc=True, errors="coerce")
        fallback = pd.to_datetime(group["date"], utc=True, errors="coerce")
        row_start = row_start.fillna(fallback)
        row_end = row_start + pd.Timedelta(days=1)
        overlap_start = row_start.where(row_start > w.start, w.start)
        overlap_end = row_end.where(row_end < w.end, w.end)
        fraction = ((overlap_end - overlap_start).dt.total_seconds() / 86400.0).clip(0, 1)
        comp = {c: float((pd.to_numeric(group[c], errors="coerce").fillna(0) *
                          fraction).sum()) for c in COMPONENTS}
        ov, a, p, q = oee.recompute(*(comp[c] for c in COMPONENTS))
        rows.append({
            "machine": w.machine,
            "scope_start": w.start,
            "scope_end": w.end,
            **comp,
            "OEE": float(ov), "A": float(a), "P": float(p), "Q": float(q),
        })
    return pd.DataFrame(rows)


def attributable_oee(components, prevented_h: float) -> dict:
    """Apply bounded prevented downtime to one aggregate OEE component row."""
    row = components.to_dict() if hasattr(components, "to_dict") else dict(components)
    cap_h = max(0.0, float(row.get("UnPlannedStop", 0.0))) / 3.6e6
    applied_h = min(max(0.0, float(prevented_h)), cap_h)
    result = run_scenario(
        row,
        ScenarioSpec("W1", pct=0.0, category="MODEL_CAUGHT_STOP",
                     abs_ms=applied_h * 3.6e6),
        category_ms=applied_h * 3.6e6,
    )
    return {
        "applied_prevented_h": applied_h,
        "before": {k: result.before[k] for k in ("OEE", "A", "P", "Q")},
        "after": {k: result.after[k] for k in ("OEE", "A", "P", "Q")},
        "delta": dict(result.delta),
        "components_before": {k: float(row.get(k, 0.0) or 0.0) for k in COMPONENTS},
    }


def financial_projection(prevented_h: float, n_episodes: int, observed_days: float,
                         assumptions: FinancialAssumptions, annual_days: int = 365) -> dict:
    """Value recovered time once, and charge every alert episode including false alarms."""
    observed_days = max(float(observed_days), 1e-9)
    gross = float(prevented_h) * assumptions.downtime_cost_per_hour
    intervention = int(n_episodes) * assumptions.intervention_cost
    net = gross - intervention
    roi = net / intervention if intervention > 0 else None
    factor = annual_days / observed_days
    return {
        "observed": {
            "gross_eur": round(gross, 2),
            "intervention_eur": round(intervention, 2),
            "net_eur": round(net, 2),
            "roi": round(roi, 4) if roi is not None else None,
        },
        "annualized": {
            "factor": round(factor, 6),
            "prevented_h": round(float(prevented_h) * factor, 3),
            "gross_eur": round(gross * factor, 2),
            "intervention_eur": round(intervention * factor, 2),
            "net_eur": round(net * factor, 2),
            "roi": round(roi, 4) if roi is not None else None,
        },
    }


def _sum_components(rows: list[dict]) -> dict:
    return {c: sum(r["oee"]["components_before"][c] for r in rows) for c in COMPONENTS}


def evaluate_operating_point(scored: pd.DataFrame, stops: pd.DataFrame,
                             baseline: pd.DataFrame, threshold: float,
                             pm_assumptions: PMValueAssumptions | None = None,
                             financial_assumptions: FinancialAssumptions | None = None,
                             episodes_override: pd.DataFrame | None = None) -> dict:
    """Evaluate recall, alert cost, attributable OEE, and EUR at one threshold."""
    pm_assumptions = pm_assumptions or PMValueAssumptions()
    financial_assumptions = financial_assumptions or FinancialAssumptions(
        currency="EUR", value_recovered_time_as="downtime_cost")
    windows = scored_windows(scored, pm_assumptions.horizon_min)
    scoped = scope_significant_stops(stops, windows)
    matched = match_stops(scored, scoped, threshold, pm_assumptions.horizon_min)
    episodes = (episodes_override.copy() if episodes_override is not None
                else fanuc.risk_episodes(scored, threshold))
    if len(episodes):
        episodes["hit"] = episodes["hit"].map(
            lambda value: value if isinstance(value, (bool, np.bool_))
            else str(value).strip().lower() == "true")
    base = aggregate_oee_window(baseline, windows)

    per_machine = []
    for w in windows.itertuples(index=False):
        sm = matched[matched["machine"] == w.machine]
        ep = episodes[episodes["machine"] == w.machine] if len(episodes) else episodes
        caught = sm[sm["caught"]]
        caught_h = float(caught["duration_ms"].sum() / 3.6e6)
        requested_h = caught_h * pm_assumptions.intervention_effectiveness
        brow = base[base["machine"] == w.machine].iloc[0]
        oee_result = attributable_oee(brow, requested_h)
        total = int(len(sm))
        n_ep = int(len(ep))
        ep_hits = int(ep["hit"].sum()) if n_ep else 0
        fin = financial_projection(
            oee_result["applied_prevented_h"], n_ep, w.observed_days,
            financial_assumptions, pm_assumptions.annual_days)
        per_machine.append({
            "machine": w.machine,
            "test_start": str(w.start),
            "test_end": str(w.end),
            "observed_days": round(float(w.observed_days), 4),
            "significant_stops": total,
            "caught_stops": int(caught.shape[0]),
            "recall": round(float(caught.shape[0] / total), 4) if total else None,
            "total_downtime_h": round(float(sm["duration_ms"].sum() / 3.6e6), 3),
            "caught_downtime_h": round(caught_h, 3),
            "prevented_h": round(oee_result["applied_prevented_h"], 3),
            "episodes": n_ep,
            "episode_hits": ep_hits,
            "false_alarm_episodes": n_ep - ep_hits,
            "episode_precision": round(ep_hits / n_ep, 4) if n_ep else None,
            "oee": oee_result,
            "financial": fin,
        })

    total_stops = sum(r["significant_stops"] for r in per_machine)
    caught_stops = sum(r["caught_stops"] for r in per_machine)
    n_episodes = sum(r["episodes"] for r in per_machine)
    episode_hits = sum(r["episode_hits"] for r in per_machine)
    caught_h = sum(r["caught_downtime_h"] for r in per_machine)
    prevented_h = sum(r["prevented_h"] for r in per_machine)
    portfolio_components = _sum_components(per_machine)
    portfolio_oee = attributable_oee(portfolio_components, prevented_h)
    observed_start = windows["start"].min()
    observed_end = windows["end"].max()
    observed_days = (observed_end - observed_start).total_seconds() / 86400.0
    portfolio_fin = financial_projection(
        portfolio_oee["applied_prevented_h"], n_episodes, observed_days,
        financial_assumptions, pm_assumptions.annual_days)

    return {
        "threshold": round(float(threshold), 6),
        "test_start": str(observed_start),
        "test_end": str(observed_end),
        "observed_days": round(observed_days, 4),
        "significant_stops": total_stops,
        "caught_stops": caught_stops,
        "recall": round(caught_stops / total_stops, 4) if total_stops else None,
        "caught_downtime_h": round(caught_h, 3),
        "prevented_h": round(portfolio_oee["applied_prevented_h"], 3),
        "episodes": n_episodes,
        "episode_hits": episode_hits,
        "false_alarm_episodes": n_episodes - episode_hits,
        "episode_precision": round(episode_hits / n_episodes, 4) if n_episodes else None,
        "oee": portfolio_oee,
        "financial": portfolio_fin,
        "per_machine": per_machine,
    }


def threshold_sensitivity(scored: pd.DataFrame, stops: pd.DataFrame,
                          baseline: pd.DataFrame, deployed_threshold: float,
                          pm_assumptions: PMValueAssumptions | None = None,
                          financial_assumptions: FinancialAssumptions | None = None,
                          thresholds=None,
                          deployed_episodes: pd.DataFrame | None = None) -> dict:
    """Evaluate 51 evenly spaced thresholds plus the deployed operating point."""
    values = np.linspace(0.0, 1.0, 51) if thresholds is None else np.asarray(thresholds, float)
    values = np.unique(np.append(values, float(deployed_threshold)))
    rows = []
    for threshold in values:
        result = evaluate_operating_point(
            scored, stops, baseline, float(threshold),
            pm_assumptions, financial_assumptions,
            episodes_override=(deployed_episodes if np.isclose(
                threshold, deployed_threshold, atol=1e-12) else None))
        rows.append({
            "threshold": result["threshold"],
            "recall": result["recall"],
            "caught_stops": result["caught_stops"],
            "caught_downtime_h": result["caught_downtime_h"],
            "prevented_h": result["prevented_h"],
            "episodes": result["episodes"],
            "episode_precision": result["episode_precision"],
            "delta_oee": result["oee"]["delta"]["dOEE"],
            "annualized_net_eur": result["financial"]["annualized"]["net_eur"],
            "annualized_gross_eur": result["financial"]["annualized"]["gross_eur"],
            "annualized_intervention_eur": result["financial"]["annualized"]["intervention_eur"],
        })
    optimum = max(rows, key=lambda r: (r["annualized_net_eur"], r["threshold"]))
    return {
        "selection_note": (
            "Retrospective held-out sensitivity only; the deployed headline remains "
            f"threshold={deployed_threshold:.4f}."),
        "economic_optimum": optimum,
        "rows": rows,
    }


def assumptions_dict(pm_assumptions: PMValueAssumptions,
                     financial_assumptions: FinancialAssumptions) -> dict:
    return {
        "label": ASSUMPTION_LABEL,
        "pm": asdict(pm_assumptions),
        "financial": asdict(financial_assumptions),
    }
