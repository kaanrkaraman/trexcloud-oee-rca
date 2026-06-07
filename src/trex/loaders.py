"""Encoding-aware, boolean-correct loaders for the trexCloud CSV dump.

Bakes in every data gotcha discovered during review:
  * cp1254 (Turkish) encoding, never UTF-8
  * Postgres 't'/'f' string booleans -> real bool
  * ms durations -> helpers to hours/minutes
  * UTC timestamp parsing
  * Nightwatch integer unit_id -> unit_uid resolution
  * never full-scan the 7.4M-row telemetry: time/signal-filtered reader

Set the data directory via TREX_DATA env var, or pass data_dir explicitly.
"""
from __future__ import annotations
import os
from glob import glob
from pathlib import Path
import pandas as pd

ENC = "cp1254"
_BOOL = {"t": True, "f": False, "true": True, "false": False, True: True, False: False}

# columns that are Postgres 't'/'f' booleans across the dump
BOOL_COLS = {
    "purge", "sync", "remove", "is_enabled", "is_planned", "is_unit_on",
    "is_test_prod", "exclude_from_oee", "is_online", "is_array", "is_stock",
    "is_work_order", "is_deleted", "enabled", "is_expression", "is_manual_entry",
    "is_simulation", "is_potential_anomaly", "has_machine_opcode",
    "calculate_oee_with_stock", "system_offline_is_planned",
}
TS_COLS = {
    "started_on", "ended_on", "trans_date", "slice_on", "received_on",
    "heartbeat_on", "inserted_on", "time", "source_utc_timestamp",
    "server_utc_timestamp", "last_update_date", "started_on_system",
    "local_data_day",
}


def data_dir(data_dir: str | os.PathLike | None = None) -> Path:
    d = data_dir or os.environ.get("TREX_DATA", "dataset")
    return Path(d)


def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        if c in BOOL_COLS and df[c].dtype != bool:
            # pandas 3.0 reads text as StringDtype (not object); map regardless of dtype
            df[c] = df[c].map(_BOOL).astype("boolean")
        elif c in TS_COLS:
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    return df


def load(table: str, *, dir: str | os.PathLike | None = None, coerce: bool = True,
         **kw) -> pd.DataFrame:
    """Load one logical table (no .csv). Numbered parts (e.g. nightwatch_data) are
    concatenated when `table` is the prefix. Use `read_telemetry` for filtered reads."""
    base = data_dir(dir)
    parts = sorted(glob(str(base / f"{table}_[0-9][0-9][0-9].csv")))
    paths = parts if parts else [base / f"{table}.csv"]
    df = pd.concat(
        (pd.read_csv(p, encoding=ENC, low_memory=False, **kw) for p in paths),
        ignore_index=True,
    )
    return _coerce(df) if coerce else df


def ms_to_hours(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce") / 3_600_000.0


def ms_to_minutes(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce") / 60_000.0


def machine_master(dir: str | os.PathLike | None = None) -> pd.DataFrame:
    """One row per MES machine with vendor, enabled flag, and the Nightwatch
    integer id (NaN for the two telemetry-less machines: TurboCut, ARES SEIKI)."""
    unit = load("trex_mes_unit", dir=dir)
    dev = load("trex_mes_device", dir=dir)[["uid", "collector_type_name"]]
    nu = load("trex_nightwatch_unit", dir=dir)[["id", "unit_uid"]]
    m = (
        unit.merge(dev, left_on="device_uid", right_on="uid", suffixes=("", "_dev"), how="left")
        .merge(nu.rename(columns={"id": "nw_unit_id"}), left_on="uid", right_on="unit_uid",
               suffixes=("", "_nw"), how="left")
    )
    vendor = {"FanucFocas": "Fanuc", "MitsubishiCnc": "Mitsubishi", "LibPlc": "Nukon"}
    m["vendor"] = m["collector_type_name"].map(vendor)
    m["has_telemetry"] = m["nw_unit_id"].notna()
    return m[["uid", "name", "vendor", "collector_type_name", "is_enabled",
              "nw_unit_id", "has_telemetry"]].rename(columns={"uid": "unit_uid"})


def read_telemetry(dir: str | os.PathLike | None = None, *, string: bool = False,
                   start=None, end=None, readingdef_uids=None,
                   columns=("time", "readingdef_uid", "value", "index", "instance_id"),
                   chunksize: int = 1_000_000) -> pd.DataFrame:
    """Filtered streaming read of the big telemetry tables. ALWAYS pass a time range
    and/or readingdef_uids — never materialize all 7.4M rows. Returns a filtered frame."""
    base = data_dir(dir)
    prefix = "trex_nightwatch_data_string" if string else "trex_nightwatch_data"
    paths = sorted(glob(str(base / f"{prefix}_[0-9][0-9][0-9].csv")))

    def _utc(x):
        if x is None:
            return None
        t = pd.Timestamp(x)
        return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")

    start, end = _utc(start), _utc(end)
    uid_set = set(readingdef_uids) if readingdef_uids is not None else None
    out = []
    for p in paths:
        for ch in pd.read_csv(p, encoding=ENC, usecols=lambda c: c in columns,
                              low_memory=False, chunksize=chunksize):
            ch["time"] = pd.to_datetime(ch["time"], utc=True, errors="coerce")
            if start is not None:
                ch = ch[ch["time"] >= start]
            if end is not None:
                ch = ch[ch["time"] <= end]
            if uid_set is not None:
                ch = ch[ch["readingdef_uid"].isin(uid_set)]
            if len(ch):
                out.append(ch)
    return (pd.concat(out, ignore_index=True) if out
            else pd.DataFrame(columns=list(columns)))
