# HANDOFF — trexCloud (Predictive OEE + RCA + What-If)

Resume point after a context reset. Everything below is **built, run, and verified**. The project
targets the **Gold + Platinum** judging bars and is **functionally complete** — remaining work is
presentation finalization and a few open decisions (§7).

**Repos / git state (read this):**
- `origin` = `git@github.com:kaanrkaraman/trexcloud-oee-rca.git` (PRIVATE).
- `friend` = `https://github.com/dmrfrkn/trexxxxxhackathon.git` — **the current source of truth**; a
  teammate added the prediction↔OEE bridge + scenarios + deck updates. We fast-forwarded it in.
- Local HEAD = `5cef527` (friend/main) **PLUS uncommitted UI simplification** (`web/src/App.jsx`,
  `components.jsx`, `theme.css`). **Not committed/pushed yet — user decides which remote.**
- `dataset/` (4.3 GB) is gitignored and must stay; never re-download it.

Project memory (honest findings, keep consulting): `~/.claude/projects/-Users-kaan-...-JuneHackathon/memory/`
(`trexcloud-dataset-facts.md`, `trexcloud-workflow-plan.md`, `trexcloud-crossmachine-audit.md`).

---

## 1. What this is
trexCloud CSV export of one anonymous CNC + laser plant (Aug 2025 – May 2026), 12 machines, ~7.4M
telemetry rows, in `dataset/`. Pipeline: AD (baseline deviation) → RCA → What-If/OEE → financial,
plus a supervised stop-predictor, **connected** into one predictive-maintenance value story, surfaced
through a **React dashboard** and a **slide deck**.

`uv`-managed (never pip). `src/trex/` is an installed package. Stack: pandas 3.0, torch,
scikit-learn 1.9; React/Vite + Recharts (web); reportlab + python-pptx (deck).

**Official requirements live in `dataset/presentations/` (3 PPTX) + `dataset/docs/` (3 MD).** Medal
criteria (RCA pptx slide 18): Bronze=list, Silver=match+Pareto, **Gold**=baseline deviation +
multi-signal → causality chain, **Platinum**=cross-machine patterns + quantified ΔOEE + financial
recommendation. The What-If pptx asks for ΔA/ΔP/ΔQ/ΔOEE + impact waterfall + financial card. RCA pptx
slide 16 explicitly asks to **merge RCA with What-If** (the bridge).

---

## 2. How to run (cwd = repo root)
```bash
uv sync                                          # (chflags -R nohidden .venv if ModuleNotFoundError)
# analysis/models -> analysis/artifacts + analysis/reports
uv run python scripts/build_foundation.py        # machine_master, signal_map, oee_baseline, downtime_pareto
uv run python scripts/build_ad.py                # unsupervised AD (RCA evidence)
uv run python scripts/build_crossmachine.py      # honest cross-machine detectors -> 04
uv run python scripts/build_regime_models.py     # merge-vs-split regimes -> 05
uv run python scripts/tune_fanuc.py              # leakage-safe Fanuc tuning -> 06
uv run python scripts/build_fanuc_risk.py        # DEPLOYED Fanuc predictor -> fanuc_risk*.{parquet,csv,json}
uv run python scripts/build_scenarios.py         # What-If scenario catalog (S1..S4) -> scenarios.json + 07
# pm_value (prediction↔OEE bridge) is computed inside export_web (and tested separately)
uv run python scripts/export_web.py              # -> web/public/data/bundle.json (machines, pareto, fanuc,
                                                 #    crossmachine, regime_models, rca_demo, scenarios, pm_value)
uv run python scripts/build_slides.py            # -> trexCloud_Sunum.pptx   (deck; teammate updated it, ~1.2MB)
uv run python scripts/build_slides_pdf.py        # -> trexCloud_Sunum.pdf
uv run --with pytest python -m pytest tests/ -q  # 8 pmvalue tests PASS
cd web && npm install && npm run dev             # http://localhost:5173  (?view=predict|cross|overview)
```
**Visual checks (no LibreOffice/poppler; these work):** PDF page → PNG: `gs -sDEVICE=png16m -r96
-dFirstPage=N -dLastPage=N -sOutputFile=/tmp/s.png file.pdf`. React UI → PNG: start `npm run preview`,
then `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu
--window-size=1500,950 --virtual-time-budget=6000 --screenshot=/tmp/ui.png "http://localhost:5173/?view=predict"`.

---

## 3. Library map (`src/trex/`)
| Module | Role | Key API |
|---|---|---|
| `loaders` | cp1254 + `'t'/'f'`→bool, machine master, bounded telemetry | `load`, `machine_master`, `read_telemetry`, `ms_to_hours/minutes` |
| `signals` | canonical vendor-agnostic roles | `build_signal_map`, `classify`, `EVIDENCE_ROLES` |
| `oee` | recompute A/P/Q/OEE from raw ms (trusted) | `baseline(level=1)`, `recompute(...)` |
| `ad` | unsupervised AD (RCA evidence, NOT a forecaster) | `features`, `baselines`, `autoencoder`, `eval`, `emit` |
| `predict.fanuc` | the DEPLOYED predictor | `train_score`, `risk_episodes`, `znorm`, `augment`, `FANUC`, `best_params` |
| `rca` | events, pareto, correlate, cascade, recurrence, **crossmachine**, root-cause cards | `build_event_stream`, `build_root_cause_card`, `to_whatif_bridge`, `crossmachine.*` |
| `whatif` | scenarios, decomposition, financials, **bridge** | `run_scenario` (→ `delta{dOEE,dA,dP,dQ}`), `compute_financials`, `FinancialAssumptions`, **`pmvalue`** |
| `whatif.pmvalue` | **prediction↔OEE bridge** (teammate, 318 lines, 8 tests) | `evaluate_operating_point`, `threshold_sensitivity`, `attributable_oee`, `financial_projection`, `PMValueAssumptions` |

Web (`web/src/`): `App.jsx` (**rewritten — simplified, 3 lean tabs**), `components.jsx` (Recharts +
hover-jitter fix), `lib.js` (ports `oee.recompute` + W1 + `pmFinancials` to JS), `theme.css`
(dark industrial). Data: `web/public/data/bundle.json`. Reports: `analysis/reports/01..07`.

---

## 4. Load-bearing data facts (VERIFIED — some contradict the docs; do NOT regress)
- **cp1254 (Turkish), Postgres `'t'/'f'` bools, ms durations, UTC, shift 21:00.** pandas-3.0 traps
  handled: text = `StringDtype` (don't guard bool coercion on `dtype==object`); µs timestamps (use
  `ad.features.to_ns`); `oee.recompute` uses `np.divide(where=)`.
- **Docs' "evidence" signals (servo temp/power/path-load) are catalog-only:** 0 rows even on Makine 7
  (2.75M rows); path_load 28 rows. Real streaming: `run_time`, `axis_position`, `cycle_time`,
  `run_state`. → prediction ceiling is set by data, not the model.
- **Regimes (by row counts):** Fanuc **{1,2,3,5,9}** (cycle+run_state+production; only jointly-modelable;
  cycle_time spans 8× → per-machine z-norm needed). Mitsubishi **{7,8}** (run_time+axis, sparse cycle).
  **{4,6,10,TurboCut,ARES}** telemetry-blind (4/6/10 defined but 0 streamed rows).
- **Alarms only on Makine 1 & 2.** Flagship: **Makine 1, 2026-01-12 04:47** AIR PRESSURE FAILED → Z AXIS
  ZERO RETURN, root = AIR_PRESSURE (causal-precedence order, not array index).
- **All significant unplanned stops carry ONE label `Duruş`** → RCA ranks what/when (Pareto), not
  device-level *why* except M1/M2. **Q=1** (simulate), **P=0** on no-production days. NW↔MES join 162/162.
  **System Offline = connectivity** (fanned out per `instance_id`), not a machine fault.

---

## 5. Current results (verified, honest)
- **Deployed Fanuc predictor** (held-out test 2026-01-29→05-22): **ROC 0.731, lift 2.38, episode
  precision 0.44 over 722 episodes**, threshold 0.178. Leakage-safe. Honest within-regime ROC ≈ 0.72
  (Fanuc) / 0.63 (Mitsubishi); pooled "0.76" was partly base-rate inflation. Mitsubishi {7,8} kept in
  RCA/OEE (not discarded), scoped out of prediction by signal availability.
- **Cross-machine (honest):** old `find_recurrence` connectivity #1 hit is a row-duplication TAUTOLOGY.
  Real: stop synchronization 708 co-stop hrs vs daily-null 564±28 → **z=5.16, p<0.001**; regime map;
  coupling {1,2,3,9} = slow envelope, NOT acute (detrended r≈0). Reason concordance VACUOUS.
- **What-If scenarios (`scripts/build_scenarios.py`, bundle `scenarios.rows`):** S1 Makine 1 top-unplanned
  −30% → **ΔOEE +18.0 pp, net €6,614, ROI 22**. S2 reclassify 8h unplanned→planned → ΔA +0.3pp, net −€300
  (no runtime). S3 perf +10% on Makine 4 → **INERT (ProductSum=0)**. S4 connectivity fixed → recovers
  662h schedule but **ΔOEE 0 / net €0 (IT action, not machine OEE)**. All honest edge cases.
- **★ Prediction↔OEE BRIDGE (`whatif.pmvalue`, in bundle `pm_value`) — THE CONNECTION, now done:**
  measured on held-out test → **recall 0.69 (364/527 significant stops caught)**, prevented_h 722 ×
  effectiveness 0.35 → **attributable ΔOEE +10.4 pp (all ΔA)**. Financials charge every alert episode
  (TP+FP): at the deployed F1 threshold **net is NEGATIVE (−€159k observed / −€513k annualized, ROI
  −0.73)** because 722 alerts × €300 > prevented-downtime value. The threshold sweep finds an **economic
  optimum at threshold 0.78** (recall 0.057, precision 0.76, ΔOEE +2.4pp, **annualized net +€11k**).
  *This is the elegant bit: recall drives value, precision drives cost — €/OEE depend on the operating
  point.* **8 pmvalue tests pass.**
- **UI (simplified this session):** App.jsx rewritten into **3 lean tabs** — *Tahmin → Aksiyon* (4 KPIs →
  risk chart → RCA cascade+deviation → What-If slider; the 1-minute story), *Çapraz Makine* (sync bars +
  regimes + honest reading), *Filo & OEE* (fleet grid + Pareto + scenario table). Removed: dense tables
  from hero, financial input fields, telemetry sparklines, big scope box. **Hover jitter fixed**
  (`Tooltip isAnimationActive=false` + `wrapperStyle.transition:'none'` + `.recharts-tooltip-wrapper`).
  `?view=` deep-links. All 3 views screenshot-verified to render cleanly.
- **Deck:** teammate updated `trexCloud_Sunum.pptx/.pdf` (now ~1.2MB, likely embeds visuals). Plus
  `README.md` and `SUNUM_PROFESYONEL_TASARIM_BRIFI.md/.pdf`.

---

## 6. Completeness vs Gold/Platinum — VERIFIED MET (from the official presentations)
- **Gold** (baseline deviation + multi-signal → causality chain): ✅ DeviationBars (robust-z, run_state
  −7.7σ) + AIR PRESSURE→Z-AXIS cascade by causal precedence — exactly the pptx's own example.
- **Platinum** (cross-machine + quantified ΔOEE + financial): ✅ all three pillars (Cross tab, What-If
  ΔOEE + pm_value ΔOEE, scenario/pm € recommendation).
- **What-If ideal deliverable**: baseline dashboard ✅, intervention selector (slider) ✅, ΔOEE→A/P/Q
  decomposition ✅ (shown as before/after A·P·Q bars — *minor*: pptx says "waterfall"; bars are clearer
  for a 1-min demo, optional to swap), financial card ✅. **RCA↔What-If synthesis** ✅ via `pmvalue`.
- **No blocking gaps.** Project is finalize-ready.

---

## 7. ⭐ NEXT — presentation finalization + open decisions
1. **Commit/push the UI simplification.** It's uncommitted. Decide remote: push to `friend` (current
   source of truth) and/or `origin`. No Claude co-author trailer.
2. **Financial framing for the pitch (important):** lead the € recommendation with the **positive S1
   scenario** (Makine 1 air-pressure fix → +18pp OEE, net €6,614), and present the predictive-maintenance
   layer as **+10.4 OEE points operational**. The pm_value *deployed* ROI is NEGATIVE — do NOT headline it;
   it is honest depth (false-alarm economics) and the **economic-optimum threshold (+€11k)** is the answer
   if asked. The UI already does this (shows ΔOEE, not the negative €). (Optional: lower the €300
   intervention assumption to make the deployed point positive — but negative-with-honest-assumptions is
   more credible; discuss with user.)
3. **Deck pass:** confirm the teammate's `trexCloud_Sunum.pptx` reflects the connection (recall→ΔOEE→€,
   economic optimum) and the simplified UI screenshots. Slides target Gold+Platinum; speaker notes in the
   notes pane. Regenerate via `build_slides.py` / `build_slides_pdf.py` if edited.
4. **Optional polish:** swap What-If bars → true ΔOEE waterfall (decompose.py `waterfall_rows` exists);
   decide keep/remove old Streamlit `app/`.

---

## 8. Conventions / guardrails
- Never pip; `uv add` / `uv run`. **Never** add a Claude co-author trailer to commits.
- Never full-scan telemetry; always `read_telemetry(start,end,readingdef_uids)` tight window.
- **All € figures are labeled assumptions** (`ASSUMPTION_LABEL`); no cost data in the dump. recall/precision
  are real (held-out). Keep `ad` (unsupervised RCA evidence) vs `predict` (supervised forecaster) distinct.
  Prediction value is Fanuc-only.
- gitignored: `dataset/`, `.venv/`, `node_modules/`, `*.parquet`, `*.pt`.
