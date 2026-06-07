"""Build the foundation artifacts for both challenges.

Outputs (analysis/artifacts/):
  machine_master.csv     — 12 machines, vendor, telemetry availability
  signal_map.csv         — canonical semantic signal layer (NW reading_def + roles + MES join)
  oee_baseline.parquet   — per machine/day recomputed A/P/Q/OEE (trusted)
  downtime_pareto.csv    — unplanned-stop hours by machine x reason (RCA + What-If lever)
"""
from pathlib import Path
import pandas as pd
from trex import loaders, signals, oee

OUT = Path("analysis/artifacts")
OUT.mkdir(parents=True, exist_ok=True)


def main():
    mm = loaders.machine_master()
    mm.to_csv(OUT / "machine_master.csv", index=False)
    print(f"machine_master: {len(mm)} machines, "
          f"{int(mm.has_telemetry.sum())} with telemetry")

    sm = signals.build_signal_map()
    sm.to_csv(OUT / "signal_map.csv", index=False)
    print(f"signal_map: {len(sm)} signals | matched MES: {int(sm.matched_mes.sum())}/{len(sm)} "
          f"| evidence signals: {int(sm.is_evidence_signal.sum())}")
    print("  roles:", dict(sm.canonical_role.value_counts()))

    base = oee.baseline(level=1)
    base.to_parquet(OUT / "oee_baseline.parquet", index=False)
    print(f"oee_baseline: {len(base)} machine-days | "
          f"median OEE={base.OEE.median():.3f} A={base.A.median():.3f} P={base.P.median():.3f}")

    # downtime pareto (unplanned, machine x reason)
    ss = loaders.load("trex_mes_stoppage_slice")
    unit = loaders.load("trex_mes_unit")[["uid", "name"]]
    rd = loaders.load("trex_mes_reading_def")[["uid", "display_text"]]
    ss = (ss.merge(unit, left_on="unit_uid", right_on="uid", how="left")
            .merge(rd.rename(columns={"uid": "rduid"}), left_on="reading_def_uid",
                   right_on="rduid", how="left"))
    up = ss[ss.is_planned.eq(False).fillna(False)].copy()  # unplanned only, NA-safe
    up["hours"] = loaders.ms_to_hours(up.duration_milliseconds)
    par = (up.groupby(["name", "display_text"], dropna=False)
             .agg(events=("id", "size"), hours=("hours", "sum"))
             .reset_index().sort_values("hours", ascending=False))
    par.rename(columns={"name": "machine", "display_text": "reason"}, inplace=True)
    par.to_csv(OUT / "downtime_pareto.csv", index=False)
    print(f"downtime_pareto: {len(par)} machine x reason rows | "
          f"total unplanned hours={par.hours.sum():.0f}")
    print("\nartifacts written to", OUT.resolve())


if __name__ == "__main__":
    main()
