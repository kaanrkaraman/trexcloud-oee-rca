# trexCloud — Fanuc Stop-Predictor Tuning (honest, leakage-safe)

**Config:** Fanuc {1,2,3,5,9}, per-machine z-norm, HistGBDT. Outer split per-machine chronological (train 186,066 / test 124,047). Hyperparameters chosen ONLY on an inner chronological validation; the test set is evaluated once per stage.

| stage | ROC-AUC | PR-AUC | lift | F1 | precision | recall |
|---|--:|--:|--:|--:|--:|--:|
| baseline (default, base features) | 0.7143 | 0.4141 | 2.31 | 0.4216 | 0.3242 | 0.6026 |
| + derived features | 0.7137 | 0.4105 | 2.29 | 0.426 | 0.3475 | 0.5502 |
| + tuned hyperparameters | 0.7311 | 0.4263 | 2.38 | 0.4463 | 0.3795 | 0.5418 |

**Net improvement: ROC 0.7143 → 0.7311 (+0.0168), lift 2.31 → 2.38 (+0.07).**

- Best params (selected on inner validation, inner PR-AUC 0.3738): `{'learning_rate': 0.02, 'max_iter': 300, 'max_leaf_nodes': 15, 'min_samples_leaf': 200, 'l2_regularization': 1.0, 'max_features': 0.9, 'class_weight': None}`
- Search: 41 randomized trials over learning_rate, max_iter, max_leaf_nodes, min_samples_leaf, l2, max_features, class_weight.

## Honest reading

- Gains from tuning a tree are expected to be modest; the derived features and the per-machine normalization typically matter more. The table shows where the gain actually came from.
- All numbers are on the **untouched future test set**; the search never saw it, so this is a real out-of-sample estimate, not an optimistic in-sample one.
- The ceiling is still set by data, not model: the mechanical-evidence signals (servo temp / path-load) are empty, so we predict from cycle-time / run-state / stop-dynamics only. A bigger jump would require either those signals (not in this dump) or a different target (shorter horizon, time-to-stop regression).
