"""Supervised stop-prediction dataset — leakage-safe by construction.

Task: at a *running* bucket t, will a SIGNIFICANT unplanned stop (>= min_stop_min) start
within the next `horizon_min`?

Features at t use only data <= t:
  - telemetry rolling stats (short + long lookback) + slope
  - stop DYNAMICS: recency/frequency of ALL unplanned stops AND micro-stops (<5 min) and
    significant stops, plus recent downtime burden — degradation often shows as rising
    micro-stop frequency before a big stop.
  - hour-of-day (shift rhythm)
Label uses only the future window (t, t+H]. Chronological split happens in benchmark.py.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .. import rca
from ..ad import features as adfeat

LOOKBACK = 15
LONG_LOOKBACK = 60
HORIZON_MIN = 60
MIN_STOP_MIN = 15
MICRO_MAX_MIN = 5


def _unplanned_by_machine():
    ev = rca.events.load_stoppage_events()
    up = ev[ev.category == "UNPLANNED_RUNSTOP"].copy()
    up["min"] = (up.duration_ms / 6e4).clip(lower=0)
    out = {}
    for m, g in up.groupby("machine"):
        g = g.sort_values("start")
        out[m] = (g["start"].to_numpy(dtype="datetime64[ns]"), g["min"].to_numpy())
    return out


def stop_starts(min_stop_min=MIN_STOP_MIN) -> dict:
    """machine -> sorted significant-stop start times (the prediction label source)."""
    unp = _unplanned_by_machine()
    return {m: starts[mins >= min_stop_min] for m, (starts, mins) in unp.items()}


def _range_count(sorted_starts, lo_ts, hi_ts):
    return (np.searchsorted(sorted_starts, hi_ts, "right")
            - np.searchsorted(sorted_starts, lo_ts, "left"))


def _engineer_machine(f, base_cols, all_starts, all_mins, sig_starts, *,
                      lookback, long_lookback, horizon_min):
    f = f.sort_values("ts").reset_index(drop=True)
    ts = f["ts"].to_numpy(dtype="datetime64[ns]")
    out = {"machine": f["machine"].to_numpy(), "ts": f["ts"].to_numpy()}

    for c in base_cols:
        s = pd.to_numeric(f[c], errors="coerce")
        out[c] = s.to_numpy()
        out[f"{c}__roll_mean"] = s.rolling(lookback, min_periods=3).mean().to_numpy()
        out[f"{c}__roll_std"] = s.rolling(lookback, min_periods=3).std().to_numpy()
        out[f"{c}__slope"] = (s - s.shift(lookback)).to_numpy()
        out[f"{c}__long_mean"] = s.rolling(long_lookback, min_periods=5).mean().to_numpy()
    if "n_samples" in f:
        out["n_samples"] = f["n_samples"].to_numpy()
    out["is_idle_now"] = (f["is_idle"].fillna(False).astype(int).to_numpy()
                          if "is_idle" in f else np.zeros(len(ts)))

    one_h, four_h = np.timedelta64(60, "m"), np.timedelta64(240, "m")
    micro = all_mins < MICRO_MAX_MIN if all_mins is not None else None

    def recency_block(starts, prefix, mins=None, micro_mask=None):
        if starts is None or len(starts) == 0:
            out[f"{prefix}_min_since"] = np.full(len(ts), 9999.0)
            out[f"{prefix}_cnt_1h"] = np.zeros(len(ts))
            out[f"{prefix}_cnt_4h"] = np.zeros(len(ts))
            return
        idx = np.searchsorted(starts, ts, "right")
        last = np.where(idx > 0, starts[np.clip(idx - 1, 0, len(starts) - 1)], np.datetime64("NaT"))
        out[f"{prefix}_min_since"] = np.where(
            idx > 0, (ts - last) / np.timedelta64(1, "m"), 9999.0)
        out[f"{prefix}_cnt_1h"] = (idx - np.searchsorted(starts, ts - one_h, "left")).astype(float)
        out[f"{prefix}_cnt_4h"] = (idx - np.searchsorted(starts, ts - four_h, "left")).astype(float)

    recency_block(all_starts, "anystop")
    recency_block(sig_starts, "sigstop")
    # micro-stop frequency (rising micro-stops = instability precursor)
    if all_starts is not None and len(all_starts):
        microstarts = all_starts[micro]
        recency_block(microstarts, "micro")
        # recent downtime burden (sum of stop minutes started in last 4h, capped per stop)
        cum = np.concatenate([[0], np.cumsum(np.clip(all_mins, 0, 240))])
        hi = np.searchsorted(all_starts, ts, "right")
        lo = np.searchsorted(all_starts, ts - four_h, "left")
        out["downtime_min_4h"] = cum[hi] - cum[lo]
    else:
        for p in ("micro_min_since", "micro_cnt_1h", "micro_cnt_4h"):
            out[p] = np.zeros(len(ts))
        out["downtime_min_4h"] = np.zeros(len(ts))

    out["hour"] = f["ts"].dt.hour.to_numpy().astype(float)

    H = np.timedelta64(horizon_min, "m")
    if sig_starts is not None and len(sig_starts):
        out["y"] = (np.searchsorted(sig_starts, ts + H, "right")
                    > np.searchsorted(sig_starts, ts, "right")).astype(int)
    else:
        out["y"] = np.zeros(len(ts), dtype=int)

    df = pd.DataFrame(out)
    return df[df["ts"] <= (f["ts"].max() - pd.Timedelta(minutes=horizon_min))]


def _active_sig_intervals(min_stop_min):
    """machine -> list of (start_ns, end_ns) for significant unplanned stops (to mask
    'predicting during the breakdown' — that would be tautological, not predictive)."""
    ev = rca.events.load_stoppage_events()
    up = ev[ev.category == "UNPLANNED_RUNSTOP"].copy()
    up["min"] = (up.duration_ms / 6e4).clip(lower=0)
    up = up[up["min"] >= min_stop_min]
    out = {}
    for m, g in up.groupby("machine"):
        s = g["start"].to_numpy("datetime64[ns]")
        e = s + (g["min"].to_numpy() * 60 * 1e9).astype("timedelta64[ns]")
        out[m] = (s, e)
    return out


def build_supervised(*, features_path="analysis/artifacts/ad_features.parquet",
                     machines=None, lookback=LOOKBACK, long_lookback=LONG_LOOKBACK,
                     horizon_min=HORIZON_MIN, min_stop_min=MIN_STOP_MIN,
                     running_only=False, exclude_active_stop=True) -> tuple[pd.DataFrame, list]:
    """running_only=False keeps idle buckets (informative pre-stop states) + is_idle feature.
    exclude_active_stop drops buckets *inside* an ongoing significant stop (avoids the
    tautology of 'predicting' a stop while already stopped)."""
    feats = pd.read_parquet(features_path)
    feats["ts"] = pd.to_datetime(feats["ts"], utc=True)
    base_cols = adfeat.feature_columns(feats)
    unp = _unplanned_by_machine()
    sig = stop_starts(min_stop_min)
    active = _active_sig_intervals(min_stop_min) if exclude_active_stop else {}
    frames = []
    for m, g in feats.groupby("machine"):
        if machines and m not in machines:
            continue
        g = g[~g["is_offline"].fillna(False)]
        if running_only:
            g = g[~g["is_idle"].fillna(False)]
        if exclude_active_stop and m in active:
            s, e = active[m]
            t = g["ts"].to_numpy("datetime64[ns]")
            # bucket is inside a stop if the most recent stop-start <= t has end >= t
            idx = np.searchsorted(s, t, "right") - 1
            inside = (idx >= 0) & (e[np.clip(idx, 0, len(e) - 1)] >= t)
            g = g[~inside]
        if len(g) < lookback + 50:
            continue
        all_starts, all_mins = unp.get(m, (None, None))
        frames.append(_engineer_machine(g, base_cols, all_starts, all_mins, sig.get(m),
                                        lookback=lookback, long_lookback=long_lookback,
                                        horizon_min=horizon_min))
    data = pd.concat(frames, ignore_index=True).sort_values(["machine", "ts"])
    feat_cols = [c for c in data.columns if c not in ("machine", "ts", "y")]
    feat_cols = [c for c in feat_cols if data[c].notna().any()]
    return data.reset_index(drop=True), feat_cols
