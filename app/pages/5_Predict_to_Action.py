"""Predict → Root Cause → What-If, end-to-end for the Fanuc production cell.

The Platinum story on one page: the deployed Fanuc stop-predictor flags a high-risk episode →
RCA explains why → What-If quantifies the OEE / € recovery if the root cause is fixed.
Predictive layer is scoped to Fanuc by design (signal availability); the honest scope note is shown.
"""
import sys
import pathlib
sys.path.insert(0, next(str(p) for p in pathlib.Path(__file__).resolve().parents
                        if p.name == "app"))

import pandas as pd
import streamlit as st
from lib import data, charts, state
from trex import rca, whatif, loaders

st.set_page_config(page_title="Predict → Action", page_icon="🎯", layout="wide")
st.title("🎯 Predict → Root Cause → What-If")

meta = data.fanuc_meta()
risk = data.fanuc_risk()
eps = data.fanuc_episodes()

st.info("**Scope (by design):** the predictive layer covers the **Fanuc production cell "
        "{Makine 1, 2, 3, 5, 9}**, where the cycle-time / run-state signals that precede stops "
        "actually stream. Mitsubishi {7,8} lack those signals (predictor ≈ chance) and are covered "
        "in RCA / OEE instead; {4, 6, 10, TurboCut, ARES} have no telemetry. Numbers below are on "
        "an **untouched future** test window — the model never saw them.")

if not len(risk) or not meta:
    st.warning("Run `uv run python scripts/build_fanuc_risk.py` first."); st.stop()

m = st.columns(5)
m[0].metric("ROC-AUC", meta.get("ROC_AUC"))
m[1].metric("Lift vs base", f"{meta.get('lift')}×")
m[2].metric("Episode precision", f"{meta.get('episode_precision', 0)*100:.0f}%",
            help="Share of flagged high-risk episodes followed by a real significant stop "
                 f"(base rate {meta.get('base_rate', 0)*100:.0f}%).")
m[3].metric("Significant stop", "≥15 min within 60 min")
m[4].metric("Test rows", f"{meta.get('n_test', 0):,}")

machine = st.selectbox("Fanuc machine", meta.get("machines", []),
                       index=0 if meta.get("machines") else None)
rm = risk[risk.machine == machine]
if not len(rm):
    st.warning("No risk rows for this machine."); st.stop()

thr = float(meta.get("threshold", 0.5))

# ── 1. PREDICT — risk timeline + actual stops ────────────────────────────────
st.subheader("1 · Predict — stop-risk timeline")
hourly = rm.set_index("ts")["risk"].resample("1h").max().dropna().reset_index()
ev = data.event_stream()
sm = ev[(ev.machine == machine) & (ev.category == "UNPLANNED_RUNSTOP")].dropna(subset=["start"])
sm = sm[loaders.ms_to_hours(sm.duration_ms) >= 0.25]
t0, t1 = rm.ts.min(), rm.ts.max()
stop_times = sm[(sm.start >= t0) & (sm.start <= t1)].start

em = eps[eps.machine == machine].sort_values("peak_risk", ascending=False).reset_index(drop=True)
window = None
ep = None
if len(em):
    labels = [f"{r.start:%Y-%m-%d %H:%M} UTC · peak {r.peak_risk:.2f} · "
              f"{'⚠️ real stop followed' if r.hit else 'no stop'}" for r in em.itertuples()]
    sel = st.selectbox("High-risk episode (sorted by peak risk)", range(len(em)),
                       format_func=lambda i: labels[i])
    ep = em.iloc[sel]
    window = (ep.start, ep.end)

st.plotly_chart(charts.risk_timeline(hourly, thr, stop_times, window=window), width="stretch")
if ep is not None:
    st.caption(f"Selected episode: {ep.start:%Y-%m-%d %H:%M} → {ep.end:%H:%M} UTC · "
               f"peak risk {ep.peak_risk:.2f} · {'a real significant stop followed' if ep.hit else 'no significant stop followed (false alarm)'}.")

# ── 2. RCA — explain the flagged episode ─────────────────────────────────────
st.divider()
st.subheader("2 · Root cause — why it stops")


@st.cache_data(show_spinner="Running root-cause analysis…")
def _card(machine, start, end):
    return rca.build_root_cause_card(machine, start, end, stream=data.event_stream())


if ep is None:
    st.caption("No above-threshold risk episodes for this machine in the test window.")
    card = None
else:
    try:
        card = _card(machine, ep.start, ep.end + pd.Timedelta(minutes=60))
    except Exception as e:                       # keep the page resilient
        card = None
        st.warning(f"Root-cause analysis unavailable for this window ({e}).")

if card is not None:
    rc = card.to_dict()
    cL, cR = st.columns([1.1, 1])
    with cL:
        st.markdown(f"**Trigger:** {rc['trigger']}  \n**Pattern:** `{rc['pattern']}`  \n"
                    f"**Linked unplanned downtime in window:** {rc['linked_downtime_hours']} h")
        if rc.get("cascade"):
            cas = rc["cascade"]
            st.markdown(f"**Alarm cascade:** {' → '.join(cas['alarms'])}  \n"
                        f"**Causal root:** `{cas['root_alarm']}` ({cas['root_category']})")
        if rc["evidence"]:
            st.markdown("**Evidence**")
            for e in rc["evidence"]:
                st.markdown(f"- {e}")
    with cR:
        st.markdown("**Ranked hypotheses**")
        hy = pd.DataFrame(rc["hypotheses"])
        if len(hy):
            st.dataframe(hy[["cause", "likelihood", "recommended_action"]],
                         hide_index=True, width="stretch")
    if rc["pattern"] in ("OPERATIONAL_STOP", "UNPLANNED_RUNSTOP") and not rc.get("cascade"):
        st.caption("ℹ️ This machine's unplanned stops carry a single generic label (`Duruş`) with "
                   "no alarm granularity, so RCA ranks **what / when** (Pareto + recency), not a "
                   "device-level **why**. Alarm-level root cause is available only on Makine 1 & 2.")
    st.markdown(f"**Recommended action:** {rc['recommended_action']}")

# ── 3. WHAT-IF — quantify the OEE / € recovery ───────────────────────────────
st.divider()
st.subheader("3 · What-If — OEE & financial impact of fixing it")

base = data.baseline()
bm = base[base.machine == machine]
COMP = ["WorkTotal", "PlannedStop", "UnPlannedStop", "WorkingTime", "PlannedTime",
        "ProductSum", "ScrapeSum"]
agg = {c: float(bm[c].sum()) for c in COMP if c in bm}
agg.update(machine=machine, date="ALL")

hint = rca.to_whatif_bridge(card) if card is not None else None
if hint is not None and hint.category == "CONNECTIVITY":
    st.warning(f"RCA verdict: **connectivity fault**. {hint.note} — this does **not** recover "
               "machine OEE; the action is an IT/network fix, not a process change.")
else:
    cat_label = hint.category if hint else "UNPLANNED_RUNSTOP"
    c = st.columns([1, 1, 2])
    pct = c[0].slider("Reduce this machine's unplanned downtime by %", 0, 100, 50) / 100.0
    spec = whatif.ScenarioSpec(kind="W1", pct=pct, category="UNPLANNED_RUNSTOP")
    res = whatif.run_scenario(agg, spec, category_ms=agg.get("UnPlannedStop", 0.0))
    if hint:
        st.caption(f"From RCA → What-If: target **{cat_label}**. {hint.note}")

    k = st.columns(4)
    for col, name in zip(k, ["OEE", "A", "P", "Q"]):
        col.metric(name, f"{res.after[name]:.1%}", f"{res.after[name] - res.before[name]:+.1%}")
    if res.assumptions_note:
        st.caption("ℹ️ " + res.assumptions_note)

    wl, wr = st.columns([1.2, 1])
    with wl:
        st.plotly_chart(charts.oee_waterfall(whatif.waterfall_rows(res.before, res.after)),
                        width="stretch")
        st.caption(f"Recovered runtime: {res.recovered_runtime_ms/3.6e6:.1f} h  ·  "
                   f"extra pieces: {res.extra_pieces:.0f}")
    with wr:
        st.markdown("**Financial impact**")
        st.caption("⚠️ " + whatif.ASSUMPTION_LABEL)
        a = whatif.FinancialAssumptions()
        a.contribution_margin_per_piece = st.number_input("Margin / piece", value=12.0)
        a.downtime_cost_per_hour = st.number_input("Downtime cost / h", value=80.0)
        a.intervention_cost = st.number_input("Intervention cost", value=300.0)
        a.value_recovered_time_as = st.radio("Value recovered time as",
                                             ["margin", "downtime_cost"], horizontal=True)
        fin = whatif.compute_financials(res, a, period_days=1)
        f1, f2 = st.columns(2)
        f1.metric(f"Net / {a.horizon_days}d", f"{fin.net_benefit:,.0f} {a.currency}")
        f2.metric("Payback (days)", "—" if fin.payback_days is None else f"{fin.payback_days:.1f}")
