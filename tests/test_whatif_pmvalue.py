import unittest

import pandas as pd

from trex import whatif


def component_row(machine="M1", unplanned_h=10, product=100):
    return {
        "machine": machine, "date": "2026-01-01",
        "WorkTotal": 100 * 3.6e6,
        "PlannedStop": 10 * 3.6e6,
        "UnPlannedStop": unplanned_h * 3.6e6,
        "WorkingTime": 80 * 3.6e6,
        "PlannedTime": 100 * 3.6e6,
        "ProductSum": product,
        "ScrapeSum": 0,
    }


class ScenarioTests(unittest.TestCase):
    def test_w2_absolute_duration_preserves_runtime(self):
        result = whatif.run_scenario(
            component_row(),
            whatif.ScenarioSpec("W2", pct=0.9, abs_ms=8 * 3.6e6))
        self.assertAlmostEqual(result.after["UnPlannedStop"], 2 * 3.6e6)
        self.assertAlmostEqual(result.after["PlannedStop"], 18 * 3.6e6)
        self.assertAlmostEqual(result.recovered_runtime_ms, 0)
        self.assertGreater(result.delta["dA"], 0)

    def test_absolute_adjustment_is_capped_by_category(self):
        result = whatif.run_scenario(
            component_row(),
            whatif.ScenarioSpec("W2", abs_ms=8 * 3.6e6),
            category_ms=3 * 3.6e6,
        )
        self.assertAlmostEqual(result.after["UnPlannedStop"], 7 * 3.6e6)
        self.assertAlmostEqual(result.after["PlannedStop"], 13 * 3.6e6)

    def test_w4_inert_without_production(self):
        result = whatif.run_scenario(component_row(product=0), whatif.ScenarioSpec("W4", 0.1))
        self.assertEqual(result.delta["dP"], 0)
        self.assertEqual(result.delta["dOEE"], 0)
        self.assertIn("INERT", result.assumptions_note)


class PMValueTests(unittest.TestCase):
    def setUp(self):
        self.scored = pd.DataFrame({
            "machine": ["Makine 1"] * 5,
            "ts": pd.to_datetime([
                "2026-01-01 09:00Z", "2026-01-01 09:30Z", "2026-01-01 09:59Z",
                "2026-01-01 10:00Z", "2026-01-01 10:30Z"]),
            "risk": [0.9, 0.1, 0.8, 0.99, 0.1],
            "y": [1, 1, 1, 0, 0],
        })

    def test_strict_window_excludes_boundaries(self):
        stops = pd.DataFrame({
            "machine": ["Makine 1"],
            "start": pd.to_datetime(["2026-01-01 10:00Z"]),
            "duration_ms": [3.6e6],
        })
        matched = whatif.match_stops(self.scored, stops, threshold=0.85, horizon_min=60)
        self.assertFalse(bool(matched.iloc[0]["caught"]))
        matched = whatif.match_stops(self.scored, stops, threshold=0.75, horizon_min=60)
        self.assertTrue(bool(matched.iloc[0]["caught"]))

    def test_missed_stop_and_duration_deduplication(self):
        windows = whatif.scored_windows(self.scored, 60)
        raw = pd.DataFrame({
            "machine": ["Makine 1", "Makine 1", "Makine 7"],
            "start": pd.to_datetime([
                "2026-01-01 10:00Z", "2026-01-01 10:00Z", "2026-01-01 10:00Z"]),
            "end": pd.to_datetime([
                "2026-01-01 11:00Z", "2026-01-01 11:00Z", "2026-01-01 11:00Z"]),
            "duration_ms": [30 * 3.6e6, 12 * 3.6e6, 3.6e6],
        })
        scoped = whatif.scope_significant_stops(raw, windows)
        self.assertEqual(len(scoped), 1)
        self.assertEqual(scoped.iloc[0]["duration_ms"], 24 * 3.6e6)
        matched = whatif.match_stops(self.scored, scoped, threshold=0.95)
        self.assertFalse(bool(matched.iloc[0]["caught"]))

    def test_effectiveness_is_capped_by_oee_unplanned(self):
        result = whatif.attributable_oee(component_row(unplanned_h=2), prevented_h=9)
        self.assertEqual(result["applied_prevented_h"], 2)
        self.assertGreater(result["delta"]["dOEE"], 0)
        self.assertEqual(result["delta"]["dP"], 0)
        self.assertEqual(result["delta"]["dQ"], 0)

    def test_annualization_and_roi(self):
        assumptions = whatif.FinancialAssumptions(
            downtime_cost_per_hour=80, intervention_cost=300,
            currency="EUR", value_recovered_time_as="downtime_cost")
        result = whatif.financial_projection(10, 2, 100, assumptions, annual_days=365)
        self.assertEqual(result["observed"]["gross_eur"], 800)
        self.assertEqual(result["observed"]["intervention_eur"], 600)
        self.assertAlmostEqual(result["observed"]["roi"], 1 / 3, places=4)
        self.assertAlmostEqual(result["annualized"]["prevented_h"], 36.5)

    def test_threshold_optimizer_uses_net_value(self):
        baseline = pd.DataFrame([{
            **component_row("Makine 1"),
            "date": pd.Timestamp("2026-01-01").date(),
            "trans_date": pd.Timestamp("2026-01-01T00:00:00Z"),
        }])
        stops = pd.DataFrame({
            "machine": ["Makine 1"],
            "start": pd.to_datetime(["2026-01-01 10:00Z"]),
            "duration_ms": [10 * 3.6e6],
        })
        pm = whatif.PMValueAssumptions(intervention_effectiveness=1, horizon_min=60)
        fin = whatif.FinancialAssumptions(
            downtime_cost_per_hour=1000, intervention_cost=1, currency="EUR",
            value_recovered_time_as="downtime_cost")
        sweep = whatif.threshold_sensitivity(
            self.scored, stops, baseline, 0.75, pm, fin, thresholds=[0.75, 0.95])
        self.assertEqual(sweep["economic_optimum"]["threshold"], 0.75)


if __name__ == "__main__":
    unittest.main()
