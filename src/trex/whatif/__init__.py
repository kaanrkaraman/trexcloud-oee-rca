"""What-If / OEE simulation + financial impact."""
from . import scenarios, decompose, financials  # noqa: F401
from .scenarios import ScenarioSpec, ScenarioResult, run_scenario, run_scenario_range
from .decompose import decompose_oee, waterfall_rows
from .financials import FinancialAssumptions, FinancialResult, compute_financials, ASSUMPTION_LABEL

__all__ = ["scenarios", "decompose", "financials", "ScenarioSpec", "ScenarioResult",
           "run_scenario", "run_scenario_range", "decompose_oee", "waterfall_rows",
           "FinancialAssumptions", "FinancialResult", "compute_financials", "ASSUMPTION_LABEL"]
