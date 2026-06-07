"""Fanuc production-cell stop predictor — the deployed configuration.

This is the model we present: Fanuc {1,2,3,5,9} only (where the cycle-time / run-state signals
that precede stops actually stream), per-machine robust z-norm, tuned HistGBDT. Mitsubishi {7,8}
are intentionally NOT here — they lack the predictive signals (see 05_REGIME_MODELS /
06_FANUC_TUNING) and are covered by RCA/OEE instead.

Leakage-safe: per-machine chronological split, z-norm stats from train only, past-only features.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             precision_recall_curve)
from .dataset import build_supervised

FANUC = ["Makine 1", "Makine 2", "Makine 3", "Makine 5", "Makine 9"]
TELE_KEYS = ("cycle_time", "run_state", "run_time", "axis_move", "machine_mode", "production")
ART = Path("analysis/artifacts")
DEFAULT_PARAMS = dict(learning_rate=0.02, max_iter=300, max_leaf_nodes=15,
                      min_samples_leaf=200, l2_regularization=1.0, max_features=0.9,
                      class_weight=None)


def best_params() -> dict:
    p = ART / "fanuc_tuning_metrics.json"
    if p.exists():
        return json.loads(p.read_text())["best_params"]
    return dict(DEFAULT_PARAMS)


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
                te.loc[te.machine == m, c] = (te.loc[te.machine == m, c] - med) / iqr
    return tr, te


def augment(df):
    """cheap derived features from existing columns (no telemetry re-read, no future info)."""
    d = df.copy()
    def sub(a, b):
        return d[a] - d[b] if a in d and b in d else 0.0
    d["cycle_dev"] = sub("cycle_time_mean", "cycle_time_mean__long_mean")
    d["runstate_dev"] = sub("run_state_duty", "run_state_duty__long_mean")
    d["prod_dev"] = sub("production_count_delta", "production_count_delta__long_mean")
    if "cycle_time_mean__roll_mean" in d and "cycle_time_mean__long_mean" in d:
        d["cycle_short_long"] = d["cycle_time_mean__roll_mean"] / (
            d["cycle_time_mean__long_mean"].replace(0, np.nan))
    if "sigstop_cnt_4h" in d and "downtime_min_4h" in d:
        d["stop_pressure"] = d["sigstop_cnt_4h"] * np.log1p(d["downtime_min_4h"])
    if "micro_cnt_1h" in d and "micro_cnt_4h" in d:
        d["micro_accel"] = d["micro_cnt_1h"] - d["micro_cnt_4h"] / 4.0
    if "hour" in d:
        d["hour_sin"] = np.sin(2 * np.pi * d["hour"] / 24)
        d["hour_cos"] = np.cos(2 * np.pi * d["hour"] / 24)
    new = ["cycle_dev", "runstate_dev", "prod_dev", "cycle_short_long", "stop_pressure",
           "micro_accel", "hour_sin", "hour_cos"]
    return d, [c for c in new if c in d]


def build_dataset(horizon_min=60, min_stop_min=15):
    data, base = build_supervised(machines=FANUC, horizon_min=horizon_min,
                                  min_stop_min=min_stop_min)
    base = [c for c in base if data[c].notna().any()]
    data, new = augment(data)
    data[new] = data[new].replace([np.inf, -np.inf], np.nan)
    new = [c for c in new if data[c].notna().any()]
    return data.reset_index(drop=True), base + new


def train_score(train_frac=0.6, params=None, horizon_min=60, min_stop_min=15):
    """Train tuned HistGBDT on the chronological train, score the held-out future.
    Returns (model, scored_test_df[machine,ts,y,risk], feat_cols, metrics)."""
    data, feat = build_dataset(horizon_min, min_stop_min)
    tr, te = chrono_split(data, train_frac)
    trz, tez = znorm(tr, te, feat)
    model = HistGradientBoostingClassifier(random_state=0, **(params or best_params()))
    model.fit(trz[feat].to_numpy(float), trz["y"].to_numpy())
    risk = model.predict_proba(tez[feat].to_numpy(float))[:, 1]
    scored = tez[["machine", "ts", "y"]].copy()
    scored["risk"] = risk
    y = scored["y"].to_numpy()
    prec, rec, th = precision_recall_curve(y, risk)
    f1s = np.divide(2 * prec * rec, prec + rec, out=np.zeros_like(prec), where=(prec + rec) > 0)
    thr = float(th[max(0, np.argmax(f1s) - 1)]) if len(th) else 0.5
    metrics = {"ROC_AUC": round(float(roc_auc_score(y, risk)), 4),
               "PR_AUC": round(float(average_precision_score(y, risk)), 4),
               "base_rate": round(float(y.mean()), 4), "threshold": round(thr, 4),
               "n_train": int(len(tr)), "n_test": int(len(te)), "n_features": len(feat),
               "test_start": str(scored.ts.min()), "test_end": str(scored.ts.max())}
    metrics["lift"] = round(metrics["PR_AUC"] / metrics["base_rate"], 2)
    return model, scored, feat, metrics


def risk_episodes(scored, threshold, *, merge_gap_min=20, min_buckets=3):
    """Group consecutive above-threshold buckets (time-gap-merged) into risk episodes.
    `hit` = an actual significant stop fell within the horizon of some bucket in the episode."""
    out = []
    for m, g in scored.groupby("machine"):
        g = g.sort_values("ts").reset_index(drop=True)
        ts = g["ts"].to_numpy()
        idx = np.where(g["risk"].to_numpy() >= threshold)[0]
        if not len(idx):
            continue
        s = prev = idx[0]
        runs = []
        for j in idx[1:]:
            if (ts[j] - ts[prev]) / np.timedelta64(1, "m") <= merge_gap_min:
                prev = j
            else:
                runs.append((s, prev)); s = j; prev = j
        runs.append((s, prev))
        for a, b in runs:
            if b - a + 1 < min_buckets:
                continue
            seg = g.iloc[a:b + 1]
            out.append({"machine": m, "start": seg.ts.iloc[0], "end": seg.ts.iloc[-1],
                        "peak_risk": round(float(seg.risk.max()), 3),
                        "mean_risk": round(float(seg.risk.mean()), 3),
                        "n_buckets": int(len(seg)), "hit": bool(seg.y.max() == 1)})
    ep = pd.DataFrame(out)
    return (ep.sort_values("peak_risk", ascending=False).reset_index(drop=True)
            if len(ep) else ep)
