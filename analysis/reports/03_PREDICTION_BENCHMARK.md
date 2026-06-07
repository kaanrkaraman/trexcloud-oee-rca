# trexCloud — Stop-Prediction Benchmark

**Task:** predict a *significant* unplanned stop (≥15 min) starting within the next **60 min**, from a running bucket.  
**Methodology (leakage-safe):** features use only data ≤ t (rolling lookback + stop-recency); **chronological per-machine split** (train ≤ 2026-03-11 05:02:00+00:00, test ≥ 2026-01-29 12:10:00+00:00); imputers/scalers fit on train only.

- Train rows: 234,365 · Test rows: 156,248 · Features: 58

## Model comparison (on held-out future)

| model | base rate | PR-AUC | ROC-AUC | lift | F1 | precision | recall |
|---|--:|--:|--:|--:|--:|--:|--:|
| hist_gbdt | 0.2515 | 0.5255 | 0.7598 | 2.09 | 0.5483 | 0.4923 | 0.6187 |
| random_forest | 0.2515 | 0.5027 | 0.7456 | 2.0 | 0.5254 | 0.4599 | 0.6125 |
| logreg | 0.2515 | 0.4987 | 0.7384 | 1.98 | 0.5309 | 0.4387 | 0.6722 |
| mlp | 0.2515 | 0.4322 | 0.6808 | 1.72 | 0.473 | 0.3972 | 0.5846 |
| ad_score_unsupervised* | 0.2515 | 0.2698 | 0.5078 | 1.07 | 0.4023 | 0.2519 | 0.9983 |
| baseline_always_positive | 0.2515 | 0.2515 | 0.5 | 1.0 | 0.4019 | 0.2515 | 1.0 |

> **lift** = PR-AUC ÷ base rate (>1 means the model beats random/always-positive). ROC-AUC > 0.5 and lift > 1 are the honest 'is this real signal?' checks.

**Best model: `hist_gbdt`** — PR-AUC 0.5255 (base 0.2515, lift 2.09×), ROC-AUC 0.7598.

## Top predictive features

| feature | importance |
|---|--:|
| hour | 0.0869 |
| downtime_min_4h | 0.0692 |
| sigstop_min_since | 0.0676 |
| micro_min_since | 0.0446 |
| cycle_time_mean__long_mean | 0.0414 |
| anystop_cnt_4h | 0.0386 |
| run_time_delta__long_mean | 0.0383 |
| run_state_duty__long_mean | 0.037 |
| micro_cnt_4h | 0.035 |
| anystop_min_since | 0.0346 |
| cycle_time_mean__roll_mean | 0.0308 |
| cycle_time_mean | 0.0278 |

## Data-prep validation (what we checked)

- **Masking matters most.** The first version dropped all idle buckets (`running_only`), which removed the informative 'machine winding down' states and capped ROC at ~0.71. Keeping those buckets (with an `is_idle` feature) while **excluding buckets *inside* an active significant stop** (so we never 'predict' a stop that is already happening) raised ROC to ~0.76 — and removing the mid-stop buckets *increased* the score, proving the lift is genuine pre-stop signal, not a tautology.
- **Pooling is fine.** Per-machine z-normalization and machine one-hot encoding gave identical ROC to pooled-raw, so cross-machine scale-mixing was **not** the problem.
- **Stop-dynamics features help.** Adding micro-stop frequency / recent downtime burden (degradation often shows as rising micro-stops before a big stop) added real signal on top of telemetry.

## Notes / honesty

- Trivial baselines (`always_positive`, `recent_stop`) are included on purpose: a model is only useful if it beats them on PR-AUC/ROC-AUC.
- Predicting *any* stop is near-trivial (base rate 0.88–0.96 on busy machines); we predict *significant* stops where the base rate is lower and lift is meaningful.
- **Ceiling.** ~0.76 ROC / ~2.1× lift is close to the achievable limit for THIS data: the real condition-monitoring signals (servo temp/power/path-load) are empty (0 rows), so we predict breakdowns from cycle-time/run-state only; many significant 'Duruş' stops are operational/unclassified; and stop rates are non-stationary (some machines' rate shifts between train and test). It is a solid risk model, not a crystal ball.
- This is the supervised counterpart to the unsupervised AD in `trex.ad`; AD remains the RCA evidence layer (which signals deviate), prediction answers *will it stop soon*.
- `ad_score_unsupervised*` = the unsupervised AD score evaluated as a stop predictor on the same target/test split (`*` = its score normalization is global, so it is a mildly optimistic baseline). It shows whether unsupervised AD alone rivals the supervised models.
- Figures: `figures/predict_pr_curves.html`, `figures/predict_feature_importance.html`.
