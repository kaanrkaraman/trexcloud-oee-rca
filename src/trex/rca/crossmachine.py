"""Cross-machine pattern detection — the defensible version.

Replaces naive co-occurrence binning (`recurrence.find_recurrence`, which has no null model
and whose top finding is a row-duplication artifact) with three rigorous detectors:

  1. synchronization_test  — do significant unplanned stops co-initiate across machines MORE
     than chance? Two nulls: FREE circular-shift (tests any alignment, incl. shared daily
     rhythm) and DAILY-preserving shift (tests alignment BEYOND shared hour-of-day schedule).
     The gap between them separates "they stop together because same shift" from "they stop
     together because a shared facility event". Also reports hour-of-day concentration and
     reason concordance.
  2. coupling            — pairwise correlation of per-machine anomaly-score series, with a
     connected-components cluster at r>=thr; computed on ALL / LIVE / RUNNING buckets so we
     can see whether a cluster is a genuine coupling or just a shared idle/offline schedule.
  3. regime_map          — derives the data-comparability regimes FROM feature availability
     (not vendor catalog) and flags which machine sets can actually be jointly modeled.

Honesty is the point: every detector reports what would also fire by chance / by schedule.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .. import loaders
from . import events

SCORES = "analysis/artifacts/ad_scores.parquet"
FEATURES = "analysis/artifacts/ad_features.parquet"


# ---------------------------------------------------------------- synchronization
def significant_unplanned(min_min=15.0) -> pd.DataFrame:
    ev = events.load_stoppage_events().dropna(subset=["start"])
    up = ev[ev.category == "UNPLANNED_RUNSTOP"].copy()
    up = up[loaders.ms_to_hours(up.duration_ms) >= (min_min / 60.0)]
    return up[["machine", "start", "label", "duration_ms"]]


def _occupancy(up: pd.DataFrame, bucket="1h"):
    up = up.dropna(subset=["machine"]).copy()
    up["b"] = up.start.dt.floor(bucket)
    idx = pd.date_range(up.b.min(), up.b.max(), freq=bucket)
    machines = sorted(up.machine.unique())
    mi = {m: i for i, m in enumerate(machines)}
    pos = {t: i for i, t in enumerate(idx)}
    M = np.zeros((len(machines), len(idx)), dtype=np.int8)
    for m, b in zip(up.machine, up.b):
        M[mi[m], pos[b]] = 1
    return machines, idx, M


def synchronization_test(min_min=15.0, bucket="1h", n_perm=400, seed=0) -> dict:
    rng = np.random.default_rng(seed)
    up = significant_unplanned(min_min)
    machines, idx, M = _occupancy(up, bucket)
    col = M.sum(0)
    obs = int((col >= 2).sum())
    H = M.shape[1]
    per_day = max(1, int(round(pd.Timedelta("1D") / pd.Timedelta(bucket))))

    def null(daily: bool):
        out = np.empty(n_perm)
        for k in range(n_perm):
            sh = (rng.integers(0, max(1, H // per_day), M.shape[0]) * per_day if daily
                  else rng.integers(0, H, M.shape[0]))
            Ms = np.vstack([np.roll(M[i], int(sh[i])) for i in range(M.shape[0])])
            out[k] = (Ms.sum(0) >= 2).sum()
        return out

    def stat(name, nd):
        mu, sd = float(nd.mean()), float(nd.std() + 1e-9)
        return {"null": name, "exp": round(mu, 1), "sd": round(sd, 1),
                "z": round((obs - mu) / sd, 2), "p": float((nd >= obs).mean())}

    free, daily = stat("free_shift", null(False)), stat("daily_preserving", null(True))

    # hour-of-day concentration of co-stop buckets
    co_hours = pd.Series(idx[col >= 2].hour)
    hod = (co_hours.value_counts(normalize=True).sort_values(ascending=False))
    top3_share = float(hod.head(3).sum()) if len(hod) else 0.0

    # reason granularity: how many DISTINCT unplanned-stop reasons exist at all? If 1, any
    # "same-reason concordance" is vacuous (trivially 100%) and must not be reported as evidence.
    up2 = up.copy(); up2["b"] = up2.start.dt.floor(bucket)
    n_co_buckets = int(up2.groupby("b").machine.nunique().ge(2).sum())
    n_distinct_reasons = int(up["label"].nunique())
    reason_note = ("VACUOUS — single generic label, no reason granularity"
                   if n_distinct_reasons <= 1 else "informative")

    return {"machines": machines, "n_machines": len(machines), "buckets": H,
            "observed_co_stop_hours": obs, "free": free, "daily": daily,
            "top3_hour_share": round(top3_share, 3),
            "busiest_hours": [int(h) for h in hod.head(3).index.tolist()],
            "n_distinct_reasons": n_distinct_reasons, "reason_note": reason_note,
            "n_co_stop_buckets": n_co_buckets}


# ---------------------------------------------------------------- coupling
def _score_pivot(mode="running"):
    sc = pd.read_parquet(SCORES)[["machine", "ts", "score", "is_idle", "is_offline"]]
    sc["ts"] = pd.to_datetime(sc["ts"], utc=True)
    if mode in ("live", "running"):
        sc = sc[~sc.is_offline.fillna(False)]
    if mode == "running":
        sc = sc[~sc.is_idle.fillna(False)]
    return (sc.assign(h=sc.ts.dt.floor("1h"))
              .groupby(["machine", "h"]).score.mean().unstack("machine"))


def _clusters(C: pd.DataFrame, thr: float):
    adj = {m: set() for m in C.columns}
    for a in C.columns:
        for b in C.columns:
            if a != b and C.loc[a, b] >= thr:
                adj[a].add(b)
    seen, comps = set(), []
    for m in C.columns:
        if m in seen:
            continue
        stack, comp = [m], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x); comp.append(x); stack.extend(adj[x] - seen)
        if len(comp) >= 2:
            comps.append(sorted(comp))
    return comps


def coupling(thr=0.5, min_overlap=50) -> dict:
    out = {}
    for mode in ("all", "live", "running"):
        piv = _score_pivot(mode).dropna(axis=1, how="all")
        C = piv.corr(min_periods=min_overlap)                       # levels (incl. slow trend)
        Cd = piv.diff().corr(min_periods=min_overlap)               # first-diff (event timescale)
        off = C.where(~np.eye(len(C), dtype=bool)).stack()
        offd = Cd.where(~np.eye(len(Cd), dtype=bool)).stack()
        out[mode] = {"corr": C, "corr_diff": Cd,
                     "median_off": round(float(off.median()), 3),
                     "max_off": round(float(off.max()), 3),
                     "clusters": _clusters(C.fillna(0), thr),
                     "median_off_diff": round(float(offd.median()), 3),
                     "max_off_diff": round(float(offd.max()), 3),
                     "clusters_diff": _clusters(Cd.fillna(0), thr),
                     "top_pairs": [(a, b, round(float(v), 3))
                                   for (a, b), v in off.sort_values(ascending=False).head(4).items()
                                   if a < b]}
    return out


# ---------------------------------------------------------------- regime map
FEAT_ROLES = ["cycle_time_mean", "run_state_duty", "run_time_delta",
              "axis_move_total", "production_count_delta"]


def regime_map(min_buckets=500) -> dict:
    feats = pd.read_parquet(FEATURES)
    mm = loaders.machine_master()
    avail, scale = [], {}
    for m, g in feats.groupby("machine"):
        live = g[~g.is_offline.fillna(False)]
        row = {"machine": m, "live_buckets": len(live)}
        for c in FEAT_ROLES:
            row[c] = int(g[c].notna().sum())
        avail.append(row)
    A = pd.DataFrame(avail)
    # presence pattern = which roles exceed min_buckets
    present = {r["machine"]: tuple(c for c in FEAT_ROLES if r[c] >= min_buckets)
               for _, r in A.iterrows()}
    # add blind machines (no telemetry rows at all)
    for _, r in mm.iterrows():
        present.setdefault(r["name"], tuple())
    # group machines by identical presence pattern => data regime
    regimes = {}
    for mac, pat in present.items():
        regimes.setdefault(pat, []).append(mac)
    # comparability of each shared role (median spread across machines that have it)
    comp = []
    for c in FEAT_ROLES:
        s = feats[feats[c].notna()].groupby("machine")[c].median()
        s = s[s > 0]
        if len(s) >= 2:
            comp.append({"role": c, "machines": len(s),
                         "median_min": float(s.min()), "median_max": float(s.max()),
                         "spread_x": round(float(s.max() / s.min()), 1)})
    return {"availability": A, "present": present,
            "regimes": {", ".join(p) or "(blind)": sorted(ms) for p, ms in regimes.items()},
            "comparability": pd.DataFrame(comp)}
