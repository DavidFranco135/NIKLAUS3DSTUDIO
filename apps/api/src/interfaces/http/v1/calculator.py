from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.application.calculator import use_cases as calculator_use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.infrastructure.db.models import User
from src.interfaces.http.dependencies import get_current_user, get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    CostProfileResponse,
    CreateCostProfileRequest,
    CreateQuoteRequest,
    QuoteResponse,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["calculator"])


@router.post(
    "/cost-profiles",
    response_model=CostProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def create_cost_profile(
    organization_id: UUID, payload: CreateCostProfileRequest, db: Session = Depends(get_db)
) -> CostProfileResponse:
    profile = calculator_use_cases.create_cost_profile(
        db,
        organization_id=organization_id,
        name=payload.name,
        energy_cost_per_kwh=payload.energy_cost_per_kwh,
        labor_cost_per_hour=payload.labor_cost_per_hour,
        packaging_cost_flat=payload.packaging_cost_flat,
        waste_percentage=payload.waste_percentage,
        fees_percentage=payload.fees_percentage,
        profit_margin_percentage=payload.profit_margin_percentage,
        tax_percentage=payload.tax_percentage,
        is_default=payload.is_default,
    )
    return CostProfileResponse.model_validate(profile)


@router.get(
    "/cost-profiles",
    response_model=list[CostProfileResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_cost_profiles(
    organization_id: UUID, db: Session = Depends(get_db)
) -> list[CostProfileResponse]:
    profiles = calculator_use_cases.list_cost_profiles(db, organization_id=organization_id)
    return [CostProfileResponse.model_validate(p) for p in profiles]


@router.get(
    "/cost-profiles/{cost_profile_id}",
    response_model=CostProfileResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_cost_profile(
    organization_id: UUID, cost_profile_id: UUID, db: Session = Depends(get_db)
) -> CostProfileResponse:
    try:
        profile = calculator_use_cases.get_cost_profile(
            db, organization_id=organization_id, cost_profile_id=cost_profile_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return CostProfileResponse.model_validate(profile)


@router.post(
    "/quotes",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def create_quote(
    organization_id: UUID,
    payload: CreateQuoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuoteResponse:
    try:
        quote = calculator_use_cases.create_quote(
            db,
            organization_id=organization_id,
            cost_profile_id=payload.cost_profile_id,
            project_id=payload.project_id,
            project_version_id=payload.project_version_id,
            customer_id=payload.customer_id,
            created_by=current_user.id,
            material_cost=payload.material_cost,
            print_time_hours=payload.print_time_hours,
            machine_cost_per_hour=payload.machine_cost_per_hour,
            machine_id=payload.machine_id,
            energy_kwh=payload.energy_kwh,
            labor_hours=payload.labor_hours,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return QuoteResponse.model_validate(quote)


@router.get(
    "/quotes",
    response_model=list[QuoteResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_quotes(organization_id: UUID, db: Session = Depends(get_db)) -> list[QuoteResponse]:
    quotes = calculator_use_cases.list_quotes(db, organization_id=organization_id)
    return [QuoteResponse.model_validate(q) for q in quotes]


@router.get(
    "/quotes/{quote_id}",
    response_model=QuoteResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_quote(
    organization_id: UUID, quote_id: UUID, db: Session = Depends(get_db)
) -> QuoteResponse:
    try:
        quote = calculator_use_cases.get_quote(
            db, organization_id=organization_id, quote_id=quote_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return QuoteResponse.model_validate(quote)
