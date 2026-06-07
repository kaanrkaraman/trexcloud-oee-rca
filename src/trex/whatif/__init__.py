"""What-If / OEE simulation + financial impact."""
from . import scenarios, decompose, financials, pmvalue  # noqa: F401
from .scenarios import ScenarioSpec, ScenarioResult, run_scenario, run_scenario_range
from .decompose import decompose_oee, waterfall_rows
from .financials import FinancialAssumptions, FinancialResult, compute_financials, ASSUMPTION_LABEL
from .pmvalue import (PMValueAssumptions, aggregate_oee_window, attributable_oee,
                      evaluate_operating_point, financial_projection, match_stops,
                      scope_significant_stops, scored_windows, threshold_sensitivity)

__all__ = ["scenarios", "decompose", "financials", "ScenarioSpec", "ScenarioResult",
           "run_scenario", "run_scenario_range", "decompose_oee", "waterfall_rows",
           "FinancialAssumptions", "FinancialResult", "compute_financials", "ASSUMPTION_LABEL",
           "pmvalue", "PMValueAssumptions", "aggregate_oee_window", "attributable_oee",
           "evaluate_operating_point", "financial_projection", "match_stops",
           "scope_significant_stops", "scored_windows", "threshold_sensitivity"]
