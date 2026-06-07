# trexCloud — Cross-Machine Pattern Detection (honest method audit)

Replaces naive co-occurrence binning with null-model-backed detectors. Every claim states what would also fire by chance or by shared schedule.

## 0. The old method was a tautology

`recurrence.find_recurrence` ranks **CONNECTIVITY at rank 0** — but that is a single instance-level *System Offline* row fanned out to every machine on the same `instance_id` (identical start/end). It is systemic *by construction*, not detected. It also has **no null model**, so chance co-occurrence scores as 'systemic'.

## 1. Synchronization of significant unplanned stops (≥15 min)

- Observed 1-h windows with ≥2 machines co-initiating a significant stop: **708** (of 708 multi-stop windows).
- **Free-shift null** (any alignment): exp 332.7±46.6 → **z=+8.05, p=0.000**.
- **Daily-preserving null** (keeps each machine's hour-of-day, tests alignment BEYOND shared shift rhythm): exp 563.9±27.9 → **z=+5.16, p=0.000**.
- Hour-of-day concentration: top-3 hours hold **43%** of co-stops (busiest UTC hours [14, 9, 12]).
- Reason granularity: **1 distinct reason(s)** for all significant unplanned stops → same-reason concordance is **VACUOUS — single generic label, no reason granularity**. The MES stop stream cannot corroborate a shared root; only the alarm stream (Makine 1 & 2 only) or telemetry can.

> Interpretation: synchronization beyond chance is **confirmed**. The daily-preserving null controls for each machine's hour-of-day rhythm, so the residual is not 'everyone breaks at shift change'. **Caveat:** it does *not* control for shared weekly / production-campaign scheduling (machines busy the same weeks), so part of the residual may be a shared production calendar rather than acute facility events. With only one stop reason (`Duruş`) the MES data cannot resolve which.

## 2. Anomaly-score coupling (which machines move together)

- **Levels** (running-only): median pairwise r = **-0.029** (most pairs independent), max r = **+0.907**; cluster at r≥0.5 = **[['Makine 1', 'Makine 2', 'Makine 3', 'Makine 9']]** (selective — Makine 5 is same regime but anti-correlates).
- **Detrended** (first-difference, event timescale): median r = **+0.020**, max r = **+0.134**, cluster = **NONE**.

> **Honest reading:** the cluster exists only in *levels*, and collapses to ~0 once detrended. So {Makine 1,2,3,9} share a **slow common envelope** (a multi-week operating / load rhythm), but they do **NOT** spike together — this is a shared operating regime, **not** fault propagation or synchronized acute anomalies. Claiming the latter would be false.

## 3. Data-regime / comparability map (can we even model cross-machine?)

Derived from feature availability, not the vendor catalog:

| regime (shared streaming roles) | machines |
|---|---|
| cycle_time_mean, run_state_duty, production_count_delta | Makine 1, Makine 2, Makine 3, Makine 5, Makine 9 |
| cycle_time_mean, run_state_duty, run_time_delta, axis_move_total | Makine 7 |
| run_state_duty, run_time_delta, axis_move_total | Makine 8 |
| (blind) | ARES SEIKI  (Fanuc), Makine 10, Makine 4, Makine 6, TurboCut 400 |

**Shared-role comparability (raw scale):**

| role | machines | median min | median max | spread |
|---|--:|--:|--:|--:|
| cycle_time_mean | 6 | 123113 | 1003918 | 8.2× |
| run_state_duty | 7 | 0 | 1 | 2.0× |
| run_time_delta | 2 | 120000 | 120000 | 1.0× |

> Vendor families share almost no feature columns; even the shared `cycle_time` spans several-× in scale → cross-machine modeling is valid only **within a regime, after per-machine normalization**. A single pooled feature matrix is half-empty.
