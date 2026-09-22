from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.application.orders import use_cases as order_use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.infrastructure.db.models import User
from src.interfaces.http.dependencies import get_current_user, get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    CreateOrderItemRequest,
    CreateOrderRequest,
    OrderItemResponse,
    OrderResponse,
    TransitionOrderStatusRequest,
)

router = APIRouter(prefix="/organizations/{organization_id}/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def create_order(
    organization_id: UUID,
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    try:
        order = order_use_cases.create_order(
            db,
            organization_id=organization_id,
            customer_id=payload.customer_id,
            quote_id=payload.quote_id,
            notes=payload.notes,
            created_by=current_user.id,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return OrderResponse.model_validate(order)


@router.get(
    "",
    response_model=list[OrderResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_orders(organization_id: UUID, db: Session = Depends(get_db)) -> list[OrderResponse]:
    orders = order_use_cases.list_orders(db, organization_id=organization_id)
    return [OrderResponse.model_validate(o) for o in orders]


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_order(
    organization_id: UUID, order_id: UUID, db: Session = Depends(get_db)
) -> OrderResponse:
    try:
        order = order_use_cases.get_order(db, organization_id=organization_id, order_id=order_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return OrderResponse.model_validate(order)


@router.post(
    "/{order_id}/transition",
    response_model=OrderResponse,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def transition_order_status(
    organization_id: UUID,
    order_id: UUID,
    payload: TransitionOrderStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    try:
        order = order_use_cases.transition_order_status(
            db,
            organization_id=organization_id,
            order_id=order_id,
            new_status=payload.status,
            triggered_by=current_user.id,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return OrderResponse.model_validate(order)


@router.post(
    "/{order_id}/items",
    response_model=OrderItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def add_order_item(
    organization_id: UUID,
    order_id: UUID,
    payload: CreateOrderItemRequest,
    db: Session = Depends(get_db),
) -> OrderItemResponse:
    try:
        item = order_use_cases.add_order_item(
            db,
            organization_id=organization_id,
            order_id=order_id,
            project_id=payload.project_id,
            project_version_id=payload.project_version_id,
            machine_id=payload.machine_id,
            material_id=payload.material_id,
            quantity=payload.quantity,
            unit_cost=payload.unit_cost,
            unit_price=payload.unit_price,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return OrderItemResponse.model_validate(item)


@router.get(
    "/{order_id}/items",
    response_model=list[OrderItemResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_order_items(
    organization_id: UUID, order_id: UUID, db: Session = Depends(get_db)
) -> list[OrderItemResponse]:
    try:
        items = order_use_cases.list_order_items(
            db, organization_id=organization_id, order_id=order_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return [OrderItemResponse.model_validate(i) for i in items]
