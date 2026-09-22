from dataclasses import asdict
from uuid import UUID

from sqlalchemy.orm import Session

from src.application.customers.use_cases import get_customer
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

    if machine_id is not None:
        machine = get_machine(db, organization_id=organization_id, machine_id=machine_id)
        effective_machine_cost_per_hour = machine.cost_per_hour or 0.0
    else:
        effective_machine_cost_per_hour = machine_cost_per_hour or 0.0

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
            profit_margin_percentage=profile.profit_margin_percentage,
            tax_percentage=profile.tax_percentage or 0.0,
        ),
    )

    quote = QuoteRepository(db).create(
        organization_id=organization_id,
        cost_profile_id=cost_profile_id,
        project_version_id=project_version_id,
        customer_id=customer_id,
        created_by=created_by,
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
