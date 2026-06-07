# HANDOFF — trexCloud Hackathon (OEE What-If + RCA + Stop Prediction)

Resume point for continuing after context compaction. Everything below is **built, run, and
verified**. Project memory also holds this: `~/.claude/projects/-Users-kaan-...-JuneHackathon/memory/`
(`trexcloud-dataset-facts.md`, `trexcloud-workflow-plan.md`). Approved plan:
`~/.claude/plans/ok-plan-the-full-snappy-valiant.md`.

---

## 1. What this is
trexCloud CSV export of one anonymous CNC + laser plant (Aug 2025 – May 2026), in `dataset/`.
Goal: **Anomaly Detection → Root Cause Analysis → What-If/OEE → financial impact**, plus a
**supervised stop-prediction** model, surfaced through a Streamlit dashboard. Targets the
"Platinum" judging bar (cross-machine patterns + quantified ΔOEE + financial recommendation).

Python project managed with **`uv`** (rule: never pip). `src/trex/` is an installed package
(`uv sync` already done). pandas 3.0, torch, scikit-learn, streamlit, plotly installed.

---

## 2. How to run (cwd = repo root; `TREX_DATA` defaults to `dataset`)
```bash
uv sync                                       # if env missing
uv run python scripts/build_foundation.py     # machine_master, signal_map, oee_baseline, downtime_pareto
uv run python scripts/build_ad.py             # unsupervised AD scores + windows (~few min, one-time)
uv run python scripts/build_predict.py        # supervised stop-prediction benchmark (multi-model)
uv run python scripts/evaluate.py             # consolidated metrics -> 02_EVALUATION.md + figures
uv run python scripts/demo.py [rca|conn|recur|whatif|ad]   # console demo of concrete cases
uv run streamlit run app/Home.py              # interactive dashboard (5 pages)
```
Verification idiom used throughout: `AppTest.from_file('app/<page>.py').run()` → assert
`len(at.exception)==0`. All 5 pages pass.

---

## 3. Library map (`src/trex/`)
| Module | Role | Key API |
|---|---|---|
| `loaders` | cp1254 + `'t'`/`'f'`→bool loaders, machine master, bounded telemetry read | `load(table)`, `machine_master()`, `read_telemetry(start,end,readingdef_uids)`, `ms_to_hours/minutes`, `to_ns` (in ad) |
| `signals` | canonical semantic signal map (vendor-agnostic roles) | `build_signal_map()`, `classify()`, `EVIDENCE_ROLES` |
| `oee` | recompute A/P/Q/OEE from JSON components (trusted) | `baseline(level=1)`, `recompute(...)` (np.divide where=, scalar-safe) |
| `ad` | **unsupervised** AD (RCA evidence) | `features.build_feature_matrix`, `baselines.fit_envelopes/score_features`, `autoencoder` (swap-able encoder), `labels`, `eval`, `emit` |
| `predict` | **supervised** stop prediction (multi-model, leakage-safe) | `build_supervised(...)`, `run_benchmark(...)`, `time_split`, `feature_importance` |
| `rca` | event model, pareto, correlation, ALERT_ARRAY cascade, recurrence, root-cause cards | `build_event_stream`, `build_event_timeline`, `stop_pareto`, `group_alarm_arrays`, `find_recurrence`, `build_root_cause_card`, `to_whatif_bridge` |
| `whatif` | W1–W5 scenarios, ΔOEE decomposition, financials | `run_scenario(spec, category_ms=)`, `decompose_oee`, `compute_financials`, `FinancialAssumptions` |

Dashboard: `app/Home.py` + `app/pages/{1_RCA_Event_Explorer,2_What_If,3_Cross_Machine_Recurrence,4_Model_Benchmark}.py`,
helpers in `app/lib/{data,charts,state}.py` (cached). Artifacts in `analysis/artifacts/`,
reports in `analysis/reports/` (`01_DATA_REVIEW.md`, `02_EVALUATION.md`, `03_PREDICTION_BENCHMARK.md`,
`figures/*.html`).

---

## 4. Load-bearing data facts (VERIFIED — some contradict the dataset docs)
- **Encoding cp1254 (Turkish), NOT utf-8.** Booleans are Postgres `'t'`/`'f'` strings. Durations ms, times UTC, shift boundary 21:00.
- **pandas 3.0 traps (all handled, don't regress):** text loads as `StringDtype` (don't guard bool coercion on `dtype==object`); timestamps stored at **µs** so `.astype('int64')` ≠ epoch-ns (use `ad.features.to_ns`); `oee.recompute` uses `np.divide(...,where=)` not `np.where` (the latter divides by zero on scalars).
- **12 machines; vendor map corrected:** Mitsubishi = {4,6,7,8}, Fanuc = {1,2,3,5,9,10}, Nukon laser = TurboCut 400; ARES SEIKI disabled. **TurboCut & ARES have NO telemetry** (MES-only RCA); TurboCut is the top downtime sink.
- **The catalog's "evidence" signals (servo temp/power/path-load) are EMPTY — 0 rows.** Real numeric signals that stream: `run_time` (2.8M), `axis_position` (1.3M), `cycle_time` (1.1M), `run_state` (868K). Only **7 of 10** telemetry machines emit features (1,2,3,5,7,8,9); Makine 4/6/10 are catalog-only.
- **System Offline (~15k h) = connectivity fault, not machine fault** — excluded from AD/OEE recovery; its identical duplicated hours across machines = the systemic fingerprint.
- **Q = 1 everywhere** (ScrapeSum=0 → simulate Q). **P = 0 on ~half of machine-days** (no counted production); production concentrated in Makine 9 & 3.
- **Nightwatch↔MES join is clean: 162/162 (100%)** `readingdef_uid` ⊂ MES `reading_def.uid`. NW join path: `readingdef_uid → reading_def.unit_id(int) → nightwatch_unit.id → unit_uid`.
- **Alarms exist only for Makine 1 & 2** (77 rows). Flagship case: Makine 1 2026-01-12 04:47 AIR PRESSURE FAILED → Z AXIS ZERO RETURN cascade (root = AIR_PRESSURE).

---

## 5. Current results (verified)
- **OEE/RCA/What-If:** What-If math validated (doc case Makine 1 2025-11-05 W1 50% → A 0→0.50; ΔOEE decomposition residual 0). Recurrence top = CONNECTIVITY across 11 machines. Portfolio W1 −30% across all machine-days ≈ 3,062 h recovered / ~322k TRY at *labeled* assumptions.
- **Unsupervised AD:** RCA evidence layer. NOTE its lead-time/PR numbers are optimistic (global normalization, no time-split). As a *forecaster* it is ≈random (ROC ~0.51) — use `predict`, not `ad`, for prediction.
- **Supervised stop prediction (latest work):** target = significant (≥15 min) unplanned stop within 60 min. **Best = HistGradientBoosting: PR-AUC 0.53, ROC-AUC 0.76, 2.1× lift, F1 0.55 (P 0.49 / R 0.62)**, beating RF/LogReg/MLP and all trivial baselines.
  - **Methodology fix that got us there:** original `running_only` masking dropped idle buckets and capped ROC at 0.71. Correct masking = keep idle buckets (+`is_idle` feature) but EXCLUDE buckets inside an active significant stop (removing them *raised* ROC → genuine pre-stop signal, no tautology). Plus micro-stop dynamics features. Verified pooling is fine (per-machine z-norm / machine one-hot give identical ROC).
  - Leakage-safe: past-only features, chronological per-machine split, preprocessors fit on train only, automated leakage assertion in `build_predict.py`.
  - **Honest ceiling ~0.76:** condition signals (temp/power/load) are empty; many "Duruş" stops are operational; stop rates are non-stationary (Makine 5 & 9 nearly double train→test).

---

## 6. Open threads / suggested next steps (in priority order)
1. **Per-machine probability calibration** (e.g. `CalibratedClassifierCV` or isotonic per machine) to handle the non-stationary base rates — likely the biggest honest gain for usability.
2. **Cost-based operating point**: pick the decision threshold from intervention cost vs missed-stop cost (a 60-min warning is only worth it if precision/recall match the economics). Tie into `whatif.FinancialAssumptions`.
3. **Longer horizon test** (2–4 h): often easier and more actionable than 60 min.
4. **Wire prediction into the RCA→What-If story**: high predicted-risk windows → preemptive root-cause + recovered-downtime estimate.
5. Optional: transformer encoder for the AE is swap-able (`AEConfig.encoder='patchtst'`, implement branch in `autoencoder.build_encoder`) — but tabular HistGBDT already wins on this feature set; low priority.
6. `scripts/diagnose_predict.py` is the ablation harness (per-machine separate models still error on all-NaN columns — drop all-NaN cols per machine if you want those numbers).

---

## 7. Conventions / guardrails
- Never pip; use `uv add` / `uv run`. Never add Claude co-author trailer to commits. Repo root is **not** a git repo from where checked (`git status` failed) — confirm before any commit work.
- Never full-scan telemetry; always `read_telemetry(start,end,readingdef_uids)` with a tight window.
- Financial numbers are user assumptions — always label them (the code does via `ASSUMPTION_LABEL`).
- Keep the AD-vs-predict distinction explicit: `ad` = unsupervised RCA evidence ("what deviated"); `predict` = supervised forecaster ("will it stop soon"). Do not present AD lead-time as a predictive metric.

---

## 8. Session addendum — cross-machine, regime modeling, deployed Fanuc predictor + integrated page
New work (all built/verified). Honest findings live in project memory `trexcloud-crossmachine-audit.md`.
- **Cross-machine (honest):** `rca/crossmachine.py` + `scripts/build_crossmachine.py` → `analysis/reports/04_CROSSMACHINE.md`. Old `find_recurrence` CONNECTIVITY top hit is a **row-duplication tautology** (offline fanned out by `instance_id`). Real results: significant-stop **synchronization** beyond chance AND beyond shared hour-of-day (daily-preserving null z=5.16); a `{1,2,3,9}` score cluster that is a **slow shared envelope, NOT acute coupling** (detrended r≈0); the **regime/comparability map**. Reason concordance is VACUOUS (all unplanned stops = one label `Duruş`).
- **Regimes (verified by row counts):** only `{1,2,3,5,9}` (Fanuc: cycle_time+run_state+production) are jointly modelable; `{7,8}` (Mitsubishi: run_time+axis, sparse cycle) are a separate weak regime; `{4,6,10,TurboCut,ARES}` are telemetry-blind (4/6/10 have defs but 0 streamed rows). Vendor "evidence" signals (servo_temp/path_load) are **0/28 rows even on Makine 7** — intended design, never delivered.
- **Merge experiment:** `scripts/build_regime_models.py` → `05_REGIME_MODELS.md`. Raw merge ≈ wash; **per-machine robust z-norm is the win** (Fanuc ROC 0.686→0.72). The headline pooled 0.76 ROC was partly **base-rate inflation** (Fanuc base 0.18 vs Mits 0.53); honest within-regime ROC ≈0.72 (Fanuc) / 0.63 (Mits).
- **Deployed Fanuc predictor:** `src/trex/predict/fanuc.py` (per-machine z-norm + augmented features + tuned HistGBDT). Tuning `scripts/tune_fanuc.py` → `06_FANUC_TUNING.md` (leakage-safe inner CV). **Final: ROC 0.731, lift 2.38, episode precision 44% (base 18%).** Mitsubishi best at 30-min horizon (lift 1.59) — kept in RCA/OEE, NOT discarded; predictor scoped to Fanuc by signal availability.
- **Risk artifacts:** `scripts/build_fanuc_risk.py` → `fanuc_risk.parquet`, `fanuc_risk_episodes.csv`, `fanuc_model_meta.json`.
- **Integrated dashboard page:** `app/pages/5_Predict_to_Action.py` — Predict (risk timeline + episodes) → RCA (root-cause card) → What-If (ΔOEE waterfall + €). Reuses `lib.charts.risk_timeline`, `data.fanuc_*`. All 6 pages pass AppTest (0 exceptions).
