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
    ProductCostItem,
    ProductCostResponse,
    ProductResponse,
    UpdateProductRequest,
)

router = APIRouter(prefix="/organizations/{organization_id}/products", tags=["products"])


def _to_response(db: Session, product) -> ProductResponse:
    materials = product_use_cases.list_product_materials(
        db, organization_id=product.organization_id, product_id=product.id
    )
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        print_time_hours=product.print_time_hours,
        machine_id=product.machine_id,
        manual_price=product.manual_price,
        size=product.size,
        photo_urls=product.photo_urls,
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
            manual_price=payload.manual_price,
            size=payload.size,
            photo_urls=payload.photo_urls,
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
    "/costs",
    response_model=list[ProductCostItem],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_products_costs(
    organization_id: UUID, cost_profile_id: UUID, db: Session = Depends(get_db)
) -> list[ProductCostItem]:
    """One request for every product's cost, instead of the frontend firing

    one `/products/{id}/cost` call per product — see
    `product_use_cases.list_products_costs`'s docstring.
    """
    try:
        breakdowns = product_use_cases.list_products_costs(
            db, organization_id=organization_id, cost_profile_id=cost_profile_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return [
        ProductCostItem(
            product_id=product_id,
            material_cost=b.material_cost,
            waste_cost=b.waste_cost,
            energy_cost=b.energy_cost,
            machine_cost=b.machine_cost,
            labor_cost=b.labor_cost,
            packaging_cost=b.packaging_cost,
            fees=b.fees,
            production_cost=b.production_cost,
            tax_amount=b.tax_amount,
            suggested_price=b.suggested_price,
        )
        for product_id, b in breakdowns.items()
    ]


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


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def update_product(
    organization_id: UUID,
    product_id: UUID,
    payload: UpdateProductRequest,
    db: Session = Depends(get_db),
) -> ProductResponse:
    try:
        product = product_use_cases.update_product(
            db,
            organization_id=organization_id,
            product_id=product_id,
            name=payload.name,
            description=payload.description,
            print_time_hours=payload.print_time_hours,
            machine_id=payload.machine_id,
            manual_price=payload.manual_price,
            size=payload.size,
            photo_urls=payload.photo_urls,
            materials=(
                [m.model_dump() for m in payload.materials]
                if payload.materials is not None
                else None
            ),
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return _to_response(db, product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def delete_product(organization_id: UUID, product_id: UUID, db: Session = Depends(get_db)) -> None:
    try:
        product_use_cases.delete_product(
            db, organization_id=organization_id, product_id=product_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
