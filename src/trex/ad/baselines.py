"""Explainable statistical AD backbone: robust-z + EWMA envelopes per (machine, feature).

Fit a normal-operating envelope on clean buckets (running, non-offline, non-labeled),
score every bucket, then collapse per-feature deviations to one machine-level score while
retaining per-feature attribution (top_roles) for RCA.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from .features import feature_columns, to_ns as _to_ns

_MAD_SCALE = 1.4826


@dataclass
class Envelope:
    machine: str
    feature: str
    median: float
    sigma: float          # robust sigma = 1.4826 * MAD (floored to avoid div0)
    q05: float
    q95: float
    ewma_alpha: float
    n_fit: int


def _intervals_mask(ts: pd.Series, windows: pd.DataFrame, machine: str) -> np.ndarray:
    """True where ts falls inside any [started_on, ended_on] window for this machine
    (windows with machine NA apply to all — e.g. instance-level offline)."""
    out = np.zeros(len(ts), dtype=bool)
    if windows is None or not len(windows):
        return out
    w = windows[(windows.machine == machine) | (windows.machine.isna())]
    arr = _to_ns(ts)
    for s, e in zip(w.started_on, w.ended_on.fillna(w.started_on)):
        out |= (arr >= pd.Timestamp(s).value) & (arr <= pd.Timestamp(e).value)
    return out


def fit_envelopes(feats: pd.DataFrame, *, exclude_windows: pd.DataFrame | None = None,
                  features: list[str] | None = None, ewma_alpha: float = 0.05,
                  running_only: bool = True) -> dict[str, Envelope]:
    """Fit one Envelope per feature on the clean 'normal' subset of one machine's buckets."""
    machine = feats["machine"].iloc[0]
    cols = features or feature_columns(feats)
    clean = feats.copy()
    if running_only and "is_idle" in clean:
        clean = clean[~clean["is_idle"].fillna(False)]
    if "is_offline" in clean:
        clean = clean[~clean["is_offline"].fillna(False)]
    if exclude_windows is not None and len(clean):
        clean = clean[~_intervals_mask(clean["ts"], exclude_windows, machine)]

    env = {}
    for c in cols:
        v = pd.to_numeric(clean[c], errors="coerce").dropna()
        if len(v) < 20:
            continue
        med = float(v.median())
        mad = float((v - med).abs().median()) * _MAD_SCALE
        sigma = mad if mad > 1e-9 else float(v.std() or 1.0) or 1.0
        env[c] = Envelope(machine, c, med, sigma, float(v.quantile(.05)),
                          float(v.quantile(.95)), ewma_alpha, int(len(v)))
    return env


def score_features(feats: pd.DataFrame, envelopes: dict[str, Envelope]) -> pd.DataFrame:
    """Per-bucket, per-feature deviation: robust_z (point) and ewma_z (drift)."""
    rows = []
    feats = feats.sort_values("ts")
    for c, e in envelopes.items():
        if c not in feats:
            continue
        v = pd.to_numeric(feats[c], errors="coerce")
        rz = (v - e.median) / e.sigma
        ewma = v.ewm(alpha=e.ewma_alpha).mean()
        ez = (ewma - e.median) / e.sigma
        rows.append(pd.DataFrame({
            "machine": feats["machine"].to_numpy(), "ts": feats["ts"].to_numpy(),
            "feature": c, "value": v.to_numpy(),
            "robust_z": rz.to_numpy(), "ewma_z": ez.to_numpy(),
            "dev_score": np.maximum(rz.abs(), ez.abs()).to_numpy(),
        }))
    if not rows:
        return pd.DataFrame(columns=["machine", "ts", "feature", "value",
                                     "robust_z", "ewma_z", "dev_score"])
    return pd.concat(rows, ignore_index=True)


def machine_anomaly_score(dev: pd.DataFrame, *, agg: str = "p95",
                          topk_attrib: int = 3) -> pd.DataFrame:
    """Collapse per-feature deviations to one score per (machine, ts) + attribution."""
    if not len(dev):
        return pd.DataFrame(columns=["machine", "ts", "score_baseline", "top_roles"])

    def _agg(s):
        return float(np.nanpercentile(s, 95)) if agg == "p95" else float(getattr(np, agg)(s))

    def _top(g):
        gg = g.reindex(g.dev_score.abs().sort_values(ascending=False).index).head(topk_attrib)
        return [{"role": r.feature, "dev_score": round(float(r.dev_score), 3),
                 "direction": "up" if r.robust_z >= 0 else "down"} for r in gg.itertuples()]

    out = (dev.groupby(["machine", "ts"])
              .apply(lambda g: pd.Series({"score_raw": _agg(g.dev_score.to_numpy()),
                                          "top_roles": _top(g)}), include_groups=False)
              .reset_index())
    # normalize to 0..100 via empirical CDF of the raw scores
    r = out["score_raw"].rank(pct=True)
    out["score_baseline"] = (r * 100).round(2)
    return out[["machine", "ts", "score_baseline", "score_raw", "top_roles"]]
