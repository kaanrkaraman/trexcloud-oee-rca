# trexCloud — Regime Modeling: merge vs split (honest comparison)

**Question.** The signal matrix aligns Fanuc and Mitsubishi by *role* (`IsNotRunning`↔`RUN_STATUS_START`, `CYCLE_TIME_MS`↔`CYCLE_TIME_M800`). Does that let us merge {1,2,3,5,9} and {7,8} into one model that beats per-regime models?

**What can actually be merged.** Only the *roles* align, not the streamed signals. The dense shared features are `run_state` + the vendor-agnostic stop-dynamics (stop recency/frequency, micro-stop burden) + hour. Fanuc's `cycle_time`/`production` and Mitsubishi's `run_time`/`axis_position` do **not** overlap and ride along as NaN.

**Base rates differ sharply** — Fanuc 0.10–0.20 vs Mitsubishi 0.54–0.59 — so these are almost different problems. ROC-AUC and lift (PR-AUC÷base) are the fair metrics; raw PR-AUC just tracks the base rate.

## A. Each regime, own model on own test (HistGBDT)

| test set | base | ROC-AUC | PR-AUC | lift | n_test |
|---|--:|--:|--:|--:|--:|
| merged | 0.2515 | 0.7598 | 0.5255 | 2.09 | 156,248 |
| fanuc | 0.1789 | 0.6856 | 0.3688 | 2.06 | 124,047 |
| mits | 0.5312 | 0.6299 | 0.6426 | 1.21 | 32,201 |

## B. Does merging help? (same test rows, HistGBDT)

| test set | trained on | ROC-AUC | PR-AUC | lift | F1 |
|---|---|--:|--:|--:|--:|
| fanuc | merged | 0.698 | 0.3832 | 2.14 | 0.406 |
| fanuc | fanuc | 0.6856 | 0.3688 | 2.06 | 0.3952 |
| mits | merged | 0.6162 | 0.638 | 1.2 | 0.6978 |
| mits | mits | 0.6299 | 0.6426 | 1.21 | 0.6982 |

**Fanuc test:** merged ROC 0.698 vs Fanuc-only 0.6856 (Δ +0.0124). **Mitsubishi test:** merged ROC 0.6162 vs Mits-only 0.6299 (Δ -0.0137).

## C. Per-machine z-norm (signal-scale alignment), HistGBDT + logreg

| test set | model | ROC-AUC | PR-AUC | lift |
|---|---|--:|--:|--:|
| fanuc | hist_gbdt | 0.7208 | 0.4174 | 2.33 |
| fanuc | logreg | 0.6686 | 0.3067 | 1.71 |
| mits | hist_gbdt | 0.6257 | 0.6458 | 1.22 |
| mits | logreg | 0.6016 | 0.6186 | 1.16 |

## Verdict (the truth)

- **Raw merge is a wash:** it *helps* Fanuc (ROC +0.0124, more data on shared features) and *hurts* Mitsubishi (ROC -0.0137, base-rate dilution) — both small.
- **Per-machine z-norm is the real win, and it is what makes the single merged model best.** Merged+z-norm HistGBDT beats the Fanuc-only model by ROC +0.0352 (0.686→0.7208, lift→2.33) and ties the Mits-only model on Mitsubishi (ROC -0.0042). So a **single model over the merged group, with per-machine normalization, is the recommended solution** — simpler AND better.
- **I was wrong earlier that z-norm can't move a tree.** Per-machine z-norm is NOT a global monotonic transform — it aligns each feature onto a per-machine scale, so one split threshold (`cycle_time is high *for this machine*`) generalizes across machines. That is exactly the cross-machine scale-mixing the matrix warned about, and fixing it is the single biggest gain in this experiment.
- **The 0.76 'pooled' ROC was partly inflated by base-rate heterogeneity.** Honest within-regime predictive power is ROC ~0.69→0.72 (Fanuc) and ~0.63 (Mitsubishi); the pooled 0.76 partly reflects the model telling a Mitsubishi bucket (base 0.53) from a Fanuc bucket (base 0.18), not stop-from-no-stop within a machine.
- **Mitsubishi {7,8} barely beat their base rate (lift ~1.2).** They stop significantly >50% of any 60-min window, so 'will it stop' is nearly always yes — 60-min significant-stop prediction is near-saturated there; a shorter horizon or time-to-stop regression would suit them better.
