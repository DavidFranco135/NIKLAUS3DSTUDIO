from uuid import UUID

from sqlalchemy.orm import Session

from src.domain.shared.exceptions import CustomerNotFoundError
from src.infrastructure.db.models import Customer
from src.infrastructure.db.repositories import (
    CustomerRepository,
    OrderRepository,
    ProjectRepository,
    QuoteRepository,
)


def create_customer(
    db: Session,
    *,
    organization_id: UUID,
    name: str,
    email: str | None,
    phone: str | None,
    document: str | None,
    address: dict | None,
    notes: str | None,
) -> Customer:
    customer = CustomerRepository(db).create(
        organization_id=organization_id,
        name=name,
        email=email,
        phone=phone,
        document=document,
        address=address,
        notes=notes,
    )
    db.commit()
    return customer


def list_customers(db: Session, *, organization_id: UUID) -> list[Customer]:
    return CustomerRepository(db).list_for_org(organization_id)


def get_customer(db: Session, *, organization_id: UUID, customer_id: UUID) -> Customer:
    customer = CustomerRepository(db).get(organization_id, customer_id)
    if customer is None:
        raise CustomerNotFoundError(str(customer_id))
    return customer


def update_customer(
    db: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
    name: str | None,
    email: str | None,
    phone: str | None,
    document: str | None,
    address: dict | None,
    notes: str | None,
) -> Customer:
    customer = get_customer(db, organization_id=organization_id, customer_id=customer_id)
    if name is not None:
        customer.name = name
    if email is not None:
        customer.email = email
    if phone is not None:
        customer.phone = phone
    if document is not None:
        customer.document = document
    if address is not None:
        customer.address = address
    if notes is not None:
        customer.notes = notes
    db.commit()
    return customer


def delete_customer(db: Session, *, organization_id: UUID, customer_id: UUID) -> None:
    customer = get_customer(db, organization_id=organization_id, customer_id=customer_id)
    CustomerRepository(db).soft_delete(customer)
    db.commit()


def get_customer_history(db: Session, *, organization_id: UUID, customer_id: UUID) -> dict:
    """Passou a incluir `orders` na Fase 14 — antes disso (Fase 13) só havia

    orçamentos e projetos vinculados.
    """
    get_customer(db, organization_id=organization_id, customer_id=customer_id)
    return {
        "quotes": QuoteRepository(db).list_for_customer(organization_id, customer_id),
        "projects": ProjectRepository(db).list_for_customer(organization_id, customer_id),
        "orders": OrderRepository(db).list_for_customer(organization_id, customer_id),
    }
