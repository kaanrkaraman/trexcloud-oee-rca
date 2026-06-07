"""Unsupervised AD validation against weak labels. Labels NEVER enter fit/train.

Offline windows are removed from BOTH scores and labels before any metric (no telemetry
exists there; ~14,900h of offline would otherwise swamp precision).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .baselines import _intervals_mask
from .features import to_ns as _to_ns


def _drop_offline(scores: pd.DataFrame, offline: pd.DataFrame) -> pd.DataFrame:
    if offline is None or not len(offline):
        return scores
    keep = []
    for m, g in scores.groupby("machine"):
        mask = _intervals_mask(g["ts"], offline, m)
        keep.append(g[~mask])
    return pd.concat(keep, ignore_index=True) if keep else scores


def lead_time_to_alarm(scores: pd.DataFrame, labels: pd.DataFrame, *,
                       thresh: float, horizon="6h", score_col="score") -> pd.DataFrame:
    """For each labeled event, minutes between the first prior threshold crossing
    (within `horizon`) and the event. NaN = missed (no early warning)."""
    H = pd.Timedelta(horizon).value
    rows = []
    for m, ev in labels.groupby("machine"):
        s = scores[(scores.machine == m) & (scores[score_col] >= thresh)].sort_values("ts")
        st = _to_ns(s["ts"])
        for e in ev.itertuples():
            t = pd.Timestamp(e.started_on).value
            window = st[(st <= t) & (st >= t - H)]
            lead = (t - window.min()) / 6e10 if len(window) else np.nan
            rows.append({"machine": m, "event": getattr(e, "label_text", None),
                         "started_on": e.started_on, "lead_time_min": lead})
    return pd.DataFrame(rows)


def event_precision_recall(scores: pd.DataFrame, labels: pd.DataFrame, *,
                           thresholds=None, match_window="30m", score_col="score"):
    """PR over thresholds. A flagged bucket is TP if a labeled event falls within
    match_window after it; recall = fraction of labeled events with a flag before them."""
    if thresholds is None:
        thresholds = np.linspace(50, 99, 10)
    W = pd.Timedelta(match_window).value
    out = []
    for th in thresholds:
        tp = fp = 0
        matched_events = 0
        ev_total = 0
        for m, ev in labels.groupby("machine"):
            s = scores[(scores.machine == m) & (scores[score_col] >= th)]
            st = _to_ns(s["ts"])
            et = _to_ns(ev["started_on"])
            ev_total += len(et)
            if len(st):
                for f in st:
                    hit = ((et >= f) & (et <= f + W)).any()
                    tp += int(hit); fp += int(not hit)
                for t in et:
                    if ((st <= t) & (st >= t - W)).any():
                        matched_events += 1
        prec = tp / (tp + fp) if (tp + fp) else np.nan
        rec = matched_events / ev_total if ev_total else np.nan
        out.append({"thresh": round(float(th), 1), "precision": prec, "recall": rec,
                    "flags": tp + fp})
    return pd.DataFrame(out)


def summarize(scores: pd.DataFrame, labels: pd.DataFrame, offline: pd.DataFrame, *,
              thresh: float = 90.0, score_col="score") -> pd.DataFrame:
    """Per-machine: n_events, median lead-time, precision@thresh. Offline-excluded."""
    sc = _drop_offline(scores, offline)
    lt = lead_time_to_alarm(sc, labels, thresh=thresh, score_col=score_col)
    rows = []
    for m in sorted(labels.machine.dropna().unique()):
        lm = lt[lt.machine == m]
        rows.append({
            "machine": m, "n_events": int(len(lm)),
            "median_lead_min": round(float(lm.lead_time_min.median()), 1)
            if lm.lead_time_min.notna().any() else np.nan,
            "pct_with_warning": round(float(lm.lead_time_min.notna().mean() * 100), 1)
            if len(lm) else np.nan,
        })
    return pd.DataFrame(rows)
