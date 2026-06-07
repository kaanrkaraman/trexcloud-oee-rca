"""Push the Fanuc stop-predictor as far as it honestly goes.

Config under study = the winner from 05_REGIME_MODELS: Fanuc {1,2,3,5,9}, per-machine robust
z-norm, HistGBDT. We layer three improvements and measure each on the SAME held-out future:
  (1) baseline  — current default params, base features
  (2) +features — cheap derived features (deviations, ratios, cyclical hour) from existing cols
  (3) +tuned    — randomized hyperparameter search

LEAKAGE CONTROL (the whole point):
  - outer split: per-machine chronological train(0.6)/test(0.4). TEST IS TOUCHED ONCE, at the end.
  - hyperparameters are selected ONLY on an inner chronological validation carved from train
    (last 25% of the train period). No shuffled k-fold (would leak across time & machines).
  - z-norm stats are recomputed from the relevant *training* rows at every level (no test stats).

Run: uv run python scripts/tune_fanuc.py
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (average_precision_score, roc_auc_score, f1_score,
                             precision_score, recall_score, precision_recall_curve)
from trex import predict

ART = Path("analysis/artifacts"); REP = Path("analysis/reports")
FANUC = ["Makine 1", "Makine 2", "Makine 3", "Makine 5", "Makine 9"]
TELE_KEYS = ("cycle_time", "run_state", "run_time", "axis_move", "machine_mode", "production")
RNG = np.random.default_rng(0)
HORIZON, MINSTOP = 60, 15


def chrono_split(df, frac):
    tr, te = [], []
    for _, g in df.groupby("machine"):
        g = g.sort_values("ts"); k = int(len(g) * frac)
        tr.append(g.iloc[:k]); te.append(g.iloc[k:])
    return pd.concat(tr).reset_index(drop=True), pd.concat(te).reset_index(drop=True)


def znorm(train, test, cols):
    """per-machine robust z (median/IQR from TRAIN only)."""
    tele = [c for c in cols if any(k in c for k in TELE_KEYS)]
    tr, te = train.copy(), test.copy()
    for m in tr.machine.unique():
        gtr = tr.machine == m
        for c in tele:
            med = tr.loc[gtr, c].median()
            iqr = (tr.loc[gtr, c].quantile(.75) - tr.loc[gtr, c].quantile(.25)) or 1.0
            if pd.notna(med):
                tr.loc[gtr, c] = (tr.loc[gtr, c] - med) / iqr
                gte = te.machine == m
                te.loc[gte, c] = (te.loc[gte, c] - med) / iqr
    return tr, te


def augment(df):
    """derive cheap features from existing columns (no telemetry re-read, no future info)."""
    d = df.copy()
    def safe(a, b):
        return d[a] - d[b] if a in d and b in d else 0.0
    # deviation of current value from its own long-run mean (per-bucket anomaly)
    d["cycle_dev"] = safe("cycle_time_mean", "cycle_time_mean__long_mean")
    d["runstate_dev"] = safe("run_state_duty", "run_state_duty__long_mean")
    d["prod_dev"] = safe("production_count_delta", "production_count_delta__long_mean")
    # short vs long ratio (regime shift)
    if "cycle_time_mean__roll_mean" in d and "cycle_time_mean__long_mean" in d:
        d["cycle_short_long"] = d["cycle_time_mean__roll_mean"] / (
            d["cycle_time_mean__long_mean"].replace(0, np.nan))
    # stop-pressure interactions
    if "sigstop_cnt_4h" in d and "downtime_min_4h" in d:
        d["stop_pressure"] = d["sigstop_cnt_4h"] * np.log1p(d["downtime_min_4h"])
    if "micro_cnt_1h" in d and "micro_cnt_4h" in d:
        d["micro_accel"] = d["micro_cnt_1h"] - d["micro_cnt_4h"] / 4.0   # rising micro-stops
    # cyclical hour + shift flag (shift boundary 21:00 UTC-ish)
    if "hour" in d:
        d["hour_sin"] = np.sin(2 * np.pi * d["hour"] / 24)
        d["hour_cos"] = np.cos(2 * np.pi * d["hour"] / 24)
    new = ["cycle_dev", "runstate_dev", "prod_dev", "cycle_short_long", "stop_pressure",
           "micro_accel", "hour_sin", "hour_cos"]
    return d, [c for c in new if c in d]


def metrics(y, p):
    base = float(y.mean())
    ap = average_precision_score(y, p); roc = roc_auc_score(y, p)
    prec, rec, th = precision_recall_curve(y, p)
    f1s = np.divide(2 * prec * rec, prec + rec, out=np.zeros_like(prec), where=(prec + rec) > 0)
    t = float(th[max(0, np.argmax(f1s) - 1)]) if len(th) else 0.5
    yhat = (p >= t).astype(int)
    return {"base_rate": round(base, 4), "ROC_AUC": round(roc, 4), "PR_AUC": round(ap, 4),
            "lift": round(ap / base, 2), "F1": round(f1_score(y, yhat, zero_division=0), 4),
            "precision": round(precision_score(y, yhat, zero_division=0), 4),
            "recall": round(recall_score(y, yhat, zero_division=0), 4)}


def fit_eval(tr, te, feats, params):
    trz, tez = znorm(tr, te, feats)
    m = HistGradientBoostingClassifier(random_state=0, **params)
    m.fit(trz[feats].to_numpy(float), trz["y"].to_numpy())
    p = m.predict_proba(tez[feats].to_numpy(float))[:, 1]
    return metrics(tez["y"].to_numpy(), p), p


DEFAULT = dict(max_iter=350, learning_rate=0.07, l2_regularization=1.0, max_depth=8)

SPACE = {
    "learning_rate": [0.02, 0.03, 0.05, 0.07, 0.1],
    "max_iter": [300, 500, 700, 900],
    "max_leaf_nodes": [15, 31, 63, 127],
    "min_samples_leaf": [20, 50, 100, 200, 400],
    "l2_regularization": [0.0, 0.5, 1.0, 2.0, 5.0],
    "max_features": [0.5, 0.7, 0.9, 1.0],
    "class_weight": [None, "balanced"],
}


def sample_params():
    return {k: SPACE[k][RNG.integers(len(SPACE[k]))] for k in SPACE}


def main():
    print("building Fanuc supervised dataset…")
    data, base_feat = predict.build_supervised(horizon_min=HORIZON, min_stop_min=MINSTOP)
    data = data[data.machine.isin(FANUC)].reset_index(drop=True)
    # drop columns that are entirely NaN for the Fanuc subset (Mitsubishi-only roles)
    base_feat = [c for c in base_feat if data[c].notna().any()]
    data, new_feat = augment(data)
    data[new_feat] = data[new_feat].replace([np.inf, -np.inf], np.nan)
    new_feat = [c for c in new_feat if data[c].notna().any()]
    aug_feat = base_feat + new_feat

    outer_tr, outer_te = chrono_split(data, 0.6)
    print(f"outer train={len(outer_tr):,}  test={len(outer_te):,}  "
          f"base feats={len(base_feat)}  +aug={len(new_feat)}")

    results = {}
    print("\n[1] baseline (default params, base features)…")
    results["baseline"], _ = fit_eval(outer_tr, outer_te, base_feat, DEFAULT)
    print("    ", results["baseline"])

    print("[2] +features (default params, augmented features)…")
    results["plus_features"], _ = fit_eval(outer_tr, outer_te, aug_feat, DEFAULT)
    print("    ", results["plus_features"])

    print("[3] hyperparameter search on INNER chronological validation (no test peeking)…")
    inner_tr, inner_val = chrono_split(outer_tr, 0.75)
    trz, valz = znorm(inner_tr, inner_val, aug_feat)
    Xtr, ytr = trz[aug_feat].to_numpy(float), trz["y"].to_numpy()
    Xv, yv = valz[aug_feat].to_numpy(float), valz["y"].to_numpy()
    N_TRIALS = 40
    trials = []
    # include the current default as a baseline candidate
    cand = [DEFAULT | {"max_leaf_nodes": None}] + [sample_params() for _ in range(N_TRIALS)]
    for i, params in enumerate(cand):
        m = HistGradientBoostingClassifier(random_state=0, **params)
        m.fit(Xtr, ytr)
        pv = m.predict_proba(Xv)[:, 1]
        s = average_precision_score(yv, pv)
        trials.append((s, params))
        if (i + 1) % 10 == 0 or i == 0:
            print(f"    trial {i+1}/{len(cand)}  best inner PR-AUC so far={max(t[0] for t in trials):.4f}")
    trials.sort(key=lambda t: t[0], reverse=True)
    best_inner, best_params = trials[0]
    print(f"    best inner PR-AUC={best_inner:.4f}  params={best_params}")

    print("[4] refit best on FULL train, evaluate ONCE on held-out test…")
    results["plus_tuned"], _ = fit_eval(outer_tr, outer_te, aug_feat, best_params)
    print("    ", results["plus_tuned"])

    out = {"config": "Fanuc {1,2,3,5,9}, per-machine z-norm, HistGBDT",
           "n_outer_train": len(outer_tr), "n_outer_test": len(outer_te),
           "default_params": DEFAULT, "best_params": best_params,
           "best_inner_pr_auc": round(float(best_inner), 4),
           "n_search_trials": len(cand), "stages": results}
    (ART / "fanuc_tuning_metrics.json").write_text(json.dumps(out, indent=2, default=str))
    _report(out)
    print("\nwrote fanuc_tuning_metrics.json + 06_FANUC_TUNING.md")


def _report(o):
    s = o["stages"]; b, f, t = s["baseline"], s["plus_features"], s["plus_tuned"]
    def row(name, m):
        return (f"| {name} | {m['ROC_AUC']} | {m['PR_AUC']} | {m['lift']} | {m['F1']} | "
                f"{m['precision']} | {m['recall']} |")
    L = ["# trexCloud — Fanuc Stop-Predictor Tuning (honest, leakage-safe)\n",
         f"**Config:** {o['config']}. Outer split per-machine chronological "
         f"(train {o['n_outer_train']:,} / test {o['n_outer_test']:,}). Hyperparameters chosen "
         "ONLY on an inner chronological validation; the test set is evaluated once per stage.\n",
         "| stage | ROC-AUC | PR-AUC | lift | F1 | precision | recall |",
         "|---|--:|--:|--:|--:|--:|--:|",
         row("baseline (default, base features)", b),
         row("+ derived features", f),
         row("+ tuned hyperparameters", t), ""]
    d_roc = round(t["ROC_AUC"] - b["ROC_AUC"], 4); d_lift = round(t["lift"] - b["lift"], 2)
    L += [f"**Net improvement: ROC {b['ROC_AUC']} → {t['ROC_AUC']} ({d_roc:+.4f}), "
          f"lift {b['lift']} → {t['lift']} ({d_lift:+.2f}).**\n",
          f"- Best params (selected on inner validation, inner PR-AUC "
          f"{o['best_inner_pr_auc']}): `{o['best_params']}`",
          f"- Search: {o['n_search_trials']} randomized trials over learning_rate, max_iter, "
          "max_leaf_nodes, min_samples_leaf, l2, max_features, class_weight.\n",
          "## Honest reading\n",
          "- Gains from tuning a tree are expected to be modest; the derived features and the "
          "per-machine normalization typically matter more. The table shows where the gain "
          "actually came from.",
          "- All numbers are on the **untouched future test set**; the search never saw it, so "
          "this is a real out-of-sample estimate, not an optimistic in-sample one.",
          "- The ceiling is still set by data, not model: the mechanical-evidence signals "
          "(servo temp / path-load) are empty, so we predict from cycle-time / run-state / "
          "stop-dynamics only. A bigger jump would require either those signals (not in this "
          "dump) or a different target (shorter horizon, time-to-stop regression).\n"]
    (REP / "06_FANUC_TUNING.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
