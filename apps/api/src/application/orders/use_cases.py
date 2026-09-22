from uuid import UUID

from sqlalchemy.orm import Session

from src.application.customers.use_cases import get_customer
from src.application.financial.use_cases import record_order_paid
from src.application.inventory.use_cases import get_material
from src.application.machines.use_cases import get_machine
from src.application.projects.use_cases import get_project
from src.domain.orders.status import validate_transition
from src.domain.orders.totals import OrderItemTotal, compute_total_amount
from src.domain.shared.exceptions import (
    OrderNotFoundError,
    ProjectVersionNotFoundError,
    QuoteNotFoundError,
)
from src.infrastructure.db.models import Order, OrderItem
from src.infrastructure.db.repositories import (
    OrderItemRepository,
    OrderRepository,
    ProjectVersionRepository,
    QuoteRepository,
)


def create_order(
    db: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
    quote_id: UUID | None,
    notes: str | None,
    created_by: UUID | None,
) -> Order:
    get_customer(db, organization_id=organization_id, customer_id=customer_id)

    total_amount = 0.0
    if quote_id is not None:
        quote_repo = QuoteRepository(db)
        quote = quote_repo.get(organization_id, quote_id)
        if quote is None:
            raise QuoteNotFoundError(str(quote_id))
        total_amount = quote.final_price if quote.final_price is not None else quote.suggested_price
        quote.status = "accepted"

    order = OrderRepository(db).create(
        organization_id=organization_id,
        customer_id=customer_id,
        quote_id=quote_id,
        total_amount=total_amount,
        notes=notes,
        created_by=created_by,
    )
    db.commit()
    return order


def list_orders(db: Session, *, organization_id: UUID) -> list[Order]:
    return OrderRepository(db).list_for_org(organization_id)


def get_order(db: Session, *, organization_id: UUID, order_id: UUID) -> Order:
    order = OrderRepository(db).get(organization_id, order_id)
    if order is None:
        raise OrderNotFoundError(str(order_id))
    return order


def transition_order_status(
    db: Session,
    *,
    organization_id: UUID,
    order_id: UUID,
    new_status: str,
    triggered_by: UUID | None = None,
) -> Order:
    order = get_order(db, organization_id=organization_id, order_id=order_id)
    validate_transition(order.status, new_status)
    OrderRepository(db).update_status(order, new_status=new_status)
    if new_status == "paid":
        record_order_paid(
            db,
            organization_id=organization_id,
            order_id=order.id,
            amount=order.total_amount,
            created_by=triggered_by,
        )
    db.commit()
    return order


def add_order_item(
    db: Session,
    *,
    organization_id: UUID,
    order_id: UUID,
    project_id: UUID | None,
    project_version_id: UUID | None,
    machine_id: UUID | None,
    material_id: UUID | None,
    quantity: int,
    unit_cost: float | None,
    unit_price: float | None,
) -> OrderItem:
    order = get_order(db, organization_id=organization_id, order_id=order_id)

    if project_version_id is not None:
        if project_id is None:
            raise ProjectVersionNotFoundError(str(project_version_id))
        get_project(db, organization_id=organization_id, project_id=project_id)
        version = ProjectVersionRepository(db).get(project_id, project_version_id)
        if version is None:
            raise ProjectVersionNotFoundError(str(project_version_id))

    if material_id is not None:
        get_material(db, organization_id=organization_id, material_id=material_id)

    if machine_id is not None:
        get_machine(db, organization_id=organization_id, machine_id=machine_id)

    item_repo = OrderItemRepository(db)
    item_repo.create(
        order_id=order.id,
        organization_id=organization_id,
        project_version_id=project_version_id,
        machine_id=machine_id,
        material_id=material_id,
        quantity=quantity,
        unit_cost=unit_cost,
        unit_price=unit_price,
    )

    items = item_repo.list_for_order(order.id)
    new_total = compute_total_amount(
        [OrderItemTotal(quantity=i.quantity, unit_price=i.unit_price) for i in items]
    )
    OrderRepository(db).update_total_amount(order, total_amount=new_total)
    db.commit()
    return item_repo.list_for_order(order.id)[-1]


def list_order_items(db: Session, *, organization_id: UUID, order_id: UUID) -> list[OrderItem]:
    get_order(db, organization_id=organization_id, order_id=order_id)
    return OrderItemRepository(db).list_for_order(order_id)
