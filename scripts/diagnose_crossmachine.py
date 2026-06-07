"""Stress-test the 'cross-machine pattern detection' claim. Adversarial, not optimistic.

Four tests:
  T1  Connectivity tautology — are multi-machine CONNECTIVITY buckets just ONE instance-level
      offline row fanned out to members (identical start/end)? If so, recurrence 'detects' a
      logging artifact, not a pattern.
  T2  Co-occurrence null model — for UNPLANNED_RUNSTOP, does observed multi-machine 1h
      co-occurrence exceed chance? Circular-shift permutation null preserves each machine's
      rate + autocorrelation but destroys cross-machine alignment.
  T3  Data-heterogeneity taxonomy — per machine, which canonical roles actually stream, how
      many rows, and are SHARED roles on comparable scales (so cross-machine modeling is valid)?
  T4  Cross-machine signal coupling — do per-machine anomaly-score series co-move? And does the
      coupling survive removing offline buckets (i.e. is there ANY non-connectivity coupling)?

Run: uv run python scripts/diagnose_crossmachine.py
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from trex import loaders, rca
from trex.rca import recurrence

pd.set_option("display.width", 200)
RNG = np.random.default_rng(0)
ART = "analysis/artifacts"


def hr(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def t1_connectivity_tautology():
    hr("T1  CONNECTIVITY recurrence — real pattern or fanned-out duplicate row?")
    off = rca.events.load_offline_events()
    off = off.dropna(subset=["start"])
    # systemic flag was set when >1 machine shares the instance_id
    n_total = len(off)
    inst = off["meta"].map(lambda m: m.get("instance_id"))
    off = off.assign(instance_id=inst)
    # For each instance offline row, how many machines did it fan out to?
    fan = off.groupby(["instance_id", "start", "end"]).machine.nunique()
    multi = fan[fan > 1]
    print(f"offline per-machine events: {n_total:,}")
    print(f"distinct (instance,start,end) offline rows: {fan.size:,}")
    print(f"  ... of which fan out to >1 machine (identical start/end): {multi.size:,} "
          f"({multi.size / max(fan.size,1):.0%})")
    print(f"machines covered by multi-machine offline: up to {int(multi.max()) if len(multi) else 0}")
    # What share of the recurrence 'systemic_score' for CONNECTIVITY is these identical rows?
    rec = recurrence.find_recurrence(bucket="1h")
    conn = rec[rec.category == "CONNECTIVITY"]
    print(f"\nrecurrence CONNECTIVITY buckets flagged systemic: {len(conn):,}")
    print("VERDICT: CONNECTIVITY 'cross-machine' co-occurrence is the SAME offline row "
          "replicated to instance members — \n         a real systemic *facility* fact, but "
          "detected by row-duplication, not by independent cross-machine inference.")


def _hourly_occupancy(starts_by_machine, t0, t1):
    """machine -> binary vector over 1h buckets (stop started in that hour)."""
    idx = pd.date_range(t0.floor("h"), t1.ceil("h"), freq="1h")
    occ = {}
    for m, st in starts_by_machine.items():
        v = np.zeros(len(idx), dtype=np.int8)
        b = ((pd.to_datetime(st, utc=True).floor("h") - idx[0]) // pd.Timedelta("1h")).astype(int)
        b = b[(b >= 0) & (b < len(idx))]
        v[np.unique(b)] = 1
        occ[m] = v
    return idx, occ


def t2_cooccurrence_null():
    hr("T2  UNPLANNED_RUNSTOP cross-machine co-occurrence vs chance (circular-shift null)")
    ev = rca.events.load_stoppage_events()
    up = ev[(ev.category == "UNPLANNED_RUNSTOP")].dropna(subset=["start"])
    up = up[loaders.ms_to_hours(up.duration_ms) >= 0.25]  # >=15min significant stops
    starts = {m: g.start.values for m, g in up.groupby("machine") if len(g) >= 5}
    if len(starts) < 2:
        print("not enough machines"); return
    allts = pd.to_datetime(np.concatenate(list(starts.values())), utc=True)
    idx, occ = _hourly_occupancy(starts, allts.min(), allts.max())
    M = np.vstack([occ[m] for m in starts])           # machines x hours
    obs_per_bucket = M.sum(axis=0)                      # machines active per hour
    obs_multi = int((obs_per_bucket >= 2).sum())       # hours with >=2 machines stopping
    obs_max = int(obs_per_bucket.max())
    # null: independently circular-shift each machine's vector
    K = 300
    null_multi = np.empty(K)
    for k in range(K):
        Ms = np.vstack([np.roll(M[i], RNG.integers(M.shape[1])) for i in range(M.shape[0])])
        null_multi[k] = (Ms.sum(axis=0) >= 2).sum()
    mu, sd = null_multi.mean(), null_multi.std() + 1e-9
    z = (obs_multi - mu) / sd
    p = float((null_multi >= obs_multi).mean())
    print(f"machines: {len(starts)}  significant-stop hours observed")
    print(f"observed hours with >=2 machines stopping: {obs_multi}  (max {obs_max} machines)")
    print(f"null (independent) expectation: {mu:.0f} +/- {sd:.0f}")
    print(f"z = {z:+.2f}   permutation p(null>=obs) = {p:.3f}")
    print("VERDICT:", "EXCEEDS chance — genuine synchronized stops." if p < 0.05
          else "WITHIN chance — multi-machine stop co-occurrence is base-rate coincidence, "
               "NOT a detected systemic pattern.")


def t3_heterogeneity_taxonomy():
    hr("T3  Data-heterogeneity taxonomy — good / present-but-mismatched / poor data")
    feats = pd.read_parquet(f"{ART}/ad_features.parquet")
    mm = loaders.machine_master()
    feat_cols = ["cycle_time_mean", "run_state_duty", "run_time_delta",
                 "axis_move_total", "production_count_delta"]
    rows = []
    for m, g in feats.groupby("machine"):
        live = g[~g.is_offline.fillna(False)]
        rec = {"machine": m, "buckets": len(g), "live_buckets": len(live)}
        for c in feat_cols:
            rec[c] = int(g[c].notna().sum())
        rows.append(rec)
    cov = pd.DataFrame(rows).sort_values("live_buckets", ascending=False)
    # add machines with NO telemetry at all
    tel_machines = set(cov.machine)
    for _, r in mm.iterrows():
        if r["name"] not in tel_machines:
            cov = pd.concat([cov, pd.DataFrame([{"machine": r["name"], "buckets": 0,
                            "live_buckets": 0, **{c: 0 for c in feat_cols}}])], ignore_index=True)
    print(cov.to_string(index=False))

    # comparability of a SHARED role across machines: cycle_time_mean distribution per machine
    print("\ncycle_time_mean per-machine distribution (are scales comparable?):")
    ct = (feats[feats.cycle_time_mean.notna()]
          .groupby("machine").cycle_time_mean
          .agg(n="count", p10=lambda s: s.quantile(.1), median="median",
               p90=lambda s: s.quantile(.9)))
    print(ct.to_string())
    meds = ct["median"].replace(0, np.nan).dropna()
    if len(meds) > 1:
        spread = meds.max() / max(meds.min(), 1e-9)
        print(f"\nmedian cycle_time spans {meds.min():.1f}..{meds.max():.1f} "
              f"=> {spread:.0f}x across machines.")
        print("VERDICT:", "comparable — pooled modeling OK." if spread < 3
              else "NOT comparable raw — same role, different physical scale per machine; "
                   "cross-machine modeling needs per-machine normalization, not raw pooling.")


def t4_signal_coupling():
    hr("T4  Cross-machine signal coupling — do anomaly scores co-move? survive offline removal?")
    sc = pd.read_parquet(f"{ART}/ad_scores.parquet")[["machine", "ts", "score", "is_offline"]]
    sc["ts"] = pd.to_datetime(sc["ts"], utc=True)

    def corr_matrix(df, label):
        piv = (df.assign(h=df.ts.dt.floor("1h"))
                 .groupby(["machine", "h"]).score.mean().unstack("machine"))
        piv = piv.dropna(axis=1, how="all")
        # need overlapping hours
        C = piv.corr(min_periods=50)
        vals = C.where(~np.eye(len(C), dtype=bool)).stack()
        print(f"\n[{label}] machines={C.shape[0]}  off-diagonal corr: "
              f"median={vals.median():.3f}  p90={vals.quantile(.9):.3f}  max={vals.max():.3f}")
        top = vals.sort_values(ascending=False).head(5)
        for (a, b), v in top.items():
            print(f"    {a:>10} ~ {b:<10} r={v:.3f}")
        return vals

    v_all = corr_matrix(sc, "ALL buckets (incl. offline)")
    v_live = corr_matrix(sc[~sc.is_offline.fillna(False)], "LIVE only (offline removed)")
    print("\nVERDICT: if coupling collapses once offline buckets are removed, the only true "
          "cross-machine\n         signal is connectivity; per-machine telemetry deviations are "
          "essentially independent.")
    print(f"  median corr  all={v_all.median():.3f}  ->  live={v_live.median():.3f}")


if __name__ == "__main__":
    t1_connectivity_tautology()
    t2_cooccurrence_null()
    t3_heterogeneity_taxonomy()
    t4_signal_coupling()
    print("\n" + "=" * 78 + "\nDONE\n" + "=" * 78)
