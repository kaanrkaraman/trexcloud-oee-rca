"""Financial impact layer. The dump contains NO cost/price data, so every output is
driven by user assumptions and labeled as such.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field

ASSUMPTION_LABEL = ("USER-PROVIDED ASSUMPTIONS — the dataset contains NO cost/price data; "
                    "treat all currency figures as hypotheses, not facts.")


@dataclass
class FinancialAssumptions:
    contribution_margin_per_piece: float = 12.0
    machine_hour_cost: float = 45.0
    downtime_cost_per_hour: float = 80.0
    scrap_cost_per_piece: float = 18.0
    intervention_cost: float = 300.0
    horizon_days: int = 30
    currency: str = "EUR"
    value_recovered_time_as: str = "margin"   # "margin" | "downtime_cost" (avoid double count)


@dataclass
class FinancialResult:
    recovered_hours: float
    extra_pieces: float
    gross_benefit: float
    net_benefit: float
    payback_days: float | None
    roi: float | None
    breakdown: dict
    assumptions: dict
    label: str = ASSUMPTION_LABEL


def compute_financials(result, assm: FinancialAssumptions, *, period_days: int = 1,
                       avoided_scrap_pieces: float = 0.0) -> FinancialResult:
    """`result`: a ScenarioResult (or object with recovered_runtime_ms & extra_pieces)."""
    recovered_h = getattr(result, "recovered_runtime_ms", 0.0) / 3.6e6
    extra_pieces = float(getattr(result, "extra_pieces", 0.0))

    margin_gain = extra_pieces * assm.contribution_margin_per_piece
    downtime_saving = recovered_h * assm.downtime_cost_per_hour
    scrap_saving = avoided_scrap_pieces * assm.scrap_cost_per_piece

    # avoid double-counting recovered time: value it ONE way
    time_value = margin_gain if assm.value_recovered_time_as == "margin" else downtime_saving
    gross_daily = time_value + scrap_saving
    horizon = assm.horizon_days
    gross_horizon = gross_daily * (horizon / max(period_days, 1))
    net_horizon = gross_horizon - assm.intervention_cost

    payback = (assm.intervention_cost / gross_daily) if gross_daily > 0 else None
    roi = (net_horizon / assm.intervention_cost) if assm.intervention_cost > 0 else None

    breakdown = {
        "margin_gain_per_period": round(margin_gain, 2),
        "downtime_saving_per_period": round(downtime_saving, 2),
        "scrap_saving_per_period": round(scrap_saving, 2),
        "valued_time_as": assm.value_recovered_time_as,
        "gross_per_period": round(gross_daily, 2),
        f"gross_over_{horizon}d": round(gross_horizon, 2),
        "intervention_cost": assm.intervention_cost,
    }
    return FinancialResult(round(recovered_h, 3), round(extra_pieces, 1),
                           round(gross_horizon, 2), round(net_horizon, 2),
                           round(payback, 2) if payback is not None else None,
                           round(roi, 2) if roi is not None else None,
                           breakdown, asdict(assm))
