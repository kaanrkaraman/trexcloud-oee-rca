"""Canonical semantic signal layer — the enabler for cross-machine modeling.

Vendor naming differs (Fanuc `IsNotRunning` vs Mitsubishi `RUN_STATUS_START__...`),
but they play the same *role*. We map every reading_def to a vendor-agnostic
`canonical_role` so a model/control-chart can reason over roles, not raw names.

Roles align with the hackathon signal matrix (anomaly / context / mechanical-evidence):
  run_state, stop_event, alarm, cycle_time, program, axis_position,
  production_count, spindle_power, servo_power, servo_temp, path_load,
  run_time, machine_mode, stock, scrap, workorder, test_prod, counter, other
"""
from __future__ import annotations
import re
import pandas as pd
from . import loaders

# ordered (first match wins) — patterns matched against readingdef_name (case-insensitive)
_RULES: list[tuple[str, str]] = [
    (r"ALM_ARR_MSG|ALERT", "alarm"),
    (r"SERVO_MOTOR_TEMPERATURE|TEMPERATURE", "servo_temp"),
    (r"POWER_CONSUMPTION.*SPINDLE", "spindle_power"),
    (r"POWER_CONSUMPTION", "servo_power"),
    (r"PATH_LOAD", "path_load"),
    (r"CYCLE_TIME", "cycle_time"),
    (r"IsNotRunning|RUN_STATUS_START|STATINFO_RUN", "run_state"),
    (r"RUN_STATUS_(PAUSE|RESET|STOP)|NC_MODE|EXECUTION|HEAD__", "machine_mode"),
    (r"RUN_TIME|START_TIME", "run_time"),
    (r"System Offline|Undefined Stoppage|M30|MagazineToolChange|Duruş|Bekliyor|SpeedLevel", "stop_event"),
    (r"PROGRAM_POSITION|TCP_.*POSITION|NEXT_DISTANCE|COMMAND_2", "axis_position"),
    (r"RUNNING_PROGRAM_NO|PROGRAM_NUMBER|ProgramNo|StockCode", "program"),
    (r"PIECES_PRODUCED", "production_count"),
    (r"^Counter$|Mill_._Work", "counter"),
    (r"Manual Stock|^Stock", "stock"),
    (r"Manual Scrap|Scrap", "scrap"),
    (r"Manual Workorder|WORK_ORDER", "workorder"),
    (r"Test Production|TEST_PROD", "test_prod"),
]
_COMPILED = [(re.compile(p, re.I), r) for p, r in _RULES]

# roles that carry the multivariate "mechanical evidence" signal for baseline-deviation RCA
EVIDENCE_ROLES = {"servo_temp", "spindle_power", "servo_power", "path_load", "cycle_time"}


def classify(name: str | float) -> str:
    if not isinstance(name, str) or not name.strip():
        return "other"
    for rx, role in _COMPILED:
        if rx.search(name):
            return role
    return "other"


def build_signal_map(dir=None) -> pd.DataFrame:
    """One row per Nightwatch reading_def, enriched with machine, vendor, canonical
    role, and the MES side of the (verified 100%) reading_def_uid join."""
    nrd = loaders.load("trex_nightwatch_reading_def", dir=dir)
    mm = loaders.machine_master(dir=dir)
    nu = loaders.load("trex_nightwatch_unit", dir=dir)[["id", "unit_uid"]]
    mrd = loaders.load("trex_mes_reading_def", dir=dir)[
        ["uid", "signal_type", "signal_category", "display_text", "exclude_from_oee"]
    ].rename(columns={"uid": "readingdef_uid", "display_text": "mes_display_text",
                      "signal_type": "mes_signal_type",
                      "signal_category": "mes_signal_category",
                      "exclude_from_oee": "mes_exclude_from_oee"})
    # MES reading_def has duplicate uids (312 rows / 246 distinct) -> dedup before join
    mrd = mrd.drop_duplicates("readingdef_uid")

    df = (
        nrd.merge(nu, left_on="unit_id", right_on="id", how="left", suffixes=("", "_nu"))
        .merge(mm[["unit_uid", "name", "vendor"]], on="unit_uid", how="left")
        .merge(mrd, on="readingdef_uid", how="left")
    )
    df["canonical_role"] = df["readingdef_name"].map(classify)
    df["is_evidence_signal"] = df["canonical_role"].isin(EVIDENCE_ROLES)
    df["matched_mes"] = df["mes_display_text"].notna()
    cols = ["readingdef_uid", "name", "vendor", "readingdef_name", "canonical_role",
            "is_evidence_signal", "external_signal_type", "external_signal_category",
            "si_unit", "mes_signal_type", "mes_signal_category", "mes_exclude_from_oee",
            "matched_mes", "unit_uid", "unit_id"]
    return df[[c for c in cols if c in df.columns]].rename(columns={"name": "machine"})
