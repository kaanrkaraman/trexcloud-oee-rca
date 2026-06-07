# trexCloud Hackathon — Data Review & Workflow Assessment

**Author:** prepared for Kaan · **Date:** 2026-06-06
**Source:** `dataset/` (trexCloud Postgres/TimescaleDB export, single anonymous CNC + laser plant)
**Grounding:** every number below was verified by running EDA over the actual CSVs (`analysis/scripts/eda.py`, `eda2.py`), not just read from the docs.

> **⚠️ CORRECTION (2026-06-07, post-implementation).** A full scan of all 19 numeric telemetry
> files disproved one claim below: the Mitsubishi "mechanical evidence" signals
> (`SERVO_MOTOR_TEMPERATURE_*`, `POWER_CONSUMPTION_*` servo/spindle, `PATH_LOAD_MODULE_*`)
> are **catalog-only — 0 rows** in the actual data. The numeric signals that *do* stream are
> `run_time` (2.8M), `axis_position` (1.3M), `cycle_time` (1.1M), `run_state` (868K), shared
> across vendors. So AD/multivariate modeling is built on movement/cycle/duty signals, not
> temp/power, and cross-machine modeling is *more* uniform than tiering implies. Items 12, §3.2
> and §6 below are superseded by this note. Also: only 7 of 10 telemetry machines (1,2,3,5,7,8,9)
> actually emit numeric features — Makine 4, 6, 10 have signal definitions but no telemetry rows.

---

## 0. TL;DR — the 12 things that actually matter

1. **The Nightwatch↔MES join is clean and complete.** Every one of the 162 Nightwatch `readingdef_uid`s appears in the MES `reading_def.uid` catalog (**162/162 = 100%**). `reading_def_uid` is a perfect bridge between domains; `unit_uid` joins machines. Your stated join concern is solved.
2. **There are 12 MES machines, not 10**, and the machine→vendor mapping in the docs is **wrong/incomplete**: **Makine 4 and Makine 6 are Mitsubishi**, not Fanuc. Mitsubishi = {4, 6, 7, 8}; Fanuc = {1, 2, 3, 5, 9, 10} (+ ARES SEIKI, disabled); Nukon laser = TurboCut 400.
3. **Two machines have NO Nightwatch telemetry at all**: **TurboCut 400** and **ARES SEIKI**. They are absent from `trex_nightwatch_unit`. TurboCut is the single **highest-downtime machine (7,653 unplanned hours)** — so your worst offender has no sensor evidence. Telemetry-based RCA is impossible there.
4. **Alerts exist for only 2 machines**: Makine 1 (29) and Makine 2 (48), 77 parsed rows total. The clean "alarm → stop" RCA story is only richly available for these two.
5. **Downtime is dominated by two buckets**: `Duruş`/IsNotRunning (unplanned, ~19,191 h) and `System Offline` (~14,901 h). **System Offline is a connectivity fault, not a machine fault** — there is no telemetry during offline, so no AD/RCA model can "explain" it from sensors. Must be separated up front via `trex_mes_status`.
6. **Quality is 1.0 everywhere** (`ScrapeSum = 0`, verified 0 nonzero rows). Any Q What-If must be simulated.
7. **Performance is 0 for ~half of machine-days**, and counted production is concentrated in just **Makine 9 (141k pieces) and Makine 3 (109k)**; every other machine is in the low thousands. OEE is therefore ≈0 for most machine-days.
8. **Do NOT trust the scalar OEE/A columns.** The stored `A` is noisy: 12 machine-day rows have `A < 0`, OEE ranges down to −64. Recompute A, P, Q from the JSON components yourself.
9. **Encoding is cp1254 / ISO-8859-9 (Turkish), NOT UTF-8.** Reading as UTF-8 throws `0xfd`/`0x98` errors. All Turkish labels (`Duruş`, `İş Bekliyor`, `Yemek Molası`) live here.
10. **Booleans are Postgres `'t'`/`'f'` strings**, not `True`/`False`. `df.is_planned == False` silently matches nothing — this is a real trap (it bit this analysis once).
11. **Times are UTC milliseconds**; shift boundary at 21:00 UTC; `level=0` plant vs `level=1` machine in `oee_summary`.
12. **Signal richness is tiered *in the catalog* — but the rich signals are empty.** Mitsubishi *defines* 27–30 signals incl. servo temperature/power/path-load, but those carry **0 telemetry rows** (see correction banner). In practice every telemetry machine exposes the same usable numeric roles (cycle_time, run_state, + run_time/axis_position on Mitsubishi), so cross-machine modeling on canonical roles is uniform, not Mitsubishi-only.

---

## 1. What the dataset is

PostgreSQL/TimescaleDB export from **trexCloud** for one anonymous plant ("Demo Plant"), tenant `3a1b2a65-d6cf-72ac-d066-46993d168fef`. Two product domains over the **same physical machines**:

| Prefix | Domain | Content |
|---|---|---|
| `trex_mes_*` | MES (business layer) | OEE/A/P/Q, stoppages, production counters, work orders, alarms, collector status |
| `trex_nightwatch_*` | Machine monitoring | High-frequency raw telemetry (numeric + string), signal metadata |

**Shared hierarchy:** `tenant_id → instance_id → device_uid → unit_uid → reading_def_uid`.

**Date coverage (verified):**
- Telemetry & MES events (stoppage, counter, workorder): **2025-08-20 → 2026-05-24**
- `oee_summary`: **2025-10-20 → 2026-05-24** (precomputed OEE starts ~2 months later than raw data)

**Volume (verified by row count):**
- `trex_nightwatch_data_*` (19 parts): **~7.36M** numeric rows (docs said 6.26M — actual is higher)
- `trex_nightwatch_data_string_*` (5 parts): **~1.11M** string rows
- MES events total ~153k (`stoppage_slice` ~52–55k, `counter_slice` 91,436, `workorder` 9,913)

---

## 2. Machine taxonomy (corrected from data, not docs)

| Machine | MES `unit_uid` | NW `id` | Vendor / collector | Enabled | NW telemetry? | NW signals |
|---|---|---|---|---|---|---|
| Makine 1 | `3a1d1435-0bb7-…cbf3` | 4 | Fanuc / FanucFocas | ✓ | ✓ | 17 |
| Makine 2 | `3a1d1435-0afb-…5258` | 5 | Fanuc / FanucFocas | ✓ | ✓ | 17 |
| Makine 3 | `3a1d8054-94bd-…2199` | 8 | Fanuc / FanucFocas | ✓ | ✓ | 17 |
| Makine 5 | `3a1debd9-412d-…9a94` | 9 | Fanuc / FanucFocas | ✓ | ✓ | 17 |
| Makine 9 | `3a1d1435-0a17-…78ee` | 3 | Fanuc / FanucFocas | ✓ | ✓ | 17 |
| Makine 10 | `3a1debf8-841b-…9668` | 12 | Fanuc / FanucFocas | ✓ | ✓ | 17 |
| **Makine 4** | `3a1debd9-c20c-…2887` | 10 | **Mitsubishi** / MitsubishiCnc | ✓ | ✓ | 27 |
| **Makine 6** | `3a1debed-c5e4-…bcbf` | 11 | **Mitsubishi** / MitsubishiCnc | ✓ | ✓ | 27 |
| Makine 7 | `3a1d144a-0d22-…ebd0` | 6 | Mitsubishi / MitsubishiCnc | ✓ | ✓ | 30 |
| Makine 8 | `3a1d144a-0eb8-…28de` | 7 | Mitsubishi / MitsubishiCnc | ✓ | ✓ | 30 |
| **TurboCut 400** | `3a1bd958-3763-…b0e9` | — | Nukon / LibPlc (laser) | ✗ | **✗ none** | 0 |
| **ARES SEIKI** | `3a1d1435-0857-…248e16` | — | Fanuc / FanucFocas | ✗ | **✗ none** | 0 |

> **Join trap:** Nightwatch's `reading_def.unit_id` is an **integer** (3–12), joined to `trex_nightwatch_unit.id`, then to MES via `unit_uid`. Don't confuse the integer `id` with the GUID `unit_uid`.

---

## 3. Signal catalog & the cross-domain bridge

### 3.1 MES `reading_def` (312 rows) — signal_type × signal_category
```
                 (blank) PLANNED UNPLANNED
(blank)             158      0        0
STOP                  1     18       35     ← Availability drivers
ALERT_ARRAY           8                     ← Fanuc alarm arrays (RCA)
COUNT                 7                      ← production counters (P)
STOCK_CYCLE          11                      ← ideal cycle time (P baseline)
STOCK_NO             28
WORK_ORDER_NO        12
PROD_ERROR           12
PULSE_COUNT          10                      ← spindle/servo power
TEST_PROD            12
```

### 3.2 Nightwatch `reading_def` (216 rows) — canonical role per vendor (from the signal matrix)
| Role | Fanuc | Mitsubishi (rich) | TurboCut |
|---|---|---|---|
| **Anomaly trigger** | `IsNotRunning`, `ALM_ARR_MSG` | `RUN_STATUS_START__GetRunStartStatus` | `SpeedLevel` errors |
| **Context** | `RUNNING_PROGRAM_NO` | `PROGRAM_POSITION_*` | `StockCode` |
| **Mechanical evidence** | `CYCLE_TIME_MS` | `SERVO_MOTOR_TEMPERATURE_M800__*`, `PATH_LOAD_MODULE__*`, `POWER_CONSUMPTION_M800A_*` | `Mill_N_Work_Time` |
| Production | `PIECES_PRODUCED_TOTAL` | `PIECES_PRODUCED_TOTAL` | counts |

Other numeric signals seen in the sample: `RUN_TIME`, `START_TIME`, `STATINFO_RUN`, `PROGRAM_POSITION_3`, `CYCLE_TIME_M800`, `COMMAND_2`, `NEXT_DISTANCE`.

> **Key implication:** only Mitsubishi machines (4, 6, 7, 8) carry temperature / power / path-load — the signals you need for true multi-signal *baseline-deviation* RCA. Fanuc machines give run-state + cycle time only.

### 3.3 The join (verified)
- `MES reading_def.uid`: 246 distinct signal uids · `NW readingdef_uid`: 162 distinct.
- **Intersection = 162 (100% of Nightwatch).** Every monitored signal resolves to an MES definition (display name, signal_type, category, exclude_from_oee). 84 MES uids are MES-only (event/business signals with no raw telemetry).
- Matched examples: `Undefined Stoppage`, `Manual Stock`, `TCP_WORK_POSITION__GetTCPWorkPosition(2)` line up name-for-name across both catalogs.

**→ Build a canonical "semantic signal layer":** map each `readingdef_uid` to (machine, vendor, canonical_role) using the matrix above. This is the single most important enabling artifact for cross-machine modeling; without it the vendor naming differences make cross-machine learning impossible.

---

## 4. The two challenges, grounded in this data

### 4.1 OEE / What-If (MES)
- **OEE = A × P × Q.** `A = (WorkTotal − PlannedStop − UnPlannedStop)/(WorkTotal − PlannedStop)`; P from `WorkingTime/PlannedTime`; `Q = (ProductSum − ScrapeSum)/ProductSum`. All times **ms**.
- `oee_summary`: 1,917 rows — **1,588 machine-level (level=1)**, 329 plant-level (level=0).
- **Reality check (level=1):** median OEE = 0, median P = 0, `A>0 & P==0` in 532 rows, OEE==0 in 783/1588 (≈49%). Quality `ScrapeSum=0` in 100% of rows.
- **Production is concentrated:** Makine 9 (141,498 pieces) and Makine 3 (108,851) dominate; all others ≤7,200. This is *why* P/OEE collapse for most machines.
- **Work orders:** 9,913 rows, all `is_stock=true` / `is_work_order=false`; `stock_cycle` present on 8,943 (median 222 s, used as the ideal-cycle baseline for P).
- **Strongest, most honest What-If lever:** unplanned-downtime reduction on the two big buckets (`Duruş`, `System Offline`) → recovered hours → ΔA → extra pieces → margin. Cycle-time improvement (P) is the second lever, best demonstrated on Makine 9/3 where pieces actually exist.

### 4.2 Root Cause Analysis (Machine Monitoring)
- **Anomaly sources:** unplanned `stoppage_slice` (32,092 unplanned slices), `mes_alert` (77, only Makine 1/2), `mes_status` offline intervals, P-drops in `oee_summary`.
- **Top unplanned downtime (verified):**
  | Reason | Events | Hours |
  |---|---|---|
  | `Duruş` (IsNotRunning) | 28,143 | 19,191 |
  | `System Offline` | 3,948 | 14,901 |
  - Per machine (unplanned h): TurboCut 7,653 · Makine 8 5,075 · Makine 7 4,720 · Makine 1 4,063 · Makine 3 2,824 · Makine 9 2,804 · Makine 5 2,652 · others <1,800.
- **Planned downtime:** `İş Bekliyor` (waiting for work, 8,626 h), `Magazin takım değişimi` (tool change, 914 h). Plus `stoppage_def` lookups: Dış Ayar, Sevkiyat, Yemek Molası (lunch, 30 min), Çay Molası (tea, 15 min).
- **Top alarms (Makine 1/2 only):** `EMERGENCY STOP.` (25), `Z AXIS NEED ZERO RETURN!` (15), `AIR PRESSURE FAILED!` (10), `CHUCK UNCLAMP.` (8), `DOOR INTERLOCK ALARM.` (4), `LUBE OIL LAST.` (3), overtravel/motor-overload singletons.
- **String telemetry** carries program names (`70KARİZMAKAPI`) and Turkish fault/log text (`ÇIKIŞ PROFIL TUTMA HATASI`, `KUMANDA PANELI ACIL STOP BASILI`). Note: some string `readingdef_uid`s did not resolve to a name in the catalog sample — string signals need a tolerant lookup.

---

## 5. Data-quality gotchas (bake these into every loader)

| # | Gotcha | Consequence / fix |
|---|---|---|
| 1 | **cp1254 encoding** | `read_csv(..., encoding="cp1254")`. UTF-8 throws on Turkish bytes. |
| 2 | **Booleans are `'t'`/`'f'` strings** | Map to bool explicitly; `== False` matches nothing. |
| 3 | **All durations in ms** | Divide by 3.6e6 for hours; 6e4 for minutes. |
| 4 | **Stored OEE/A is noisy** | `A<0` in 12 rows, OEE min −64. Recompute A/P/Q from JSON components. |
| 5 | **NW `unit_id` is integer** | `data.readingdef_uid → reading_def.unit_id → nightwatch_unit.id → unit_uid`. |
| 6 | **CSV quoting artifacts** | A timestamp leaked into `external_signal_type` for ~4 NW reading_def rows; alarm text has embedded newlines (90 lines → 77 alert rows). Use a quote-aware parser (pandas C engine ok). |
| 7 | **6M+ telemetry rows** | Never full-scan; filter by `time` + `readingdef_uid` (+ machine) always. Parts are roughly chronological (part 001 ≈ Aug–Oct 2025). |
| 8 | **Q = 1, P often 0** | Quality scenarios are simulated; OEE ≈ 0 for most days. |
| 9 | **2 machines, 0 telemetry** | TurboCut & ARES SEIKI: MES-only RCA. |
| 10 | **`exclude_from_oee` / `is_test_prod`** | All `f` in this dump, but keep the filter for correctness. |

---

## 6. Assessment of the proposed workflow

> **Proposed:** Transformer anomaly detection → RCA on detected anomalies → What-If → OEE-increase quantification. Best target: detect deviations from baseline, stack multiple signals, apply cross-machine.

**Verdict:** the *narrative* is exactly right and maps onto the judging ladder (Bronze→Platinum, where Platinum = cross-machine pattern + quantified OEE + financial recommendation). But three data realities should reshape the *execution*:

### Keep
- **AD → RCA → What-If → OEE/€ chain.** This is the winning story and directly satisfies "Platinum."
- **Baseline-deviation + multi-signal stacking** as the core RCA technique — the docs and decks explicitly reward it.
- **Cross-machine ambition** — enabled by the 100% `reading_def_uid` join.

### Change
1. **Don't lead with a transformer; lead with the semantic signal layer + simple, explainable baselines.** Most "anomalies" are *already labeled* by MES (unplanned stoppage, alert, offline). A blind unsupervised transformer risks re-discovering what's already in `stoppage_slice`. Start with per-signal robust control charts (rolling median/IQR, EWMA, STL residuals) — fast, interpretable (judges reward explainable RCA), and they double as features. Reserve a transformer/autoencoder for the *genuinely valuable* job: **multivariate leading-indicator detection** (e.g., servo temp / spindle power drifting *before* an alarm) on the data-rich Mitsubishi machines.
2. **Use reconstruction, not forecasting.** For multivariate residual AD prefer an autoencoder / PatchTST-style reconstruction over a next-step forecaster — the goal is "this window doesn't look like normal operation," not precise prediction. Only deploy it where signal density supports it (Mitsubishi 4/6/7/8).
3. **Recompute OEE from JSON components** rather than trusting scalar columns (see §5.4) — otherwise What-If deltas inherit the noise.

### Add (scope decisions you must make explicitly)
1. **Tier the machines by evidence available** — and say so in the deliverable:
   - **Rich (Mitsubishi 4/6/7/8):** full multi-signal baseline-deviation RCA (temp/power/load). This is where the transformer earns its place.
   - **Sparse (Fanuc 1/2/3/5/9/10):** run-state + cycle-time + alarms (1/2 only). Mostly event-correlation RCA.
   - **Blind (TurboCut, ARES):** MES-only — stop/counter/workorder/string logs. **TurboCut is your biggest downtime sink yet has no telemetry** — call this out; it's a strong finding, not a gap to hide.
2. **Separate connectivity faults from machine faults first.** ~14,900 h of "System Offline" is a collector/network problem with no telemetry to explain. Cross-check `trex_mes_status.is_online`. A model that tries to "explain" offline from sensors will fail by construction.
3. **Scope alarm-driven RCA to Makine 1 & 2.** They hold all 77 alerts (Air Pressure, Z-axis, Emergency Stop, Door Interlock). Build the flagship causal-chain demo here (the AIR PRESSURE → Z-AXIS cascade is the canonical example in the docs), and use stop-pattern + telemetry deviation for the rest.

### Recommended sequencing
```
0. Loaders w/ gotchas baked in (cp1254, 't'/'f', ms, recompute OEE)        [foundation]
1. Semantic signal layer: readingdef_uid → (machine, vendor, canonical_role) [enabler]
2. Per-signal normal-operating-envelope baselines per machine                [EDA → AD backbone]
3. Statistical AD (control charts / residuals) — explainable, cross-machine  [Silver/Gold]
4. RCA engine: align alert+stop+status+telemetry in [-15m,+5m]; ALERT_ARRAY
   cascade logic; cross-machine recurrence (systemic faults)                 [Gold]
5. Transformer/AE multivariate leading-indicator detector (Mitsubishi only)  [Gold+, optional]
6. What-If: recomputed-OEE engine; downtime-reduction (A) & cycle-time (P)
   scenarios; financial layer with clearly-labeled assumptions              [Platinum]
7. Cross-machine pattern report + quantified ΔOEE + €/payback recommendation [Platinum]
```

### Cross-machine, concretely
The phrase "apply this cross-machines" is feasible **only through the canonical role layer**: a model/control-chart that reasons over `{run_state, cycle_time, spindle_power, servo_temp, path_load, program_no}` rather than vendor-specific names. Two cross-machine wins are well-supported by the data: (a) **same alarm/stop pattern across machines = systemic fault** (facility air, power, network) — e.g. correlate `AIR PRESSURE FAILED` / `EMERGENCY STOP` and `System Offline` across units; (b) **transfer a normal-envelope model** from data-rich to data-sparse machines for the few shared signals (run-state, cycle time).

---

## 7. Suggested next steps
1. Lock the loaders + semantic signal map (§3.3, §5).
2. Build the recomputed OEE baseline table (per machine/day) and a downtime Pareto — these feed both challenges.
3. Prototype the RCA event-timeline on **Makine 1, AIR PRESSURE FAILED** (canonical case) end-to-end before scaling.
4. Decide transformer scope after seeing whether statistical baselines already deliver the leading-indicator story on Mitsubishi.
```
```
