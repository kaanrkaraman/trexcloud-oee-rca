# Foundation artifacts

Built by `uv run python scripts/build_foundation.py` (re-run after any loader/signal change).
All loaders bake in the dataset gotchas (cp1254, `'t'`/`'f'` booleans, ms, recomputed OEE).

| File | What it is | Key columns |
|---|---|---|
| `machine_master.csv` | 12 machines, vendor, telemetry availability | `unit_uid, name, vendor, is_enabled, nw_unit_id, has_telemetry` |
| `signal_map.csv` | Canonical semantic signal layer — every Nightwatch signal → vendor-agnostic role + MES join (100% matched) | `readingdef_uid, machine, vendor, readingdef_name, canonical_role, is_evidence_signal` |
| `oee_baseline.parquet` | Per machine/day **recomputed** A/P/Q/OEE (trusted; ignores noisy stored columns) | `machine, date, OEE, A, P, Q, ProductSum, WorkTotal, PlannedStop, UnPlannedStop` |
| `downtime_pareto.csv` | Unplanned-stop hours by machine × reason (RCA target + What-If lever) | `machine, reason, events, hours` |
| `ad_features.parquet` | 60s-grid telemetry feature matrix (built by `scripts/build_ad.py`) | `machine, ts, cycle_time_*, axis_move_*, run_time_delta, run_state_duty, …, is_idle, is_offline` |
| `ad_scores.parquet` | Per-bucket anomaly score timeline (RCA contract) | `machine, ts, score_baseline, score_ae, score, top_roles, is_idle, is_offline` |
| `ad_anomaly_windows.parquet` | Flagged anomaly windows | `machine, window_start, window_end, peak_score, detector, top_roles, nearest_label, lead_time_min` |
| `ad_ae_<machine>.pt` | Trained autoencoder weights per machine | — |
| `fanuc_risk.parquet` | Held-out deployed Fanuc risk buckets | `machine, ts, y_true, risk` |
| `fanuc_model_meta.json` | Audited model metrics and deployed operating point | ROC/PR-AUC/lift, threshold, episode precision |
| `scenarios.json` | Four inspectable OEE/financial scenarios | ΔA/ΔP/ΔQ/ΔOEE, runtime/schedule hours, EUR, owner |
| `pm_value.json` | Held-out prediction → OEE/EUR attribution | recall, caught/prevented hours, OEE gain, observed/projected value, sensitivity |

## Quick use
```python
from trex import loaders, signals, oee
mm   = loaders.machine_master()          # machine taxonomy
smap = signals.build_signal_map()        # canonical roles; filter is_evidence_signal
base = oee.baseline(level=1)             # trusted per machine/day KPIs
# filtered telemetry read — NEVER full-scan 7.4M rows:
tel  = loaders.read_telemetry(start="2026-01-12 04:32", end="2026-01-12 05:00",
                              readingdef_uids=[...])
```

## Tiering (drives modeling scope)
- **Predictive Fanuc (1/2/3/5/9):** cycle_time + run_state + production; per-machine normalized supervised model.
- **Mitsubishi RCA (7/8):** run_time + axis position, with sparse cycle data; retained for RCA/OEE, not the deployed predictor.
- **Telemetry-blind (4/6/10/TurboCut/ARES):** no streamed model inputs; MES-only RCA and generic What-If.
- Catalog-only servo temperature/power signals contain no rows; path load has only 28 rows and is not a predictive input.
