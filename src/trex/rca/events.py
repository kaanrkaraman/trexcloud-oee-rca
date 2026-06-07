"""Normalized event model unifying alerts + stoppages + offline + AD windows, plus the
event-timeline builder with a bounded telemetry overlay.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd
from .. import loaders, signals
from . import rules


@dataclass(frozen=True)
class Event:
    machine: str
    unit_uid: str | None
    source: str            # alert | stoppage | offline | ad_window
    category: str
    label: str
    start: pd.Timestamp
    end: pd.Timestamp | None
    duration_ms: float | None
    is_planned: bool | None
    excludes_oee: bool
    severity: float
    meta: dict = field(default_factory=dict)


_EVENT_COLS = ["machine", "unit_uid", "source", "category", "label", "start", "end",
               "duration_ms", "is_planned", "excludes_oee", "severity", "meta"]


def _reason_lookup(dir=None):
    rd = loaders.load("trex_mes_reading_def", dir=dir)[["uid", "display_text"]]
    return rd.drop_duplicates("uid").rename(columns={"uid": "reading_def_uid"})


def _machine_instance(dir=None) -> pd.DataFrame:
    rd = loaders.load("trex_mes_reading_def", dir=dir)[["unit_uid", "instance_id"]]
    mm = loaders.machine_master(dir=dir)[["unit_uid", "name"]]
    j = rd.dropna(subset=["instance_id"]).merge(mm, on="unit_uid", how="inner")
    return (j.groupby("name").agg(instance_id=("instance_id", lambda s: s.mode().iloc[0]),
                                  unit_uid=("unit_uid", "first")).reset_index())


def load_alert_events(dir=None) -> pd.DataFrame:
    mm = loaders.machine_master(dir=dir)[["unit_uid", "name"]]
    al = loaders.load("trex_mes_alert", dir=dir).merge(mm, on="unit_uid", how="left")
    cat = al.value.astype("string").map(rules.classify_alarm)
    return pd.DataFrame({
        "machine": al.name, "unit_uid": al.unit_uid, "source": "alert", "category": cat,
        "label": al.value.astype("string").str.strip(), "start": al.started_on,
        "end": al.ended_on, "duration_ms": al.duration_milliseconds,
        "is_planned": False, "excludes_oee": False, "severity": 0.9,
        "meta": [{"index": i, "is_array": bool(a) if pd.notna(a) else False,
                  "reading_def_uid": r}
                 for i, a, r in zip(al["index"], al.is_array, al.reading_def_uid)],
    }).dropna(subset=["start"])


def load_stoppage_events(dir=None, clip_hours: float = 24.0) -> pd.DataFrame:
    mm = loaders.machine_master(dir=dir)[["unit_uid", "name"]]
    ss = loaders.load("trex_mes_stoppage_slice", dir=dir) \
        .merge(_reason_lookup(dir=dir), on="reading_def_uid", how="left") \
        .merge(mm, on="unit_uid", how="left")
    planned = ss.is_planned.map({True: True, False: False})
    cat = [rules.classify_stop(t, p) for t, p in zip(ss.display_text, planned)]
    dur = pd.to_numeric(ss.duration_milliseconds, errors="coerce")
    cap = clip_hours * 3.6e6
    clipped = dur > cap
    excl = ss.exclude_from_oee.eq(True).fillna(False)
    df = pd.DataFrame({
        "machine": ss.name, "unit_uid": ss.unit_uid, "source": "stoppage",
        "category": cat, "label": ss.display_text, "start": ss.started_on,
        "end": ss.ended_on, "duration_ms": dur.clip(upper=cap),
        "is_planned": planned, "excludes_oee": excl,
        "severity": [0.7 if c == "UNPLANNED_RUNSTOP" else 0.4 if c == "CONNECTIVITY" else 0.2
                     for c in cat],
        "meta": [{"clipped": bool(c), "reading_def_uid": r}
                 for c, r in zip(clipped, ss.reading_def_uid)],
    })
    df.loc[df.category == "CONNECTIVITY", "excludes_oee"] = True
    return df.dropna(subset=["start"])


def load_offline_events(dir=None) -> pd.DataFrame:
    """Instance-level offline expanded to per-machine events (systemic signal)."""
    mi = _machine_instance(dir=dir)
    st = loaders.load("trex_mes_status", dir=dir)
    st = st[st.is_online.eq(False).fillna(False)]
    rows = []
    for r in st.itertuples():
        members = mi[mi.instance_id == r.instance_id]
        for m in members.itertuples():
            rows.append({"machine": m.name, "unit_uid": m.unit_uid, "source": "offline",
                         "category": "CONNECTIVITY", "label": "System Offline",
                         "start": r.started_on, "end": r.ended_on,
                         "duration_ms": r.duration_milliseconds, "is_planned": False,
                         "excludes_oee": True, "severity": 0.4,
                         "meta": {"instance_id": r.instance_id, "systemic": len(members) > 1}})
    return pd.DataFrame(rows, columns=_EVENT_COLS).dropna(subset=["start"]) if rows \
        else pd.DataFrame(columns=_EVENT_COLS)


def normalize_ad_windows(ad_df: pd.DataFrame | None) -> pd.DataFrame:
    if ad_df is None or not len(ad_df):
        return pd.DataFrame(columns=_EVENT_COLS)
    sev = ad_df["peak_score"] / 100.0 if "peak_score" in ad_df else 0.5
    return pd.DataFrame({
        "machine": ad_df["machine"], "unit_uid": None, "source": "ad_window",
        "category": "ANOMALY", "label": "telemetry anomaly",
        "start": ad_df["window_start"], "end": ad_df["window_end"],
        "duration_ms": (pd.to_datetime(ad_df["window_end"]) -
                        pd.to_datetime(ad_df["window_start"])).dt.total_seconds() * 1000,
        "is_planned": False, "excludes_oee": True, "severity": sev,
        "meta": [{"top_roles": tr} for tr in ad_df.get("top_roles", [None] * len(ad_df))],
    }).dropna(subset=["start"])


def build_event_stream(dir=None, ad_df: pd.DataFrame | None = None) -> pd.DataFrame:
    parts = [load_alert_events(dir), load_stoppage_events(dir),
             load_offline_events(dir), normalize_ad_windows(ad_df)]
    df = pd.concat([p[_EVENT_COLS] for p in parts], ignore_index=True)
    for c in ("start", "end"):
        df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    df["duration_ms"] = pd.to_numeric(df["duration_ms"], errors="coerce")
    return df.sort_values(["machine", "start"]).reset_index(drop=True)


@dataclass
class EventTimeline:
    machine: str
    window: tuple
    events: pd.DataFrame
    telemetry: pd.DataFrame
    has_telemetry: bool


DEFAULT_OVERLAY = ("run_state", "cycle_time", "axis_position", "run_time",
                   "production_count")


def _utc(x):
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def build_event_timeline(machine, start, end, *, dir=None, ad_df=None, stream=None,
                         pre_pad="15min", post_pad="5min", with_telemetry=True,
                         overlay_roles=DEFAULT_OVERLAY) -> EventTimeline:
    start, end = _utc(start), _utc(end)
    w0, w1 = start - pd.Timedelta(pre_pad), end + pd.Timedelta(post_pad)
    if stream is None:
        stream = build_event_stream(dir, ad_df)
    ev = stream[(stream.machine == machine) & (stream.start <= w1) &
                ((stream.end >= w0) | stream.end.isna() | (stream.start >= w0))].copy()

    mm = loaders.machine_master(dir=dir)
    row = mm[mm.name == machine]
    has_tel = bool(row.has_telemetry.iloc[0]) if len(row) else False
    tel = pd.DataFrame(columns=["time", "readingdef_uid", "canonical_role", "value"])
    if has_tel and with_telemetry:
        sm = signals.build_signal_map(dir=dir)
        uids = sm[(sm.machine == machine) & (sm.canonical_role.isin(overlay_roles))]
        if len(uids):
            raw = loaders.read_telemetry(dir=dir, start=w0, end=w1,
                                         readingdef_uids=list(uids.readingdef_uid))
            if len(raw):
                tel = raw.merge(sm[["readingdef_uid", "canonical_role"]],
                                on="readingdef_uid", how="left")
                tel["value"] = pd.to_numeric(tel["value"], errors="coerce")
    return EventTimeline(machine, (w0, w1), ev.reset_index(drop=True), tel, has_tel)
