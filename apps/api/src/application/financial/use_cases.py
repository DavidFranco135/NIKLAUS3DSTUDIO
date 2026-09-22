from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from src.domain.financial.summary import (
    TransactionAmount,
    compute_summary,
    validate_transaction_type,
)
from src.domain.shared.exceptions import FinancialTransactionNotFoundError, OrderNotFoundError
from src.infrastructure.db.models import FinancialTransaction
from src.infrastructure.db.repositories import FinancialTransactionRepository, OrderRepository


def create_transaction(
    db: Session,
    *,
    organization_id: UUID,
    type: str,
    category: str,
    cost_center: str | None,
    amount: float,
    reference_order_id: UUID | None,
    due_date: date | None,
    mark_as_paid: bool,
    created_by: UUID | None,
) -> FinancialTransaction:
    validate_transaction_type(type)

    if reference_order_id is not None and OrderRepository(db).get(
        organization_id, reference_order_id
    ) is None:
        raise OrderNotFoundError(str(reference_order_id))

    transaction = FinancialTransactionRepository(db).create(
        organization_id=organization_id,
        type=type,
        category=category,
        cost_center=cost_center,
        amount=amount,
        reference_order_id=reference_order_id,
        due_date=due_date,
        paid_at=datetime.now(UTC) if mark_as_paid else None,
        created_by=created_by,
    )
    db.commit()
    return transaction


def list_transactions(
    db: Session,
    *,
    organization_id: UUID,
    type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[FinancialTransaction]:
    return FinancialTransactionRepository(db).list_for_org(
        organization_id, type=type, start_date=start_date, end_date=end_date
    )


def get_transaction(
    db: Session, *, organization_id: UUID, transaction_id: UUID
) -> FinancialTransaction:
    transaction = FinancialTransactionRepository(db).get(organization_id, transaction_id)
    if transaction is None:
        raise FinancialTransactionNotFoundError(str(transaction_id))
    return transaction


def mark_transaction_paid(
    db: Session, *, organization_id: UUID, transaction_id: UUID
) -> FinancialTransaction:
    transaction = get_transaction(
        db, organization_id=organization_id, transaction_id=transaction_id
    )
    FinancialTransactionRepository(db).mark_paid(transaction)
    db.commit()
    return transaction


def get_financial_summary(
    db: Session,
    *,
    organization_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
):
    transactions = list_transactions(
        db, organization_id=organization_id, start_date=start_date, end_date=end_date
    )
    return compute_summary(
        [
            TransactionAmount(type=t.type, amount=t.amount, is_paid=t.paid_at is not None)
            for t in transactions
        ]
    )


def record_order_paid(
    db: Session, *, organization_id: UUID, order_id: UUID, amount: float, created_by: UUID | None
) -> FinancialTransaction:
    """Chamado a partir de `application/orders/use_cases.py::transition_order_status`

    quando um pedido é marcado `paid` — nunca chamado a partir de uma
    requisição direta a este módulo. Cria a `financial_transaction` já como
    paga (o dinheiro entrou no exato momento em que o pedido foi marcado
    como pago), sem passar por `due_date`/estado pendente.
    """
    return create_transaction(
        db,
        organization_id=organization_id,
        type="receita",
        category="pedido",
        cost_center=None,
        amount=amount,
        reference_order_id=order_id,
        due_date=None,
        mark_as_paid=True,
        created_by=created_by,
    )
