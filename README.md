# trexCloud Hackathon — OEE What-If & Root Cause Analysis

End-to-end solution for the trexCloud CNC + laser plant dataset:
**Anomaly Detection → Root Cause Analysis → What-If/OEE → financial impact**, with a
React dashboard. Targets the "Platinum" bar: cross-machine pattern detection +
quantified ΔOEE, predictive-maintenance attribution, and financial recommendation.

## Setup
```bash
uv sync                      # materialize venv from lockfile
# data lives in dataset/ (default); override with TREX_DATA=/path
```

## Build artifacts
```bash
uv run python scripts/build_foundation.py   # machine_master, signal_map, oee_baseline, downtime_pareto
uv run python scripts/build_ad.py            # anomaly scores + flagged windows (one-time ~few min)
uv run python scripts/build_ad.py "Makine 1" # single machine (fast dev)
uv run python scripts/build_predict.py       # supervised stop-prediction benchmark (multi-model)
uv run python scripts/build_fanuc_risk.py    # deployed Fanuc risk timeline
uv run python scripts/build_scenarios.py     # four-scenario OEE/financial catalog
uv run python scripts/build_pm_value.py      # held-out prediction → OEE/EUR attribution
uv run python scripts/export_web.py          # curated React data bundle
```

## See metrics & demos
```bash
uv run python scripts/evaluate.py    # -> analysis/reports/02_EVALUATION.md + eval_metrics.json + figures/*.html
uv run python scripts/demo.py        # console walkthrough of 5 concrete cases
uv run python scripts/demo.py rca    # one demo: rca | conn | recur | whatif | ad
```
`evaluate.py` reports AD lead-time/precision-recall per machine, RCA cascade/recurrence stats, and
the What-If portfolio impact. `demo.py` prints concrete cases (AIR PRESSURE cascade, connectivity
case, systemic recurrence, a quantified What-If, an AD leading-indicator window).

## Run the React dashboard
```bash
cd web
npm install
npm run dev
```
Views: **Overview**, **Predict→Action** (held-out model quality, attributable OEE/EUR,
scenario catalog), and **Cross-Machine**. The legacy Streamlit app remains available with
`uv run streamlit run app/Home.py`.

## Library (`src/trex/`)
| Module | Purpose |
|---|---|
| `loaders` | cp1254 + `'t'`/`'f'`→bool loaders, `machine_master`, bounded `read_telemetry` |
| `signals` | canonical semantic signal map (vendor-agnostic roles) |
| `oee` | recompute A/P/Q/OEE from JSON components (trusted baseline) |
| `ad` | unsupervised anomaly detection: feature extraction, robust-z/EWMA baselines, lightweight PyTorch autoencoder, eval, emit (RCA evidence layer) |
| `predict` | **supervised** stop prediction: leakage-safe dataset + multi-model benchmark (LogReg/RF/HistGBDT/MLP vs baselines) with classical metrics |
| `rca` | event model, pareto, correlation, ALERT_ARRAY cascade, recurrence, root-cause cards |
| `whatif` | W1–W5 scenario engine, ΔOEE decomposition, financial impact, predictive-maintenance valuation |

**AD vs predict — two different jobs (don't conflate):** `ad` is *unsupervised* and answers
"which signals deviate from normal?" (RCA evidence, scored over the full series). `predict` is
*supervised* and answers "will a significant stop occur in the next 60 min?" with a chronological
train/test split and classical metrics. The unsupervised AD score is ≈random as a *forecaster*
(ROC-AUC ~0.5); use the deployed Fanuc `predict` model (held-out ROC-AUC 0.731) for prediction.

```python
from trex import loaders, signals, oee, ad, rca, whatif
base = oee.baseline(level=1)                          # trusted per machine/day KPIs
card = rca.build_root_cause_card("Makine 1", "2026-01-12 04:40", "2026-01-12 05:00")
res  = whatif.run_scenario(base.iloc[0], whatif.ScenarioSpec("W1", 0.5), category_ms=...)
```

## Key data realities (verified, some contradict the docs)
- **cp1254 (Turkish) encoding**, not UTF-8. Postgres `'t'`/`'f'` booleans. Durations in **ms**, times **UTC**.
- **12 machines**, vendors corrected: Mitsubishi = {4,6,7,8}, Fanuc = {1,2,3,5,9,10}, Nukon = TurboCut.
- **TurboCut 400 & ARES SEIKI have no telemetry** (MES-only RCA). TurboCut is the top downtime sink.
- **The catalog's servo temp/power/path-load signals are EMPTY (0 rows).** Real numeric signals:
  `run_time, axis_position, cycle_time, run_state`. Only 7 of 10 telemetry machines emit features.
- **System Offline (~15k h) is a connectivity fault**, not a machine fault — separated everywhere,
  excluded from AD/OEE recovery. **Q=1 everywhere** (scrap simulated). **P=0 on ~half of machine-days.**
- Nightwatch↔MES join is clean: **162/162 (100%)** `readingdef_uid` ⊂ MES `reading_def.uid`.

Full data review: [`analysis/reports/01_DATA_REVIEW.md`](analysis/reports/01_DATA_REVIEW.md).
Approved implementation plan: `~/.claude/plans/ok-plan-the-full-snappy-valiant.md`.
