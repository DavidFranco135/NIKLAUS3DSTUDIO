from dataclasses import dataclass


@dataclass(frozen=True)
class CostProfileValues:
    """The configurable policy factors behind a price — mirrors the

    `cost_profiles` table (DATABASE.md), but as a plain value object so the
    calculator itself never touches the ORM/DB. Percentages are whole
    numbers (e.g. `15.0` for 15%), not fractions.
    """

    energy_cost_per_kwh: float
    labor_cost_per_hour: float
    packaging_cost_flat: float
    waste_percentage: float
    fees_percentage: float
    profit_margin_percentage: float
    tax_percentage: float = 0.0
