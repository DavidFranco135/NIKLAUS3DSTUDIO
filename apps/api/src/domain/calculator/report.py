from dataclasses import dataclass


@dataclass(frozen=True)
class CostBreakdown:
    material_cost: float
    waste_cost: float
    energy_cost: float
    machine_cost: float
    labor_cost: float
    packaging_cost: float
    fees: float
    production_cost: float
    tax_amount: float
    suggested_price: float
