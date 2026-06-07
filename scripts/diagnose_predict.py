"""Diagnose stop-prediction: is telemetry contributing, or is it recency/time only?
Robust: numpy arrays, guarded variants. Writes findings to stdout.
"""
import warnings
warnings.simplefilter("ignore")
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from trex import predict

H, MS = 60, 15
data, feat_cols = predict.build_supervised(horizon_min=H, min_stop_min=MS)
tr, te = predict.time_split(data, train_frac=0.6)
REC = [c for c in feat_cols if any(k in c for k in ("since_last", "stops_last", "hour"))]
TEL = [c for c in feat_cols if c not in REC]
print(f"rows={len(data):,} feats={len(feat_cols)} (telemetry={len(TEL)} recency/time={len(REC)}) "
      f"pos={data.y.mean():.3f}")


def fit(cols, train=tr, test=te, model="hgb", znorm_by_machine=False):
    Xtr = train[cols].to_numpy(float).copy(); Xte = test[cols].to_numpy(float).copy()
    if znorm_by_machine:
        for m in train.machine.unique():
            mtr = (train.machine == m).to_numpy(); mte = (test.machine == m).to_numpy()
            mu = np.nanmean(Xtr[mtr], axis=0); sd = np.nanstd(Xtr[mtr], axis=0); sd[sd == 0] = 1
            Xtr[mtr] = (Xtr[mtr] - mu) / sd
            if mte.any():
                Xte[mte] = (Xte[mte] - mu) / sd
    ytr, yte = train.y.to_numpy(), test.y.to_numpy()
    if model == "hgb":
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.07,
                                             l2_regularization=1.0, random_state=0)
    else:
        imp = SimpleImputer(strategy="median")
        Xtr = imp.fit_transform(Xtr); Xte = imp.transform(Xte)
        clf = RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=0,
                                     class_weight="balanced_subsample")
    clf.fit(Xtr, ytr); p = clf.predict_proba(Xte)[:, 1]
    return roc_auc_score(yte, p), average_precision_score(yte, p)


print("\n=== base rate per machine (train vs test) ===")
for m in sorted(data.machine.unique()):
    a, b = tr[tr.machine == m], te[te.machine == m]
    print(f"  {m:12s} n_tr={len(a):6d} pos_tr={a.y.mean():.3f} | n_te={len(b):6d} pos_te={b.y.mean():.3f}")

print("\n=== DECISIVE: feature-set ablation (pooled HGB) ===")
for name, cols in [("recency/time only", REC), ("telemetry only", TEL), ("ALL", feat_cols)]:
    try:
        r, p = fit(cols)
        print(f"  {name:20s} ROC={r:.3f} PR={p:.3f}  ({len(cols)} feats)")
    except Exception as e:
        print(f"  {name:20s} ERR {e}")

print("\n=== data-prep variants (ALL feats) ===")
for name, kw in [("pooled raw", {}), ("per-machine z-norm", {"znorm_by_machine": True})]:
    try:
        r, p = fit(feat_cols, **kw); print(f"  {name:20s} ROC={r:.3f} PR={p:.3f}")
    except Exception as e:
        print(f"  {name:20s} ERR {e}")
try:
    dum = pd.get_dummies(data.machine, prefix="m").astype(float)
    trd = pd.concat([tr[feat_cols].reset_index(drop=True), dum.loc[tr.index].reset_index(drop=True)], axis=1)
    ted = pd.concat([te[feat_cols].reset_index(drop=True), dum.loc[te.index].reset_index(drop=True)], axis=1)
    trw = tr.assign(_i=range(len(tr))); tew = te.assign(_i=range(len(te)))
    # quick inline fit for the augmented matrix
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.07, random_state=0)
    clf.fit(trd.to_numpy(float), tr.y.to_numpy()); p = clf.predict_proba(ted.to_numpy(float))[:, 1]
    print(f"  {'+ machine one-hot':20s} ROC={roc_auc_score(te.y, p):.3f} PR={average_precision_score(te.y, p):.3f}")
except Exception as e:
    print(f"  + machine one-hot ERR {e}")

print("\n=== per-machine separate models (HGB) ===")
aucs = []
for m in sorted(data.machine.unique()):
    a, b = tr[tr.machine == m], te[te.machine == m]
    if b.y.nunique() < 2 or len(a) < 300 or a.y.nunique() < 2:
        print(f"  {m:12s} skip"); continue
    try:
        r, p = fit(feat_cols, train=a, test=b)
        aucs.append(r); print(f"  {m:12s} ROC={r:.3f} PR={p:.3f} pos_te={b.y.mean():.3f}")
    except Exception as e:
        print(f"  {m:12s} ERR {e}")
if aucs:
    print(f"  mean per-machine ROC={np.mean(aucs):.3f}")
