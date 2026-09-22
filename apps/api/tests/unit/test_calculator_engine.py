import pytest

from src.domain.calculator.engine import calculate_quote
from src.domain.calculator.inputs import QuoteInputs
from src.domain.calculator.profile import CostProfileValues
from src.domain.shared.exceptions import InvalidCostInputsError

_ZERO_PROFILE = CostProfileValues(
    energy_cost_per_kwh=0.0,
    labor_cost_per_hour=0.0,
    packaging_cost_flat=0.0,
    waste_percentage=0.0,
    fees_percentage=0.0,
    profit_margin_percentage=0.0,
    tax_percentage=0.0,
)

_ZERO_INPUTS = QuoteInputs(
    material_cost=0.0,
    print_time_hours=0.0,
    machine_cost_per_hour=0.0,
    energy_kwh=0.0,
    labor_hours=0.0,
)


def test_all_zero_inputs_produce_zero_price():
    report = calculate_quote(_ZERO_INPUTS, _ZERO_PROFILE)
    assert report.production_cost == 0.0
    assert report.suggested_price == 0.0


def test_material_cost_only_with_no_margin_passes_through():
    inputs = QuoteInputs(
        material_cost=10.0, print_time_hours=0.0, machine_cost_per_hour=0.0,
        energy_kwh=0.0, labor_hours=0.0,
    )
    report = calculate_quote(inputs, _ZERO_PROFILE)
    assert report.material_cost == 10.0
    assert report.waste_cost == 0.0
    assert report.production_cost == pytest.approx(10.0)
    assert report.suggested_price == pytest.approx(10.0)


def test_waste_percentage_only_inflates_material_cost():
    inputs = QuoteInputs(
        material_cost=10.0, print_time_hours=0.0, machine_cost_per_hour=0.0,
        energy_kwh=0.0, labor_hours=0.0,
    )
    profile = CostProfileValues(
        energy_cost_per_kwh=0.0, labor_cost_per_hour=0.0, packaging_cost_flat=0.0,
        waste_percentage=10.0, fees_percentage=0.0, profit_margin_percentage=0.0,
        tax_percentage=0.0,
    )
    report = calculate_quote(inputs, profile)
    assert report.waste_cost == pytest.approx(1.0)
    assert report.production_cost == pytest.approx(11.0)


def test_profit_margin_and_tax_apply_after_production_cost():
    inputs = QuoteInputs(
        material_cost=100.0, print_time_hours=0.0, machine_cost_per_hour=0.0,
        energy_kwh=0.0, labor_hours=0.0,
    )
    profile = CostProfileValues(
        energy_cost_per_kwh=0.0, labor_cost_per_hour=0.0, packaging_cost_flat=0.0,
        waste_percentage=0.0, fees_percentage=0.0, profit_margin_percentage=50.0,
        tax_percentage=10.0,
    )
    report = calculate_quote(inputs, profile)
    assert report.production_cost == pytest.approx(100.0)
    assert report.tax_amount == pytest.approx(15.0)  # 10% of (100 * 1.5)
    assert report.suggested_price == pytest.approx(165.0)


def test_breakdown_line_items_sum_to_production_cost():
    inputs = QuoteInputs(
        material_cost=10.0, print_time_hours=2.0, machine_cost_per_hour=1.5,
        energy_kwh=0.4, labor_hours=0.5,
    )
    profile = CostProfileValues(
        energy_cost_per_kwh=0.9, labor_cost_per_hour=20.0, packaging_cost_flat=3.0,
        waste_percentage=5.0, fees_percentage=3.0, profit_margin_percentage=40.0,
        tax_percentage=0.0,
    )
    report = calculate_quote(inputs, profile)
    line_items_total = (
        report.material_cost
        + report.waste_cost
        + report.energy_cost
        + report.machine_cost
        + report.labor_cost
        + report.packaging_cost
        + report.fees
    )
    assert line_items_total == pytest.approx(report.production_cost)


@pytest.mark.parametrize(
    "inputs",
    [
        QuoteInputs(
            material_cost=-1.0, print_time_hours=0.0, machine_cost_per_hour=0.0,
            energy_kwh=0.0, labor_hours=0.0,
        ),
        QuoteInputs(
            material_cost=0.0, print_time_hours=-2.0, machine_cost_per_hour=0.0,
            energy_kwh=0.0, labor_hours=0.0,
        ),
    ],
)
def test_negative_input_is_rejected(inputs):
    with pytest.raises(InvalidCostInputsError):
        calculate_quote(inputs, _ZERO_PROFILE)


def test_negative_profile_factor_is_rejected():
    profile = CostProfileValues(
        energy_cost_per_kwh=0.0, labor_cost_per_hour=0.0, packaging_cost_flat=0.0,
        waste_percentage=-5.0, fees_percentage=0.0, profit_margin_percentage=0.0,
        tax_percentage=0.0,
    )
    with pytest.raises(InvalidCostInputsError):
        calculate_quote(_ZERO_INPUTS, profile)
