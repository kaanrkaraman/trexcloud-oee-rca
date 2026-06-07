"""Leakage-safe model comparison for stop prediction.

Chronological per-machine split (train = earliest train_frac, test = latest). Preprocessors
fit on train only. Compares model families + trivial baselines on the SAME held-out future,
reporting classical metrics and lift over the base rate.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (average_precision_score, roc_auc_score, f1_score,
                             precision_score, recall_score, confusion_matrix,
                             precision_recall_curve)


def make_models():
    return {
        "logreg": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                LogisticRegression(max_iter=1000, class_weight="balanced")),
        "random_forest": make_pipeline(SimpleImputer(strategy="median"),
                                       RandomForestClassifier(n_estimators=120, n_jobs=-1,
                                                              class_weight="balanced_subsample",
                                                              random_state=0)),
        "hist_gbdt": HistGradientBoostingClassifier(max_iter=350, learning_rate=0.07,
                                                    l2_regularization=1.0, max_depth=8,
                                                    random_state=0),  # handles NaN natively
        "mlp": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             MLPClassifier(hidden_layer_sizes=(64, 24), max_iter=300,
                                           early_stopping=True, random_state=0)),
    }


def time_split(data: pd.DataFrame, *, train_frac=0.6):
    """Per-machine chronological split (no shuffle): earliest train_frac -> train."""
    tr, te = [], []
    for m, g in data.groupby("machine"):
        g = g.sort_values("ts")
        k = int(len(g) * train_frac)
        tr.append(g.iloc[:k]); te.append(g.iloc[k:])
    return (pd.concat(tr).reset_index(drop=True),
            pd.concat(te).reset_index(drop=True))


def _metrics(name, y, p, *, thresh=None):
    base = float(np.mean(y))
    ap = average_precision_score(y, p) if y.sum() else np.nan
    try:
        roc = roc_auc_score(y, p) if 0 < y.sum() < len(y) else np.nan
    except ValueError:
        roc = np.nan
    # operating point = threshold maximizing F1 on this set
    if thresh is None and len(set(np.round(p, 6))) > 1 and y.sum():
        prec, rec, th = precision_recall_curve(y, p)
        f1s = np.divide(2 * prec * rec, prec + rec, out=np.zeros_like(prec), where=(prec + rec) > 0)
        thresh = float(th[max(0, np.argmax(f1s) - 1)]) if len(th) else 0.5
    thresh = 0.5 if thresh is None else thresh
    yhat = (p >= thresh).astype(int)
    cm = confusion_matrix(y, yhat, labels=[0, 1]).tolist()
    return {"model": name, "base_rate": round(base, 4), "PR_AUC": round(float(ap), 4),
            "ROC_AUC": round(float(roc), 4),
            "lift_PRAUC_over_base": round(float(ap) / base, 2) if base else np.nan,
            "F1": round(f1_score(y, yhat, zero_division=0), 4),
            "precision": round(precision_score(y, yhat, zero_division=0), 4),
            "recall": round(recall_score(y, yhat, zero_division=0), 4),
            "threshold": round(float(thresh), 4), "confusion_tn_fp_fn_tp": cm}


def run_benchmark(data: pd.DataFrame, feat_cols, *, train_frac=0.6):
    train, test = time_split(data, train_frac=train_frac)
    Xtr, ytr = train[feat_cols].to_numpy(float), train["y"].to_numpy()
    Xte, yte = test[feat_cols].to_numpy(float), test["y"].to_numpy()

    results, curves = [], {}

    # trivial baselines (no training)
    # always-positive: constant score 1
    results.append(_metrics("baseline_always_positive", yte, np.ones(len(yte)), thresh=0.5))
    # recent-stop persistence: more/closer recent stops -> higher risk
    if "stops_last_1h" in feat_cols:
        rs = test["stops_last_1h"].to_numpy(float)
        rs = rs / (rs.max() or 1)
        results.append(_metrics("baseline_recent_stop", yte, np.nan_to_num(rs)))
        curves["baseline_recent_stop"] = (yte, np.nan_to_num(rs))

    for name, model in make_models().items():
        model.fit(Xtr, ytr)
        p = model.predict_proba(Xte)[:, 1]
        results.append(_metrics(name, yte, p))
        curves[name] = (yte, p)
        if name == "hist_gbdt":
            # permutation-free importance proxy: use train gain via feature_importances if present
            pass

    res = pd.DataFrame(results).sort_values("PR_AUC", ascending=False).reset_index(drop=True)
    meta = {"n_train": int(len(train)), "n_test": int(len(test)),
            "train_end": str(train.ts.max()), "test_start": str(test.ts.min()),
            "features": feat_cols, "n_features": len(feat_cols)}
    return res, curves, meta, (test, {n: m for n, m in make_models().items()})


def feature_importance(data, feat_cols, *, train_frac=0.6, top=15):
    """Quick RF importance (fit on train) for interpretability."""
    train, _ = time_split(data, train_frac=train_frac)
    rf = make_pipeline(SimpleImputer(strategy="median"),
                       RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=0))
    rf.fit(train[feat_cols].to_numpy(float), train["y"].to_numpy())
    imp = rf.named_steps["randomforestclassifier"].feature_importances_
    return (pd.DataFrame({"feature": feat_cols, "importance": imp})
            .sort_values("importance", ascending=False).head(top).reset_index(drop=True))
