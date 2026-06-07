"""Console demo — concrete end-to-end cases you can read without launching the app.

Run: uv run python scripts/demo.py            (all demos)
     uv run python scripts/demo.py rca|conn|recur|whatif|ad   (one demo)
"""
import sys
from pathlib import Path
import pandas as pd

from trex import oee, rca, whatif
from trex.ad import labels, eval as adeval

ART = Path("analysis/artifacts")


def _rule(t):
    print("\n" + "═" * 78 + f"\n  {t}\n" + "═" * 78)


def _ad_windows():
    p = ART / "ad_anomaly_windows.parquet"
    if not p.exists():
        return None
    w = pd.read_parquet(p)
    for c in ("window_start", "window_end"):
        w[c] = pd.to_datetime(w[c], utc=True)
    return w


def demo_rca(adw):
    _rule("DEMO 1 · RCA flagship — Makine 1 AIR PRESSURE FAILED (2026-01-12 04:47)")
    card = rca.build_root_cause_card("Makine 1", "2026-01-12 04:40", "2026-01-12 05:00",
                                     ad_df=adw, stream=rca.build_event_stream(ad_df=adw))
    print(f"  Trigger : {card.trigger}")
    print(f"  Pattern : {card.pattern}   connectivity={card.is_connectivity}")
    if card.cascade:
        print(f"  Cascade : {' -> '.join(card.cascade['alarms'])}")
        print(f"            root = {card.cascade['root_category']} "
              f"(by causal precedence, not array index)")
    print(f"  Linked downtime : {card.linked_downtime_hours} h")
    print("  Evidence:")
    for e in card.evidence:
        print(f"    • {e}")
    print("  Ranked hypotheses:")
    for h in card.hypotheses[:3]:
        print(f"    {h['likelihood']:.0%}  {h['cause']}")
        print(f"         ↳ {h['recommended_action']}")
    hint = rca.to_whatif_bridge(card)
    print(f"  → What-If bridge: recover {hint.recoverable_ms/3.6e6:.1f}h "
          f"({hint.category}, scenario {hint.target_scenario})")


def demo_connectivity(adw):
    _rule("DEMO 2 · Connectivity vs machine fault — System Offline is NOT recoverable OEE")
    stream = rca.build_event_stream(ad_df=adw)
    off = stream[stream.source == "offline"].sort_values("duration_ms", ascending=False)
    if not len(off):
        print("  (no offline events)"); return
    e = off.iloc[0]
    card = rca.build_root_cause_card(e.machine, e.start, e.end or e.start, stream=stream)
    print(f"  {e.machine} offline {e.start} → {e.end}")
    print(f"  Pattern : {card.pattern}   connectivity={card.is_connectivity}")
    print(f"  Top hypothesis: {card.hypotheses[0]['cause'] if card.hypotheses else '—'}")
    hint = rca.to_whatif_bridge(card)
    print(f"  → Bridge correctly refuses OEE recovery: recoverable={hint.recoverable_ms} ms")
    print(f"     note: {hint.note}")


def demo_recurrence(adw):
    _rule("DEMO 3 · Cross-machine recurrence — systemic / facility faults")
    rec = rca.correlate_with_offline(rca.find_recurrence(stream=rca.build_event_stream(ad_df=adw)))
    if not len(rec):
        print("  (none)"); return
    print(f"  {len(rec)} systemic events (≥2 machines, same category, same hour). Top 5:")
    for r in rec.head(5).itertuples():
        print(f"    {r.bucket_start}  {r.category:18s} {r.facility_root:20s} "
              f"{r.n_machines:2d} machines  {r.total_hours:6.1f} h")
    top = rec.iloc[0]
    print(f"  ⇒ Largest: {top.category} hit {top.n_machines} machines "
          f"({top.total_hours:.0f} machine-h) — a {top.facility_root} issue, not 1 machine.")


def demo_whatif():
    _rule("DEMO 4 · What-If — reduce unplanned downtime, quantify OEE + money")
    base = oee.baseline(level=1)
    cand = base[(base.ProductSum > 0) & (base.UnPlannedStop > 0)] \
        .sort_values("UnPlannedStop", ascending=False)
    r = cand.iloc[0]
    print(f"  Baseline: {r.machine} {r.date}  "
          f"A={r.A:.3f} P={r.P:.3f} Q={r.Q:.3f} OEE={r.OEE:.3f}  "
          f"unplanned={r.UnPlannedStop/3.6e6:.1f}h pieces={r.ProductSum:.0f}")
    res = whatif.run_scenario(r, whatif.ScenarioSpec("W1", 0.5, "UNPLANNED_RUNSTOP"),
                              category_ms=r.UnPlannedStop)
    print(f"  W1 (−50% unplanned): A {res.before['A']:.3f}→{res.after['A']:.3f}  "
          f"OEE {res.before['OEE']:.3f}→{res.after['OEE']:.3f}  "
          f"(ΔOEE {res.delta['dOEE']:+.3f})")
    print("  ΔOEE waterfall:")
    for label, val in whatif.waterfall_rows(res.before, res.after):
        print(f"    {label:14s} {val:+.4f}" if label.startswith("Δ") else f"    {label:14s} {val:.4f}")
    fin = whatif.compute_financials(res, whatif.FinancialAssumptions(), period_days=1)
    print(f"  Financials (ASSUMED): recovered {fin.recovered_hours:.1f}h, "
          f"extra {fin.extra_pieces:.0f} pcs → gross {fin.gross_benefit:,.0f} / "
          f"net {fin.net_benefit:,.0f} TRY, payback "
          f"{'—' if fin.payback_days is None else f'{fin.payback_days:.1f}d'}")


def demo_ad(adw):
    _rule("DEMO 5 · Anomaly Detection — leading indicator before a labeled event")
    if adw is None or not len(adw):
        print("  (AD not built — run scripts/build_ad.py)"); return
    # Makine 7 (rich Mitsubishi) top window with a downstream labeled event
    linked = adw[(adw.machine == "Makine 7") & adw.nearest_label.notna()] \
        .sort_values("peak_score", ascending=False)
    w = linked.iloc[0] if len(linked) else adw.sort_values("peak_score", ascending=False).iloc[0]
    print(f"  {w.machine}: anomaly window {w.window_start} → {w.window_end}")
    print(f"    peak score {w.peak_score:.0f}/100  detector={w.detector}")
    print(f"    deviating roles: {w.top_roles}")
    print(f"    nearest downstream labeled event: {w.nearest_label}  "
          f"(lead {w.lead_time_min:.0f} min)" if pd.notna(w.nearest_label) else "")
    # machine-level eval headline
    sc = pd.read_parquet(ART / "ad_scores.parquet"); sc["ts"] = pd.to_datetime(sc.ts, utc=True)
    summ = adeval.summarize(sc, labels.anomaly_label_windows(), labels.offline_windows())
    m7 = summ[summ.machine == "Makine 7"]
    if len(m7):
        print(f"  Makine 7 overall: {int(m7.n_events.iloc[0])} events, "
              f"{m7.pct_with_warning.iloc[0]:.0f}% got early warning "
              f"(median lead {m7.median_lead_min.iloc[0]:.0f} min)")


def main(which):
    adw = _ad_windows()
    if which in ("all", "rca"):
        demo_rca(adw)
    if which in ("all", "conn"):
        demo_connectivity(adw)
    if which in ("all", "recur"):
        demo_recurrence(adw)
    if which in ("all", "whatif"):
        demo_whatif()
    if which in ("all", "ad"):
        demo_ad(adw)
    print("\n(Interactive demo: uv run streamlit run app/Home.py)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
