"""Domain knowledge for RCA, isolated here so analytic modules stay data-driven and
the assumptions are visible/tunable in one place.

Event categories, alarm classification, causal precedence for ALERT_ARRAY cascades,
downtime-recoverability factors, and hypothesis templates.
"""
from __future__ import annotations
import re

# ---- event categories (normalized across alert/stoppage/offline/anomaly) -------
EVENT_CATEGORIES = [
    "CONNECTIVITY",        # System Offline / collector offline — NOT a machine fault
    "UNPLANNED_RUNSTOP",   # Duruş / IsNotRunning — the core machine-fault downtime
    "WAITING_WORK",        # İş Bekliyor — operational, no work queued
    "PLANNED_BREAK",       # meals/tea/tool-change/shipment — does not hurt A
    "ALARM",               # CNC alarm event (Makine 1 & 2)
    "ANOMALY",             # AD-flagged telemetry window
]

# ---- alarm text -> canonical alarm category ------------------------------------
_ALARM_PATTERNS = [
    (r"AIR\s*PRESSURE", "AIR_PRESSURE"),
    (r"LUBE|LUBRICAT", "LUBE_OIL"),
    (r"CHUCK", "CHUCK"),
    (r"Z\s*AXIS.*ZERO|ZERO\s*RETURN|REFERENCE\s*POS", "AXIS_ZERO_RETURN"),
    (r"OVERTRAVEL|OVER\s*TRAVEL", "OVERTRAVEL"),
    (r"DOOR|INTERLOCK", "DOOR_INTERLOCK"),
    (r"MOTOR\s*OVERLOAD|OVERLOAD", "MOTOR_OVERLOAD"),
    (r"EMERGENCY\s*STOP|ACIL", "EMERGENCY_STOP"),
    (r"ILLEGAL|FORMAT|COMMAND", "PROGRAM_ERROR"),
]


def classify_alarm(text) -> str:
    if not isinstance(text, str):
        return "OTHER_ALARM"
    t = text.upper()
    for rx, cat in _ALARM_PATTERNS:
        if re.search(rx, t):
            return cat
    return "OTHER_ALARM"


# ---- stoppage display_text -> event category -----------------------------------
def classify_stop(display_text, is_planned=None) -> str:
    t = (display_text or "").lower()
    if "system offline" in t or "offline" in t:
        return "CONNECTIVITY"
    if "bekliyor" in t or "waiting" in t:
        return "WAITING_WORK"
    if any(k in t for k in ("mola", "ayar", "sevkiyat", "magazin", "takım", "tool",
                            "m30")):
        return "PLANNED_BREAK"
    if is_planned is True:
        return "PLANNED_BREAK"
    if "duruş" in t or "durus" in t or "isnotrunning" in t or "not running" in t \
       or "undefined" in t:
        return "UNPLANNED_RUNSTOP"
    return "UNPLANNED_RUNSTOP" if is_planned is False else "OTHER"


# ---- causal precedence for ALERT_ARRAY cascades --------------------------------
# lower rank = more upstream = more likely the ROOT (utility/pneumatic first;
# EMERGENCY_STOP/DOOR ranked late = usually a consequence or operator reaction).
CAUSAL_PRECEDENCE = {
    "AIR_PRESSURE": 0, "LUBE_OIL": 1, "MOTOR_OVERLOAD": 2, "CHUCK": 3,
    "AXIS_ZERO_RETURN": 4, "OVERTRAVEL": 5, "PROGRAM_ERROR": 6,
    "DOOR_INTERLOCK": 7, "EMERGENCY_STOP": 8, "OTHER_ALARM": 9,
}

# ---- how much of a category's downtime is realistically recoverable by a fix ----
RECOVERY_FACTOR = {
    "UNPLANNED_RUNSTOP": 0.5, "AIR_PRESSURE": 0.8, "LUBE_OIL": 0.7,
    "CHUCK": 0.6, "DOOR_INTERLOCK": 0.5, "AXIS_ZERO_RETURN": 0.6,
    "EMERGENCY_STOP": 0.3, "WAITING_WORK": 0.4, "CONNECTIVITY": 0.0,  # IT, not OEE
    "ANOMALY": 0.5, "OTHER": 0.3, "OTHER_ALARM": 0.3,
}

# ---- hypothesis templates keyed by alarm/stop category -------------------------
HYPOTHESIS_RULES = {
    "AIR_PRESSURE": [
        ("Pneumatic supply pressure loss (facility/compressor)", 0.7,
         "Air-pressure alarm fired; downstream axis/chuck faults are typical consequences",
         "Check compressor, air lines, pressure switch; add pressure monitoring"),
        ("Faulty pressure switch / sensor", 0.2,
         "Recurring air-pressure alarms without process change", "Replace/recalibrate switch"),
    ],
    "AXIS_ZERO_RETURN": [
        ("Reference lost after upstream fault (e.g. air pressure / e-stop)", 0.6,
         "Zero-return alarm commonly follows a power/pneumatic interruption",
         "Re-home axis; address the upstream trigger"),
        ("Encoder / homing switch fault", 0.3, "Repeated zero-return without upstream cause",
         "Inspect encoder and homing hardware"),
    ],
    "DOOR_INTERLOCK": [
        ("Safety door opened during cycle", 0.6, "Interlock alarm during production",
         "Operator training; verify guarding procedure"),
        ("Faulty door switch", 0.3, "Recurring interlock alarms", "Replace door switch"),
    ],
    "EMERGENCY_STOP": [
        ("Operator/safety-circuit intervention", 0.6, "E-stop is typically a reaction",
         "Review the triggering condition that prompted the stop"),
    ],
    "CONNECTIVITY": [
        ("Collector / network outage (not a machine fault)", 0.9,
         "System Offline = collector lost connection; no machine telemetry during window",
         "Fix network/collector reliability — does NOT recover machine OEE"),
    ],
    "UNPLANNED_RUNSTOP": [
        ("Unclassified machine stop (missing operator reason)", 0.5,
         "IsNotRunning/Duruş with no alarm or offline overlap",
         "Improve stop-reason classification; investigate top recurring windows"),
    ],
}
