"""One-time telemetry feature extraction: irregular event telemetry -> regular grid.

CORRECTED feature set (verified): the catalog's servo_temp/power/path_load signals
have ZERO rows. The roles that actually stream numeric data are:
  cycle_time (gauge, ms)        run_time (counter)        run_state (0..3 status)
  axis_position (gauge, multi)  production_count (counter) machine_mode (0/1)

Single fan-out pass over the 19 numeric parts (never read_telemetry per machine).
Output: analysis/artifacts/ad_features.parquet, partitioned by machine, one row per
(machine, 60s bucket) with role-keyed feature columns.
"""
from __future__ import annotations
from glob import glob
from pathlib import Path
import numpy as np
import pandas as pd
from .. import loaders, signals

FEATURE_ROLES = ("cycle_time", "axis_position", "run_time", "run_state",
                 "production_count", "machine_mode")
COUNTER_ROLES = {"run_time", "production_count"}
RESAMPLE_FREQ = "60s"
ART = Path("analysis/artifacts")


def to_ns(x):
    """tz-aware/naive datetimes (any pandas resolution) -> int64 epoch nanoseconds.
    Resolution-safe: pandas 3.0 may store datetimes as us, so .astype('int64')
    alone is NOT epoch-ns. Use this for all interval/time arithmetic."""
    return pd.to_datetime(x, utc=True).to_numpy(dtype="datetime64[ns]").astype("int64")


def role_uid_map(dir=None) -> pd.DataFrame:
    """Feature-role signals only; each readingdef_uid is 1:1 with a machine (verified)."""
    sm = signals.build_signal_map(dir=dir)
    fr = sm[sm.canonical_role.isin(FEATURE_ROLES)][
        ["readingdef_uid", "machine", "vendor", "canonical_role"]
    ].drop_duplicates("readingdef_uid").reset_index(drop=True)
    return fr


def _offline_intervals(dir=None) -> pd.DataFrame:
    """instance-level offline windows from trex_mes_status (is_online == False)."""
    st = loaders.load("trex_mes_status", dir=dir)
    off = st[st.is_online.eq(False).fillna(False)]
    return off[["instance_id", "started_on", "ended_on"]].dropna(subset=["started_on"])


def _machine_instance(dir=None) -> dict:
    """machine -> instance_id, taken from reading_def (telemetry rows are instance-tagged)."""
    rd = loaders.load("trex_mes_reading_def", dir=dir)[["unit_uid", "instance_id"]]
    mm = loaders.machine_master(dir=dir)[["unit_uid", "name"]]
    j = rd.dropna(subset=["instance_id"]).merge(mm, on="unit_uid", how="inner")
    return j.groupby("name").instance_id.agg(lambda s: s.mode().iloc[0]).to_dict()


def _collect_rows(uid_map: pd.DataFrame, *, dir=None, machines=None) -> pd.DataFrame:
    """Single streaming pass: filter each chunk to feature uids, annotate machine+role."""
    u2machine = dict(zip(uid_map.readingdef_uid, uid_map.machine))
    u2role = dict(zip(uid_map.readingdef_uid, uid_map.canonical_role))
    keep_uids = set(uid_map.readingdef_uid)
    if machines is not None:
        keep_uids = set(uid_map[uid_map.machine.isin(machines)].readingdef_uid)
    base = loaders.data_dir(dir)
    paths = sorted(glob(str(base / "trex_nightwatch_data_[0-9][0-9][0-9].csv")))
    cols = ["readingdef_uid", "value", "index", "time"]
    out = []
    for p in paths:
        for ch in pd.read_csv(p, encoding=loaders.ENC, usecols=lambda c: c in cols,
                              low_memory=False, chunksize=1_000_000):
            sub = ch[ch["readingdef_uid"].isin(keep_uids)]
            if not len(sub):
                continue
            sub = sub.copy()
            sub["machine"] = sub["readingdef_uid"].map(u2machine)
            sub["role"] = sub["readingdef_uid"].map(u2role)
            sub["time"] = pd.to_datetime(sub["time"], utc=True, errors="coerce")
            sub["value"] = pd.to_numeric(sub["value"], errors="coerce")
            out.append(sub.dropna(subset=["time"]))
    if not out:
        return pd.DataFrame(columns=cols + ["machine", "role"])
    return pd.concat(out, ignore_index=True)


def _resample_machine(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """df = one machine's long rows [time, readingdef_uid, value, role]. -> wide grid."""
    df = df.set_index("time").sort_index()
    parts = {}

    def grouper(s):
        return s.groupby(pd.Grouper(freq=freq))

    # counters: per-uid max -> diff -> clip0 -> sum across uids
    for role in COUNTER_ROLES:
        r = df[df.role == role]
        if len(r):
            per = (r.groupby("readingdef_uid").value
                     .resample(freq).max().groupby(level=0).diff().clip(lower=0))
            parts[f"{role}_delta"] = per.groupby(level=1).sum()

    # cycle_time gauge: mean / std
    ct = df[df.role == "cycle_time"]
    if len(ct):
        parts["cycle_time_mean"] = grouper(ct.value).mean()
        parts["cycle_time_std"] = grouper(ct.value).std()

    # axis_position: per-channel range, then movement total/max across channels
    ax = df[df.role == "axis_position"]
    if len(ax):
        rng = (ax.groupby("readingdef_uid").value.resample(freq)
                 .agg(lambda s: s.max() - s.min()))
        parts["axis_move_total"] = rng.groupby(level=1).sum()
        parts["axis_move_max"] = rng.groupby(level=1).max()

    # run_state: duty = fraction of samples reporting running (value > 0)
    rs = df[df.role == "run_state"]
    if len(rs):
        parts["run_state_duty"] = grouper((rs.value > 0).astype(float)).mean()

    # machine_mode: last value + number of mode changes in bucket
    mm = df[df.role == "machine_mode"]
    if len(mm):
        parts["machine_mode_last"] = grouper(mm.value).last()
        parts["machine_mode_changes"] = grouper(mm.value).agg(lambda s: s.nunique())

    parts["n_samples"] = grouper(df.value).size()
    wide = pd.DataFrame(parts)
    wide = wide[wide["n_samples"] > 0]
    return wide.reset_index().rename(columns={"time": "ts"})


def build_feature_matrix(*, machines=None, freq: str = RESAMPLE_FREQ, dir=None,
                         out: str | Path | None = "analysis/artifacts/ad_features.parquet",
                         ) -> pd.DataFrame:
    """One-time pass -> per-(machine, bucket) wide feature matrix. Writes parquet."""
    uid_map = role_uid_map(dir=dir)
    raw = _collect_rows(uid_map, dir=dir, machines=machines)
    if not len(raw):
        raise RuntimeError("no feature-role telemetry rows found")
    off = _offline_intervals(dir=dir)
    mi = _machine_instance(dir=dir)

    frames = []
    for machine, g in raw.groupby("machine"):
        wide = _resample_machine(g[["time", "readingdef_uid", "value", "role"]], freq)
        if not len(wide):
            continue
        wide.insert(0, "machine", machine)
        # idle: little/no running signal in the bucket
        duty = wide["run_state_duty"] if "run_state_duty" in wide else pd.Series(0.0, index=wide.index)
        wide["is_idle"] = duty.fillna(0.0) < 0.05
        # offline: bucket falls inside an instance offline interval
        inst = mi.get(machine)
        wide["is_offline"] = False
        if inst is not None and len(off):
            oi = off[off.instance_id == inst]
            if len(oi):
                ts = to_ns(wide["ts"])
                mask = np.zeros(len(wide), dtype=bool)
                for s, e in zip(oi.started_on, oi.ended_on.fillna(oi.started_on)):
                    mask |= (ts >= pd.Timestamp(s).value) & (ts <= pd.Timestamp(e).value)
                wide["is_offline"] = mask
        frames.append(wide)

    feats = pd.concat(frames, ignore_index=True).sort_values(["machine", "ts"])
    feats = feats.reset_index(drop=True)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        feats.to_parquet(out, index=False)
    return feats


def feature_columns(feats: pd.DataFrame) -> list[str]:
    """Numeric feature columns present and non-empty (dynamic, never hardcode)."""
    meta = {"machine", "ts", "n_samples", "is_idle", "is_offline"}
    return [c for c in feats.columns
            if c not in meta and feats[c].notna().any()]
