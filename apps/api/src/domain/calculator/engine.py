from src.domain.calculator.inputs import QuoteInputs
from src.domain.calculator.profile import CostProfileValues
from src.domain.calculator.report import CostBreakdown
from src.domain.shared.exceptions import InvalidCostInputsError


def _require_non_negative(name: str, value: float) -> None:
    if value < 0:
        raise InvalidCostInputsError(f"{name} não pode ser negativo (recebido: {value}).")


def calculate_quote(inputs: QuoteInputs, profile: CostProfileValues) -> CostBreakdown:
    """100% deterministic — ARCHITECTURE.md §14. No AI call happens here;

    AI may only ever have *fed* one of these numbers upstream (e.g.
    extracting "PLA branco" from a prompt), never computed the math itself.

    Interpretation choices made explicit here (the one-line formula in the
    architecture doc doesn't disambiguate these), since none are used
    unless a `CostProfile` is explicitly configured that way:
    - `waste_percentage` is extra *material* budgeted for failed prints/
      purge — applied only to `material_cost`, not the whole subtotal.
    - `fees_percentage` (payment/marketplace fees, etc.) applies to the
      production subtotal (material-with-waste + energy + machine + labor +
      packaging), since the formula lists `fees` as a component of
      `production_cost`, before margin.
    - `tax_percentage` applies after the profit margin, to the price the
      customer would actually pay, not to the internal production cost.
    """
    for name, value in (
        ("material_cost", inputs.material_cost),
        ("print_time_hours", inputs.print_time_hours),
        ("machine_cost_per_hour", inputs.machine_cost_per_hour),
        ("energy_kwh", inputs.energy_kwh),
        ("labor_hours", inputs.labor_hours),
        ("energy_cost_per_kwh", profile.energy_cost_per_kwh),
        ("labor_cost_per_hour", profile.labor_cost_per_hour),
        ("packaging_cost_flat", profile.packaging_cost_flat),
        ("waste_percentage", profile.waste_percentage),
        ("fees_percentage", profile.fees_percentage),
        ("profit_margin_percentage", profile.profit_margin_percentage),
        ("tax_percentage", profile.tax_percentage),
    ):
        _require_non_negative(name, value)

    material_with_waste = inputs.material_cost * (1 + profile.waste_percentage / 100)
    waste_cost = material_with_waste - inputs.material_cost

    energy_cost = inputs.energy_kwh * profile.energy_cost_per_kwh
    machine_cost = inputs.print_time_hours * inputs.machine_cost_per_hour
    labor_cost = inputs.labor_hours * profile.labor_cost_per_hour
    packaging_cost = profile.packaging_cost_flat

    subtotal = material_with_waste + energy_cost + machine_cost + labor_cost + packaging_cost
    fees = subtotal * (profile.fees_percentage / 100)
    production_cost = subtotal + fees

    price_before_tax = production_cost * (1 + profile.profit_margin_percentage / 100)
    tax_amount = price_before_tax * (profile.tax_percentage / 100)
    suggested_price = price_before_tax + tax_amount

    return CostBreakdown(
        material_cost=inputs.material_cost,
        waste_cost=waste_cost,
        energy_cost=energy_cost,
        machine_cost=machine_cost,
        labor_cost=labor_cost,
        packaging_cost=packaging_cost,
        fees=fees,
        production_cost=production_cost,
        tax_amount=tax_amount,
        suggested_price=suggested_price,
    )
