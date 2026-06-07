# HANDOFF — trexCloud (Predictive OEE + RCA + What-If)

Resume point after a context reset. Everything below is **built, run, and verified**.
Public repo: **https://github.com/kaanrkaraman/trexcloud-oee-rca** (main; dataset & `.venv` gitignored).
Project memory also holds the honest findings:
`~/.claude/projects/-Users-kaan-...-JuneHackathon/memory/` (`trexcloud-dataset-facts.md`,
`trexcloud-workflow-plan.md`, `trexcloud-crossmachine-audit.md`).

> **THE NEXT TASK is in §6.** Everything before it is current state. Read §6 carefully — it is the
> one thing the user wants done next: **connect the prediction layer (ROC/lift) to the OEE-gain layer
> (ΔA/ΔP/ΔOEE + €), and build an inspectable scenario catalog.**

---

## 1. What this is
trexCloud CSV export of one anonymous CNC + laser plant (Aug 2025 – May 2026), 12 machines, ~7.4M
telemetry rows, in `dataset/` (gitignored). Goal targets the **Gold + Platinum** judging bars:
Anomaly Detection → Root-Cause Analysis → What-If/OEE → financial impact, plus a **supervised
stop-prediction** model, surfaced through a **React dashboard** and a **slide deck**.

Python project managed with **`uv`** (rule: never pip). `src/trex/` is an installed package.
Stack: pandas 3.0, torch, scikit-learn 1.9, plotly; React/Vite + Recharts for the web app;
reportlab + python-pptx for the deck.

---

## 2. How to run (cwd = repo root; `TREX_DATA` defaults to `dataset`)
```bash
uv sync                                          # materialize venv (chflags -R nohidden .venv if ModuleNotFoundError)
# --- analysis / models (each writes to analysis/artifacts + analysis/reports) ---
uv run python scripts/build_foundation.py        # machine_master, signal_map, oee_baseline, downtime_pareto
uv run python scripts/build_ad.py                # unsupervised AD scores/windows (RCA evidence)
uv run python scripts/build_predict.py           # multi-model stop-prediction benchmark (pooled)
uv run python scripts/build_crossmachine.py      # NEW honest cross-machine detectors -> 04_CROSSMACHINE.md
uv run python scripts/build_regime_models.py     # merge-vs-split regime experiment -> 05_REGIME_MODELS.md
uv run python scripts/tune_fanuc.py              # leakage-safe Fanuc hyperparameter search -> 06_FANUC_TUNING.md
uv run python scripts/build_fanuc_risk.py        # DEPLOYED Fanuc predictor -> fanuc_risk*.{parquet,csv,json}
# --- web bundle + deck ---
uv run python scripts/export_web.py              # -> web/public/data/bundle.json (curated, static)
uv run python scripts/build_slides.py            # -> trexCloud_Sunum.pptx (editable, notes pane = speaker script)
uv run python scripts/build_slides_pdf.py        # -> trexCloud_Sunum.pdf (landscape 16:9, identical design)
uv run python scripts/build_presentation_plan.py # -> trexCloud_Sunum_Plani.pdf (slide-by-slide plan)
# --- React dashboard ---
cd web && npm install && npm run dev             # http://localhost:5173  (5173, NOT streamlit/8501)
```
Old Streamlit app still exists at `app/` (5 pages, all pass AppTest) — superseded by the React app;
**user has not decided keep/remove.** Render a PDF page to an image for visual checks:
`gs -sDEVICE=png16m -r96 -dFirstPage=N -dLastPage=N -sOutputFile=/tmp/s.png file.pdf` (poppler/LibreOffice
are broken on this machine; `gs` and `qlmanage -t` work).

---

## 3. Library map (`src/trex/`)
| Module | Role | Key API |
|---|---|---|
| `loaders` | cp1254 + `'t'`/`'f'`→bool loaders, machine master, bounded telemetry read | `load`, `machine_master`, `read_telemetry`, `ms_to_hours/minutes` |
| `signals` | canonical vendor-agnostic signal roles | `build_signal_map`, `classify`, `EVIDENCE_ROLES` |
| `oee` | recompute A/P/Q/OEE from raw ms components (trusted) | `baseline(level=1)`, `recompute(...)` (np.divide where=, scalar-safe) |
| `ad` | **unsupervised** AD (RCA evidence, NOT a forecaster) | `features`, `baselines`, `autoencoder`, `eval`, `emit` |
| `predict` | **supervised** stop prediction | `build_supervised`, `run_benchmark`, `time_split`; **`fanuc`** = deployed model |
| `predict.fanuc` | the DEPLOYED predictor | `build_dataset`, `znorm`, `augment`, `train_score`, `risk_episodes`, `FANUC`, `best_params` |
| `rca` | events, pareto, correlate, ALERT cascade, recurrence, **crossmachine**, root-cause cards | `build_event_stream`, `build_root_cause_card`, `to_whatif_bridge`, `crossmachine.*` |
| `whatif` | W1–W5 scenarios, ΔOEE decomposition, financials | `ScenarioSpec`, `run_scenario` (returns before/after/**delta{dOEE,dA,dP,dQ}**), `decompose_oee`, `compute_financials`, `FinancialAssumptions`, `ASSUMPTION_LABEL` |

Web: `web/src/{App.jsx,components.jsx,lib.js,theme.css}` + `web/public/data/bundle.json`.
`lib.js` ports `oee.recompute` + W1 What-If to JS (client-side, instant). 3 views: Overview,
Predict→Action (Gold+Platinum centerpiece), Cross-Machine.
Artifacts in `analysis/artifacts/`, reports `analysis/reports/01..06`.

---

## 4. Load-bearing data facts (VERIFIED — some contradict the docs; do NOT regress)
- **Encoding cp1254 (Turkish), Postgres `'t'/'f'` bools, ms durations, UTC, shift 21:00.** pandas-3.0
  traps handled: text loads as `StringDtype` (don't guard bool coercion on `dtype==object`); µs
  timestamps (use `ad.features.to_ns`, not `.astype('int64')`); `oee.recompute` uses `np.divide(where=)`.
- **The docs' "evidence" signals (servo temp/power/path-load) are catalog-only.** Verified by full
  row-count scan: servo_temp/power = **0 rows even on Makine 7 (2.75M rows total)**; path_load = **28 rows**.
  Real streaming signals: `run_time`, `axis_position`, `cycle_time`, `run_state`. → tahmin tavanı veriyle
  sınırlı, modelle değil.
- **Telemetry regimes (verified by row counts):** Fanuc **{1,2,3,5,9}** = cycle_time+run_state+production
  (only jointly-modelable group; cycle_time spans 8× scale → per-machine z-norm needed). Mitsubishi
  **{7,8}** = run_time+axis (sparse cycle). **{4,6,10,TurboCut,ARES}** telemetry-blind (4/6/10 have
  definitions but 0 streamed rows; TurboCut/ARES 0 definitions). 277k orphan telemetry rows = 59 uids
  not in the reading_def catalog (unattributable).
- **Alarms only on Makine 1 & 2** (77 rows). Flagship: **Makine 1, 2026-01-12 04:47** AIR PRESSURE FAILED
  → Z AXIS ZERO RETURN cascade, root = AIR_PRESSURE (ordered by causal precedence, not array index).
- **All significant unplanned stops carry ONE generic label `Duruş`** → RCA can rank what/when (Pareto),
  not device-level *why* except on M1/M2.
- **Q = 1 everywhere** (ScrapeSum=0 → simulate). **P = 0 on no-production days.** Nightwatch↔MES
  join 162/162 (100%). **System Offline = connectivity fault** (fanned out per `instance_id`), not a machine fault.

---

## 5. Current results (verified, honest)
- **OEE / What-If:** validated. `whatif.run_scenario` recomputes A/P/Q and returns `delta{dOEE,dA,dP,dQ}`
  + recovered runtime + extra pieces; `compute_financials` adds €/payback (labeled assumptions). React
  What-If panel recomputes client-side.
- **Deployed Fanuc predictor** (`predict.fanuc`, `scripts/build_fanuc_risk.py`): target = significant
  (≥15 min) unplanned stop within 60 min; per-machine robust z-norm + augmented features + **tuned
  HistGBDT**. Held-out future (test 2026-01-29 → 05-22): **ROC 0.731, PR-AUC 0.426, lift 2.38, base
  0.179, threshold 0.178, episode precision 0.44 over 722 episodes.** Leakage-safe (chronological split,
  inner-CV tuning, past-only features).
- **Honest within-regime numbers:** Fanuc ROC ~0.72, Mitsubishi ~0.63. The pooled "0.76" was partly
  **base-rate inflation** (Fanuc base 0.18 vs Mitsubishi 0.53). Per-machine z-norm is the real win
  (0.686→0.72 on Fanuc). Mitsubishi {7,8} **not discarded** — scoped out of prediction by signal
  availability, kept in RCA/OEE; best at 30-min horizon (lift 1.59).
- **Cross-machine (honest, `rca.crossmachine`):** old `find_recurrence` top "systemic" hit (CONNECTIVITY)
  is a row-duplication **tautology**. Real: stop **synchronization** 708 co-stop hours vs daily-preserving
  null 564±28 → **z=5.16, p<0.001** (beyond shift rhythm); regime/comparability map; coupling cluster
  {1,2,3,9} is a **slow shared envelope, NOT acute coupling** (detrended r≈0). Reason concordance VACUOUS
  (single `Duruş` label).
- **Deck:** `trexCloud_Sunum.pptx` (11 slides, editable, speaker notes in notes pane) + `.pdf` (identical
  design, gs-verified). Clean light theme, single deep-green accent, consistent master furniture, Turkish
  comma decimals.

---

## 6. ⭐ NEXT TASK — connect prediction ↔ OEE gains + scenario catalog (DO THIS)
**User's intent (verbatim spirit):** "We did an AI predictive-maintenance thing but didn't tie it to OEE
gains. Build scenarios that are easily inspectable, each with ΔA / ΔP / ΔOEE and financial gains computed,
and finalize by **merging the ROC/lift layer with the OEE-gain layer**." The What-If engine already
computes ΔA/ΔP/ΔOEE per scenario — what's missing is (A) a clean named-scenario catalog and (B) a
**model-driven** scenario that turns prediction performance into attributable ΔOEE / €.

### Part A — Scenario catalog (inspectable, ΔA/ΔP/ΔOEE + €)
Build `scripts/build_scenarios.py` → `analysis/artifacts/scenarios.json` + `analysis/reports/07_SCENARIOS.md`.
Curate the scenarios already named in the slides, each on a concrete machine/scope, wiring `category_ms`
from `rca` pareto. For each, call `whatif.run_scenario` + `compute_financials` and emit a tidy row:
`{scenario, machine, ΔA, ΔP, ΔQ, ΔOEE, recovered_h, extra_pieces, gross€, net€, payback}`.
Suggested set (keep it small and legible):
- **S1** Makine X: top unplanned category −30% (W1).  ← the "reduce unplanned by X%" case the user wants ΔOEE for.
- **S2** Reclassify unplanned→planned for a maintenance window (W2).
- **S3** Performance/cycle +10% (W4) — show it's INERT when ProductSum=0 (honesty).
- **S4** Connectivity fixed plant-wide (IT) — show it recovers schedule but is an IT action, **not** machine-OEE (use `is_connectivity` short-circuit).
Surface as a sortable table in the React app (new panel) and a slide.

### Part B — Prediction→OEE bridge (the finale: ROC/lift × OEE/€)
New module `src/trex/whatif/pmvalue.py` + `scripts/build_pm_value.py` →
`analysis/artifacts/pm_value.json` + `analysis/reports/08_PM_VALUE.md`. **Fanuc scope only.** Steps:
1. **Measure the model on the held-out test** (use `fanuc_risk.parquet` + actual significant stops from
   `rca` events): per Fanuc machine, count significant stops; a stop is **caught** iff a bucket with
   `risk ≥ threshold` exists in `(t_stop − 60min, t_stop)`. Compute **recall** = caught/total and
   **caught_downtime_h** = Σ durations of caught stops. Count flagged **episodes** (already 722; precision
   0.44 → ~0.56 are false alarms).
2. **Assumptions (LABEL them, like financials):** `intervention_effectiveness e` (fraction of a caught
   stop's downtime actually avoided/shortened, default ~0.35) and reuse `FinancialAssumptions`
   (downtime_cost_per_hour, intervention_cost, margin, horizon).
3. **Attributable OEE gain:** `prevented_h = caught_downtime_h × e`. Reduce `UnPlannedStop` by `prevented_h`
   on the **test-window** OEE components per machine (recompute `oee.baseline` restricted to test dates, or
   scale the machine baseline by the test fraction) → `oee.recompute` → **ΔA, ΔOEE** attributable to the model.
4. **ROI that ties precision/recall to €:** `value = prevented_h × downtime_cost_per_hour` (or margin via
   extra pieces); `intervention_total = n_flagged_episodes × intervention_cost` (every flag = a check, TP+FP);
   `net = value − intervention_total`, `ROI = net / intervention_total`. **This is the connection** — recall
   drives value, precision drives cost, so OEE/€ now depend on the operating point.
5. **Elegant extra (optional):** sweep the threshold to find the **net-€-maximizing operating point**
   (the cost-based threshold) and report ΔOEE/€ there — shows we pick the threshold by economics, not F1.
6. **Output a single headline** the deck can quote: "AI kestirimci bakım → ~X saat/yıl geri kazanım,
   **+Z puan OEE**, ~€Y net (varsayımlar etiketli)."

### Part C — Surface + finalize
- `export_web.py`: add `scenarios` and `pm_value` blocks to `bundle.json`.
- React: add a **"Kestirimci Bakım Getirisi"** card to Predict→Action (recovered-h, ΔOEE, €, ROI) with
  `e`/cost sliders (client-side recompute), and a **Scenario table** panel. Rebuild (`npm run build`).
- Deck: update slide 7 (Tahmin) or add a slide to show the connected number; update slide 9 (What-If) to
  reference pm_value. Regenerate `.pptx` + `.pdf`.
- Reports: `07_SCENARIOS.md`, `08_PM_VALUE.md`. Commit & push.

### Honesty guardrails for this task (CRITICAL — the project's whole credibility rests on this)
- `e` and all costs are **assumptions** (no cost data in the dump) — label them everywhere (`ASSUMPTION_LABEL`).
- recall/precision are **real** (held-out test); don't inflate. The attributable gain is bounded: you can't
  prevent missed stops, and only `e` of caught ones.
- Don't double-count recovered time (margin XOR downtime-cost, as `compute_financials` already enforces).
- Prediction value is **Fanuc-only**; Mitsubishi/blind machines get OEE gains via generic What-If, not via
  the model. Keep the AD-vs-predict distinction explicit.

---

## 7. Conventions / guardrails
- Never pip; `uv add` / `uv run`. **Never** add a Claude co-author trailer to commits. Repo is now git
  (`origin` = git@github.com:kaanrkaraman/trexcloud-oee-rca.git, branch `main`).
- Never full-scan telemetry; always `read_telemetry(start,end,readingdef_uids)` with a tight window.
- All € figures are labeled assumptions. Keep `ad` = unsupervised RCA evidence vs `predict` = supervised
  forecaster distinct. `dataset/`, `.venv/`, `node_modules/`, `*.parquet`, `*.pt` are gitignored.

## 8. Open / optional threads (lower priority than §6)
- Per-machine probability **calibration** for non-stationary base rates.
- **Longer/short horizon** & time-to-stop regression for Mitsubishi (their 60-min target is saturated).
- Decide keep/remove the old Streamlit `app/`.
- Optional transformer encoder for the AE (`AEConfig.encoder='patchtst'`) — low priority; HistGBDT wins on this feature set.
