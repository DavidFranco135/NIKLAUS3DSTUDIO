from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.application.customers import use_cases as customer_use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.interfaces.http.dependencies import get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    CreateCustomerRequest,
    CustomerHistoryResponse,
    CustomerResponse,
    ProjectResponse,
    QuoteResponse,
    UpdateCustomerRequest,
)

router = APIRouter(prefix="/organizations/{organization_id}/customers", tags=["customers"])


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def create_customer(
    organization_id: UUID, payload: CreateCustomerRequest, db: Session = Depends(get_db)
) -> CustomerResponse:
    customer = customer_use_cases.create_customer(
        db,
        organization_id=organization_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        document=payload.document,
        address=payload.address,
        notes=payload.notes,
    )
    return CustomerResponse.model_validate(customer)


@router.get(
    "",
    response_model=list[CustomerResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_customers(organization_id: UUID, db: Session = Depends(get_db)) -> list[CustomerResponse]:
    customers = customer_use_cases.list_customers(db, organization_id=organization_id)
    return [CustomerResponse.model_validate(c) for c in customers]


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_customer(
    organization_id: UUID, customer_id: UUID, db: Session = Depends(get_db)
) -> CustomerResponse:
    try:
        customer = customer_use_cases.get_customer(
            db, organization_id=organization_id, customer_id=customer_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return CustomerResponse.model_validate(customer)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def update_customer(
    organization_id: UUID,
    customer_id: UUID,
    payload: UpdateCustomerRequest,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    try:
        customer = customer_use_cases.update_customer(
            db,
            organization_id=organization_id,
            customer_id=customer_id,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            document=payload.document,
            address=payload.address,
            notes=payload.notes,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return CustomerResponse.model_validate(customer)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def delete_customer(
    organization_id: UUID, customer_id: UUID, db: Session = Depends(get_db)
) -> None:
    try:
        customer_use_cases.delete_customer(
            db, organization_id=organization_id, customer_id=customer_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc


@router.get(
    "/{customer_id}/history",
    response_model=CustomerHistoryResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_customer_history(
    organization_id: UUID, customer_id: UUID, db: Session = Depends(get_db)
) -> CustomerHistoryResponse:
    try:
        history = customer_use_cases.get_customer_history(
            db, organization_id=organization_id, customer_id=customer_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return CustomerHistoryResponse(
        quotes=[QuoteResponse.model_validate(q) for q in history["quotes"]],
        projects=[ProjectResponse.model_validate(p) for p in history["projects"]],
    )
