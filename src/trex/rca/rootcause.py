"""Root cause card: orchestrate timeline -> cascade -> correlate -> ranked hypotheses,
plus the bridge that turns a card into a What-If recoverable-downtime hint.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import pandas as pd
from .. import loaders
from . import rules
from .events import build_event_timeline, build_event_stream
from .cascade import group_alarm_arrays, AlarmCascade
from .correlate import correlate_alarms_to_stops, classify_pattern


@dataclass
class Hypothesis:
    cause: str
    likelihood: float
    rationale: str
    recommended_action: str
    category: str


@dataclass
class RootCauseCard:
    machine: str
    window: tuple
    trigger: str
    pattern: str
    evidence: list = field(default_factory=list)
    cascade: dict | None = None
    hypotheses: list = field(default_factory=list)
    recommended_action: str = ""
    linked_downtime_hours: float = 0.0
    is_connectivity: bool = False

    def to_dict(self):
        d = asdict(self)
        d["window"] = [str(self.window[0]), str(self.window[1])]
        return d


@dataclass
class WhatIfHint:
    machine: str
    category: str
    recoverable_ms: float
    target_scenario: str
    note: str


def _rank_hypotheses(primary_category, pattern, evidence) -> list[Hypothesis]:
    out = []
    for cat in dict.fromkeys([primary_category, "UNPLANNED_RUNSTOP"]):
        for tmpl in rules.HYPOTHESIS_RULES.get(cat, []):
            cause, like, rat, act = tmpl
            out.append(Hypothesis(cause, like, rat, act, cat))
    # boost if telemetry drift corroborates (DRIFT_ALARM_STOP)
    if pattern == "DRIFT_ALARM_STOP":
        for h in out:
            h.likelihood = min(1.0, h.likelihood + 0.1)
    out.sort(key=lambda h: h.likelihood, reverse=True)
    return out


def build_root_cause_card(machine, start, end, *, dir=None, ad_df=None,
                          stream=None) -> RootCauseCard:
    tl = build_event_timeline(machine, start, end, dir=dir, ad_df=ad_df, stream=stream,
                              with_telemetry=False)
    ev = tl.events
    evidence = []

    cascades = group_alarm_arrays(machine, dir=dir)
    win_cascades = [c for c in cascades if tl.window[0] <= c.timestamp <= tl.window[1]]
    casc = win_cascades[0] if win_cascades else None

    alarms = ev[ev.source == "alert"]
    stops = ev[ev.source == "stoppage"]
    offline = ev[ev.source == "offline"]
    ad = ev[ev.source == "ad_window"]
    is_conn = bool(len(offline)) and not len(alarms)

    has_alarm = len(alarms) > 0
    has_drift = len(ad) > 0
    lag = None
    if has_alarm:
        corr = correlate_alarms_to_stops(machine, dir=dir)
        corr = corr[corr.matched]
        if len(corr):
            lag = float(corr.lag_seconds.min())

    pattern = classify_pattern(has_alarm=has_alarm, lag_seconds=lag,
                               has_ad_drift=has_drift, is_connectivity=is_conn)

    if casc:
        evidence.append(f"Alarm cascade ({len(casc.alarms)}): "
                        f"{' -> '.join(casc.alarms)} | root={casc.root_alarm}")
        primary_cat = casc.root_category
        trigger = f"Alarm cascade root: {casc.root_alarm}"
    elif has_alarm:
        primary_cat = alarms.category.iloc[0]
        evidence.append(f"Alarm: {alarms.label.iloc[0]}")
        trigger = f"Alarm: {alarms.label.iloc[0]}"
    elif is_conn:
        primary_cat = "CONNECTIVITY"
        evidence.append("Collector offline window (no machine telemetry present)")
        trigger = "System Offline"
    elif len(ad):
        primary_cat = "ANOMALY"
        roles = ad.meta.iloc[0].get("top_roles") if len(ad) else None
        evidence.append(f"AD telemetry anomaly; deviating: {roles}")
        trigger = "Telemetry anomaly (AD)"
    else:
        primary_cat = "UNPLANNED_RUNSTOP"
        trigger = "Unplanned stop"

    if lag is not None:
        evidence.append(f"Nearest alarm->stop lag: {lag:.0f}s")
    if has_drift and casc:
        evidence.append("Telemetry drift preceded the alarm (predictive signal)")

    linked_hours = float(loaders.ms_to_hours(
        stops[stops.category.isin(["UNPLANNED_RUNSTOP"])].duration_ms).sum())

    hyps = _rank_hypotheses(primary_cat, pattern, evidence)
    rec = hyps[0].recommended_action if hyps else "Investigate top recurring stop windows"

    return RootCauseCard(
        machine=machine, window=tl.window, trigger=trigger, pattern=pattern,
        evidence=evidence, cascade=(asdict(casc) | {"timestamp": str(casc.timestamp)}
                                    if casc else None),
        hypotheses=[asdict(h) for h in hyps], recommended_action=rec,
        linked_downtime_hours=round(linked_hours, 2), is_connectivity=is_conn)


def to_whatif_bridge(card: RootCauseCard, *, recovery_fraction=None) -> WhatIfHint:
    cat = (card.cascade["root_category"] if card.cascade
           else card.hypotheses[0]["category"] if card.hypotheses
           else "UNPLANNED_RUNSTOP")
    if card.is_connectivity:
        return WhatIfHint(card.machine, "CONNECTIVITY", 0.0, "none",
                          "Connectivity fault — fix collector/network; does NOT recover machine OEE")
    frac = recovery_fraction if recovery_fraction is not None \
        else rules.RECOVERY_FACTOR.get(cat, 0.5)
    recoverable = card.linked_downtime_hours * 3.6e6 * frac
    return WhatIfHint(card.machine, cat, recoverable, "W1",
                      f"Fixing {cat} recovers ~{frac*100:.0f}% of {card.linked_downtime_hours:.1f}h linked downtime")
