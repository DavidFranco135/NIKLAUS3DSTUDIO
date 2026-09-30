from dataclasses import asdict
from uuid import UUID

from sqlalchemy.orm import Session

from src.application.customers.use_cases import get_customer
from src.application.inventory.use_cases import get_material
from src.application.machines.use_cases import get_machine
from src.application.projects.use_cases import get_project
from src.domain.calculator.engine import calculate_quote
from src.domain.calculator.inputs import QuoteInputs
from src.domain.calculator.profile import CostProfileValues
from src.domain.shared.exceptions import (
    CostProfileNotFoundError,
    ProjectVersionNotFoundError,
    QuoteNotFoundError,
)
from src.infrastructure.db.models import CostProfile, Quote
from src.infrastructure.db.repositories import (
    CostProfileRepository,
    ProjectVersionRepository,
    QuoteRepository,
)


def create_cost_profile(
    db: Session,
    *,
    organization_id: UUID,
    name: str,
    energy_cost_per_kwh: float,
    labor_cost_per_hour: float,
    packaging_cost_flat: float,
    waste_percentage: float,
    fees_percentage: float,
    profit_margin_percentage: float,
    tax_percentage: float | None,
    is_default: bool,
) -> CostProfile:
    repo = CostProfileRepository(db)
    if is_default:
        repo.clear_default(organization_id)
    profile = repo.create(
        organization_id=organization_id,
        name=name,
        energy_cost_per_kwh=energy_cost_per_kwh,
        labor_cost_per_hour=labor_cost_per_hour,
        packaging_cost_flat=packaging_cost_flat,
        waste_percentage=waste_percentage,
        fees_percentage=fees_percentage,
        profit_margin_percentage=profit_margin_percentage,
        tax_percentage=tax_percentage,
        is_default=is_default,
    )
    db.commit()
    return profile


def list_cost_profiles(db: Session, *, organization_id: UUID) -> list[CostProfile]:
    return CostProfileRepository(db).list_for_org(organization_id)


def get_cost_profile(db: Session, *, organization_id: UUID, cost_profile_id: UUID) -> CostProfile:
    profile = CostProfileRepository(db).get(organization_id, cost_profile_id)
    if profile is None:
        raise CostProfileNotFoundError(str(cost_profile_id))
    return profile


def update_cost_profile(
    db: Session,
    *,
    organization_id: UUID,
    cost_profile_id: UUID,
    name: str | None,
    energy_cost_per_kwh: float | None,
    labor_cost_per_hour: float | None,
    packaging_cost_flat: float | None,
    waste_percentage: float | None,
    fees_percentage: float | None,
    profit_margin_percentage: float | None,
    tax_percentage: float | None,
    is_default: bool | None,
) -> CostProfile:
    profile = get_cost_profile(
        db, organization_id=organization_id, cost_profile_id=cost_profile_id
    )
    repo = CostProfileRepository(db)
    if is_default is True:
        repo.clear_default(organization_id)
    if name is not None:
        profile.name = name
    if energy_cost_per_kwh is not None:
        profile.energy_cost_per_kwh = energy_cost_per_kwh
    if labor_cost_per_hour is not None:
        profile.labor_cost_per_hour = labor_cost_per_hour
    if packaging_cost_flat is not None:
        profile.packaging_cost_flat = packaging_cost_flat
    if waste_percentage is not None:
        profile.waste_percentage = waste_percentage
    if fees_percentage is not None:
        profile.fees_percentage = fees_percentage
    if profit_margin_percentage is not None:
        profile.profit_margin_percentage = profit_margin_percentage
    if tax_percentage is not None:
        profile.tax_percentage = tax_percentage
    if is_default is not None:
        profile.is_default = is_default
    db.commit()
    return profile


def delete_cost_profile(db: Session, *, organization_id: UUID, cost_profile_id: UUID) -> None:
    profile = get_cost_profile(
        db, organization_id=organization_id, cost_profile_id=cost_profile_id
    )
    CostProfileRepository(db).soft_delete(profile)
    db.commit()


def create_quote(
    db: Session,
    *,
    organization_id: UUID,
    cost_profile_id: UUID,
    project_id: UUID | None,
    project_version_id: UUID | None,
    customer_id: UUID | None,
    created_by: UUID | None,
    material_cost: float,
    print_time_hours: float,
    machine_cost_per_hour: float | None = None,
    machine_id: UUID | None = None,
    energy_kwh: float,
    labor_hours: float,
    piece_name: str | None = None,
    printer_name: str | None = None,
    weight_g: float | None = None,
    quantity: int = 1,
    profit_margin_percentage: float | None = None,
    material_id: UUID | None = None,
    cost_per_kg: float | None = None,
    extra_items: list[dict] | None = None,
    depreciation_mode: str | None = None,
    depreciation_value: float | None = None,
) -> Quote:
    profile = get_cost_profile(db, organization_id=organization_id, cost_profile_id=cost_profile_id)

    if customer_id is not None:
        get_customer(db, organization_id=organization_id, customer_id=customer_id)

    if project_version_id is not None:
        if project_id is None:
            raise ProjectVersionNotFoundError(str(project_version_id))
        get_project(db, organization_id=organization_id, project_id=project_id)
        version = ProjectVersionRepository(db).get(project_id, project_version_id)
        if version is None:
            raise ProjectVersionNotFoundError(str(project_version_id))

    # machine_id is stored for display/edit-repopulation only — the actual
    # machine cost always comes from machine_cost_per_hour (the depreciation
    # value the Peça tab computed, which may have been hand-edited away from
    # the printer's own default), mirroring update_quote's behavior.
    if machine_id is not None:
        get_machine(db, organization_id=organization_id, machine_id=machine_id)
    effective_machine_cost_per_hour = machine_cost_per_hour or 0.0

    if material_id is not None:
        get_material(db, organization_id=organization_id, material_id=material_id)

    resolved_margin = (
        profit_margin_percentage
        if profit_margin_percentage is not None
        else profile.profit_margin_percentage
    )

    breakdown = calculate_quote(
        QuoteInputs(
            material_cost=material_cost,
            print_time_hours=print_time_hours,
            machine_cost_per_hour=effective_machine_cost_per_hour,
            energy_kwh=energy_kwh,
            labor_hours=labor_hours,
        ),
        CostProfileValues(
            energy_cost_per_kwh=profile.energy_cost_per_kwh,
            labor_cost_per_hour=profile.labor_cost_per_hour,
            packaging_cost_flat=profile.packaging_cost_flat,
            waste_percentage=profile.waste_percentage,
            fees_percentage=profile.fees_percentage,
            profit_margin_percentage=resolved_margin,
            tax_percentage=profile.tax_percentage or 0.0,
        ),
    )

    quote = QuoteRepository(db).create(
        organization_id=organization_id,
        cost_profile_id=cost_profile_id,
        project_version_id=project_version_id,
        customer_id=customer_id,
        created_by=created_by,
        piece_name=piece_name,
        printer_name=printer_name,
        machine_id=machine_id,
        material_id=material_id,
        weight_g=weight_g,
        cost_per_kg=cost_per_kg,
        extra_items=[dict(item) for item in extra_items] if extra_items is not None else None,
        print_time_hours=print_time_hours,
        depreciation_mode=depreciation_mode,
        depreciation_value=depreciation_value,
        labor_hours=labor_hours,
        profit_margin_percentage=resolved_margin,
        quantity=quantity,
        cost_breakdown_snapshot=asdict(breakdown),
        production_cost=breakdown.production_cost,
        suggested_price=breakdown.suggested_price,
    )
    db.commit()
    return quote


def list_quotes(db: Session, *, organization_id: UUID) -> list[Quote]:
    return QuoteRepository(db).list_for_org(organization_id)


def get_quote(db: Session, *, organization_id: UUID, quote_id: UUID) -> Quote:
    quote = QuoteRepository(db).get(organization_id, quote_id)
    if quote is None:
        raise QuoteNotFoundError(str(quote_id))
    return quote


def update_quote(
    db: Session,
    *,
    organization_id: UUID,
    quote_id: UUID,
    piece_name: str | None,
    printer_name: str | None,
    machine_id: UUID | None,
    material_id: UUID | None,
    weight_g: float | None,
    cost_per_kg: float | None,
    extra_items: list[dict] | None,
    print_time_hours: float | None,
    depreciation_mode: str | None,
    depreciation_value: float | None,
    labor_hours: float | None,
    profit_margin_percentage: float | None,
    quantity: int | None,
    final_price: float | None,
) -> Quote:
    """Edits a saved piece using the exact same inputs as creating one, and

    re-runs the pricing engine so the breakdown reflects the edited values —
    this mirrors the Peça tab's form so editing is just as capable as
    creating. Any field left out (None) keeps its previously stored value.
    `final_price` is a separate manual override, untouched by recomputation.
    """
    quote = get_quote(db, organization_id=organization_id, quote_id=quote_id)
    profile = get_cost_profile(
        db, organization_id=organization_id, cost_profile_id=quote.cost_profile_id
    )

    resolved_machine_id = machine_id if machine_id is not None else quote.machine_id
    resolved_material_id = material_id if material_id is not None else quote.material_id
    resolved_weight_g = weight_g if weight_g is not None else (quote.weight_g or 0.0)
    resolved_cost_per_kg = cost_per_kg if cost_per_kg is not None else (quote.cost_per_kg or 0.0)
    resolved_extra_items = extra_items if extra_items is not None else (quote.extra_items or [])
    resolved_print_time_hours = (
        print_time_hours if print_time_hours is not None else (quote.print_time_hours or 0.0)
    )
    resolved_depreciation_mode = depreciation_mode or quote.depreciation_mode or "hora"
    resolved_depreciation_value = (
        depreciation_value if depreciation_value is not None else (quote.depreciation_value or 0.0)
    )
    resolved_labor_hours = labor_hours if labor_hours is not None else (quote.labor_hours or 0.0)
    resolved_margin = (
        profit_margin_percentage
        if profit_margin_percentage is not None
        else (quote.profit_margin_percentage if quote.profit_margin_percentage is not None
              else profile.profit_margin_percentage)
    )
    resolved_quantity = quantity if quantity is not None else quote.quantity

    if resolved_material_id is not None:
        get_material(db, organization_id=organization_id, material_id=resolved_material_id)

    # Mirrors the Peça tab's client-side logic exactly: the depreciation
    # value the user typed (pre-filled from the printer, but editable)
    # always drives the machine cost — a selected printer only supplies its
    # wattage, for the automatic energy-cost calculation below.
    power_watts = None
    if resolved_machine_id is not None:
        machine = get_machine(db, organization_id=organization_id, machine_id=resolved_machine_id)
        power_watts = machine.power_watts

    if resolved_depreciation_mode == "hora":
        effective_machine_cost_per_hour = resolved_depreciation_value
    else:
        effective_machine_cost_per_hour = (
            resolved_depreciation_value / resolved_print_time_hours
            if resolved_print_time_hours
            else resolved_depreciation_value
        )

    energy_kwh = (
        (power_watts / 1000) * resolved_print_time_hours
        if power_watts is not None
        else 0.0
    )

    extra_items_cost = sum(item.get("cost", 0) or 0 for item in resolved_extra_items)
    material_cost = (resolved_weight_g / 1000) * resolved_cost_per_kg + extra_items_cost

    breakdown = calculate_quote(
        QuoteInputs(
            material_cost=material_cost,
            print_time_hours=resolved_print_time_hours,
            machine_cost_per_hour=effective_machine_cost_per_hour,
            energy_kwh=energy_kwh,
            labor_hours=resolved_labor_hours,
        ),
        CostProfileValues(
            energy_cost_per_kwh=profile.energy_cost_per_kwh,
            labor_cost_per_hour=profile.labor_cost_per_hour,
            packaging_cost_flat=profile.packaging_cost_flat,
            waste_percentage=profile.waste_percentage,
            fees_percentage=profile.fees_percentage,
            profit_margin_percentage=resolved_margin,
            tax_percentage=profile.tax_percentage or 0.0,
        ),
    )

    if piece_name is not None:
        quote.piece_name = piece_name
    if printer_name is not None:
        quote.printer_name = printer_name
    quote.machine_id = resolved_machine_id
    quote.material_id = resolved_material_id
    quote.weight_g = resolved_weight_g
    quote.cost_per_kg = resolved_cost_per_kg
    quote.extra_items = resolved_extra_items
    quote.print_time_hours = resolved_print_time_hours
    quote.depreciation_mode = resolved_depreciation_mode
    quote.depreciation_value = resolved_depreciation_value
    quote.labor_hours = resolved_labor_hours
    quote.profit_margin_percentage = resolved_margin
    quote.quantity = resolved_quantity
    quote.cost_breakdown_snapshot = asdict(breakdown)
    quote.production_cost = breakdown.production_cost
    quote.suggested_price = breakdown.suggested_price
    if final_price is not None:
        quote.final_price = final_price
    db.commit()
    return quote


def delete_quote(db: Session, *, organization_id: UUID, quote_id: UUID) -> None:
    quote = get_quote(db, organization_id=organization_id, quote_id=quote_id)
    QuoteRepository(db).soft_delete(quote)
    db.commit()
