from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.application.products import use_cases as product_use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.interfaces.http.dependencies import get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    CreateProductRequest,
    ProductCostResponse,
    ProductResponse,
)

router = APIRouter(prefix="/organizations/{organization_id}/products", tags=["products"])


def _to_response(db: Session, product) -> ProductResponse:
    materials = product_use_cases.list_product_materials(db, product_id=product.id)
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        print_time_hours=product.print_time_hours,
        machine_id=product.machine_id,
        is_active=product.is_active,
        created_at=product.created_at,
        materials=materials,
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def create_product(
    organization_id: UUID, payload: CreateProductRequest, db: Session = Depends(get_db)
) -> ProductResponse:
    try:
        product = product_use_cases.create_product(
            db,
            organization_id=organization_id,
            name=payload.name,
            description=payload.description,
            print_time_hours=payload.print_time_hours,
            machine_id=payload.machine_id,
            materials=[m.model_dump() for m in payload.materials],
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return _to_response(db, product)


@router.get(
    "",
    response_model=list[ProductResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_products(organization_id: UUID, db: Session = Depends(get_db)) -> list[ProductResponse]:
    products = product_use_cases.list_products(db, organization_id=organization_id)
    return [_to_response(db, p) for p in products]


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_product(
    organization_id: UUID, product_id: UUID, db: Session = Depends(get_db)
) -> ProductResponse:
    try:
        product = product_use_cases.get_product(
            db, organization_id=organization_id, product_id=product_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return _to_response(db, product)


@router.get(
    "/{product_id}/cost",
    response_model=ProductCostResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_product_cost(
    organization_id: UUID,
    product_id: UUID,
    cost_profile_id: UUID,
    energy_kwh: float = 0.0,
    labor_hours: float = 0.0,
    db: Session = Depends(get_db),
) -> ProductCostResponse:
    try:
        breakdown = product_use_cases.compute_product_cost(
            db,
            organization_id=organization_id,
            product_id=product_id,
            cost_profile_id=cost_profile_id,
            energy_kwh=energy_kwh,
            labor_hours=labor_hours,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ProductCostResponse(
        material_cost=breakdown.material_cost,
        waste_cost=breakdown.waste_cost,
        energy_cost=breakdown.energy_cost,
        machine_cost=breakdown.machine_cost,
        labor_cost=breakdown.labor_cost,
        packaging_cost=breakdown.packaging_cost,
        fees=breakdown.fees,
        production_cost=breakdown.production_cost,
        tax_amount=breakdown.tax_amount,
        suggested_price=breakdown.suggested_price,
    )
