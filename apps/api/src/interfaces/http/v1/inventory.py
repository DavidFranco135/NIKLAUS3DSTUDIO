from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.application.inventory import use_cases as inventory_use_cases
from src.domain.auth.roles import Role
from src.domain.inventory.alerts import is_low_stock
from src.domain.shared.exceptions import DomainError
from src.infrastructure.db.models import InventoryItem, User
from src.interfaces.http.dependencies import get_current_user, get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    CreateInventoryItemRequest,
    CreateInventoryMovementRequest,
    InventoryItemResponse,
    InventoryMovementResponse,
)

router = APIRouter(prefix="/organizations/{organization_id}/inventory-items", tags=["inventory"])


def _to_response(item: InventoryItem) -> InventoryItemResponse:
    response = InventoryItemResponse.model_validate(item)
    response.is_low_stock = is_low_stock(item.quantity_on_hand, item.minimum_stock)
    return response


@router.post(
    "",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def create_inventory_item(
    organization_id: UUID, payload: CreateInventoryItemRequest, db: Session = Depends(get_db)
) -> InventoryItemResponse:
    try:
        item = inventory_use_cases.create_inventory_item(
            db,
            organization_id=organization_id,
            material_id=payload.material_id,
            name=payload.name,
            category=payload.category,
            unit=payload.unit,
            minimum_stock=payload.minimum_stock,
            unit_cost=payload.unit_cost,
            supplier=payload.supplier,
            initial_quantity=payload.initial_quantity,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return _to_response(item)


@router.get(
    "",
    response_model=list[InventoryItemResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_inventory_items(
    organization_id: UUID,
    db: Session = Depends(get_db),
    low_stock_only: bool = Query(default=False),
) -> list[InventoryItemResponse]:
    items = inventory_use_cases.list_inventory_items(
        db, organization_id=organization_id, low_stock_only=low_stock_only
    )
    return [_to_response(i) for i in items]


@router.get(
    "/{item_id}",
    response_model=InventoryItemResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_inventory_item(
    organization_id: UUID, item_id: UUID, db: Session = Depends(get_db)
) -> InventoryItemResponse:
    try:
        item = inventory_use_cases.get_inventory_item(
            db, organization_id=organization_id, item_id=item_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return _to_response(item)


@router.post(
    "/{item_id}/movements",
    response_model=InventoryMovementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def create_movement(
    organization_id: UUID,
    item_id: UUID,
    payload: CreateInventoryMovementRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InventoryMovementResponse:
    try:
        movement = inventory_use_cases.create_movement(
            db,
            organization_id=organization_id,
            item_id=item_id,
            movement_type=payload.type,
            quantity=payload.quantity,
            unit_cost=payload.unit_cost,
            notes=payload.notes,
            created_by=current_user.id,
            reference_order_id=payload.reference_order_id,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return InventoryMovementResponse.model_validate(movement)


@router.get(
    "/{item_id}/movements",
    response_model=list[InventoryMovementResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_movements(
    organization_id: UUID, item_id: UUID, db: Session = Depends(get_db)
) -> list[InventoryMovementResponse]:
    try:
        movements = inventory_use_cases.list_movements(
            db, organization_id=organization_id, item_id=item_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return [InventoryMovementResponse.model_validate(m) for m in movements]
