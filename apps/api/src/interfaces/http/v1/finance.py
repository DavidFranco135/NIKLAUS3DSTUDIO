from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.application.financial import use_cases as financial_use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.infrastructure.db.models import User
from src.interfaces.http.dependencies import get_current_user, get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    CreateFinancialTransactionRequest,
    FinancialSummaryResponse,
    FinancialTransactionResponse,
)

router = APIRouter(prefix="/organizations/{organization_id}/finance", tags=["finance"])


@router.post(
    "/transactions",
    response_model=FinancialTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def create_transaction(
    organization_id: UUID,
    payload: CreateFinancialTransactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialTransactionResponse:
    try:
        transaction = financial_use_cases.create_transaction(
            db,
            organization_id=organization_id,
            type=payload.type,
            category=payload.category,
            cost_center=payload.cost_center,
            amount=payload.amount,
            reference_order_id=payload.reference_order_id,
            due_date=payload.due_date,
            mark_as_paid=payload.mark_as_paid,
            created_by=current_user.id,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return FinancialTransactionResponse.model_validate(transaction)


@router.get(
    "/transactions",
    response_model=list[FinancialTransactionResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_transactions(
    organization_id: UUID,
    db: Session = Depends(get_db),
    type: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> list[FinancialTransactionResponse]:
    transactions = financial_use_cases.list_transactions(
        db, organization_id=organization_id, type=type, start_date=start_date, end_date=end_date
    )
    return [FinancialTransactionResponse.model_validate(t) for t in transactions]


@router.get(
    "/transactions/{transaction_id}",
    response_model=FinancialTransactionResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_transaction(
    organization_id: UUID, transaction_id: UUID, db: Session = Depends(get_db)
) -> FinancialTransactionResponse:
    try:
        transaction = financial_use_cases.get_transaction(
            db, organization_id=organization_id, transaction_id=transaction_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return FinancialTransactionResponse.model_validate(transaction)


@router.post(
    "/transactions/{transaction_id}/mark-paid",
    response_model=FinancialTransactionResponse,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def mark_transaction_paid(
    organization_id: UUID, transaction_id: UUID, db: Session = Depends(get_db)
) -> FinancialTransactionResponse:
    try:
        transaction = financial_use_cases.mark_transaction_paid(
            db, organization_id=organization_id, transaction_id=transaction_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return FinancialTransactionResponse.model_validate(transaction)


@router.get(
    "/summary",
    response_model=FinancialSummaryResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_financial_summary(
    organization_id: UUID,
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> FinancialSummaryResponse:
    summary = financial_use_cases.get_financial_summary(
        db, organization_id=organization_id, start_date=start_date, end_date=end_date
    )
    return FinancialSummaryResponse(
        total_revenue=summary.total_revenue,
        total_cost=summary.total_cost,
        total_expense=summary.total_expense,
        profit=summary.profit,
        pending_receivables=summary.pending_receivables,
        pending_payables=summary.pending_payables,
    )
