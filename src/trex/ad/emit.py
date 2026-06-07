"""Fuse baseline + AE scores into the RCA contract and write artifacts.

Outputs (analysis/artifacts/):
  ad_scores.parquet          [machine, ts, score_baseline, score_ae, score, is_idle, is_offline, transferred]
  ad_anomaly_windows.parquet [machine, window_start, window_end, peak_score, detector,
                              top_roles, nearest_label, lead_time_min]
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

ART = Path("analysis/artifacts")


def fuse_scores(feats: pd.DataFrame, baseline: pd.DataFrame,
                ae: pd.DataFrame | None = None) -> pd.DataFrame:
    """Join baseline (per-bucket) + AE (per-window end) onto the feature grid."""
    meta = feats[["machine", "ts", "is_idle", "is_offline"]].copy()
    df = meta.merge(baseline[["machine", "ts", "score_baseline", "top_roles"]],
                    on=["machine", "ts"], how="left")
    if ae is not None and len(ae):
        a = ae.copy()
        a["score_ae"] = a["recon_err"].rank(pct=True) * 100
        df = df.merge(a[["machine", "ts", "score_ae", "per_feature_err"]],
                      on=["machine", "ts"], how="left")
    else:
        df["score_ae"] = np.nan
        df["per_feature_err"] = None
    df["transferred"] = False
    # fused score: max of available detectors (each 0..100)
    df["score"] = df[["score_baseline", "score_ae"]].max(axis=1, skipna=True)
    return df


def extract_windows(scores: pd.DataFrame, *, thresh: float = 90.0,
                    merge_gap="10min", min_len=1) -> pd.DataFrame:
    """Hysteresis-merge contiguous score>thresh buckets into flagged windows."""
    gap = pd.Timedelta(merge_gap)
    out = []
    for m, g in scores.sort_values("ts").groupby("machine"):
        g = g[(g["score"] >= thresh) & (~g["is_offline"].fillna(False))]
        if not len(g):
            continue
        ts = g["ts"].reset_index(drop=True)
        grp = (ts.diff() > gap).cumsum()
        for _, w in g.assign(grp=grp.to_numpy()).groupby("grp"):
            roles = w.sort_values("score", ascending=False)["top_roles"].dropna()
            det = ("both" if w["score_ae"].notna().any() and w["score_baseline"].notna().any()
                   else "ae" if w["score_ae"].notna().any() else "baseline")
            out.append({"machine": m, "window_start": w["ts"].min(),
                        "window_end": w["ts"].max(), "peak_score": float(w["score"].max()),
                        "n_buckets": int(len(w)), "detector": det,
                        "top_roles": roles.iloc[0] if len(roles) else None})
    df = pd.DataFrame(out)
    return df[df.get("n_buckets", 0) >= min_len].reset_index(drop=True) if len(df) else df


def link_labels(windows: pd.DataFrame, labels: pd.DataFrame, *, horizon="6h") -> pd.DataFrame:
    """Attach the nearest downstream labeled event + lead time (eval linkage)."""
    if not len(windows):
        return windows
    H = pd.Timedelta(horizon)
    nl, lt = [], []
    for w in windows.itertuples():
        ev = labels[(labels.machine == w.machine) &
                    (labels.started_on >= w.window_end) &
                    (labels.started_on <= w.window_end + H)].sort_values("started_on")
        if len(ev):
            e = ev.iloc[0]
            nl.append(e.label_text)
            lt.append((e.started_on - w.window_start) / pd.Timedelta("1min"))
        else:
            nl.append(None); lt.append(np.nan)
    return windows.assign(nearest_label=nl, lead_time_min=np.round(lt, 1))


def write_outputs(scores: pd.DataFrame, windows: pd.DataFrame, out_dir=ART):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    s = scores.copy()
    s["top_roles"] = s["top_roles"].apply(lambda v: str(v) if v is not None else None)
    if "per_feature_err" in s:
        s["per_feature_err"] = s["per_feature_err"].apply(lambda v: str(v) if v is not None else None)
    s.to_parquet(out_dir / "ad_scores.parquet", index=False)
    w = windows.copy()
    if len(w):
        w["top_roles"] = w["top_roles"].apply(lambda v: str(v) if v is not None else None)
    w.to_parquet(out_dir / "ad_anomaly_windows.parquet", index=False)
    return out_dir / "ad_scores.parquet", out_dir / "ad_anomaly_windows.parquet"
