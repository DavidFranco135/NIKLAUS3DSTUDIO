from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from src.application.billing import use_cases as billing_use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.interfaces.http.dependencies import get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    CancelSubscriptionRequest,
    ChangePlanRequest,
    PlanResponse,
    SubscriptionResponse,
    UsageItemResponse,
)

router = APIRouter(prefix="/organizations/{organization_id}/billing", tags=["billing"])
global_router = APIRouter(prefix="/billing", tags=["billing"])


@global_router.get("/plans", response_model=list[PlanResponse])
def list_plans(db: Session = Depends(get_db)) -> list[PlanResponse]:
    plans = billing_use_cases.list_plans(db)
    return [PlanResponse.model_validate(p) for p in plans]


@global_router.post("/webhooks/{provider_name}")
async def receive_webhook(
    provider_name: str,
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    signature: str | None = Header(default=None, alias="X-Billing-Signature"),
) -> dict:
    payload = await request.body()
    signature_header = stripe_signature or signature or ""
    try:
        event = billing_use_cases.process_webhook_event(
            db, provider_name=provider_name, payload=payload, signature_header=signature_header
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return {"id": str(event.id), "status": event.status}


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_subscription(
    organization_id: UUID, db: Session = Depends(get_db)
) -> SubscriptionResponse:
    try:
        subscription = billing_use_cases.get_subscription(db, organization_id=organization_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return SubscriptionResponse.model_validate(subscription)


@router.get(
    "/usage",
    response_model=list[UsageItemResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_usage(organization_id: UUID, db: Session = Depends(get_db)) -> list[UsageItemResponse]:
    try:
        items = billing_use_cases.get_usage_summary(db, organization_id=organization_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return [UsageItemResponse(**asdict(item)) for item in items]


@router.post(
    "/subscription/cancel",
    response_model=SubscriptionResponse,
    dependencies=[Depends(require_org_role(Role.OWNER))],
)
def cancel_subscription(
    organization_id: UUID, payload: CancelSubscriptionRequest, db: Session = Depends(get_db)
) -> SubscriptionResponse:
    try:
        subscription = billing_use_cases.cancel_subscription(
            db, organization_id=organization_id, at_period_end=payload.at_period_end
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return SubscriptionResponse.model_validate(subscription)


@router.post(
    "/subscription/change-plan",
    response_model=SubscriptionResponse,
    dependencies=[Depends(require_org_role(Role.OWNER))],
)
def change_plan(
    organization_id: UUID, payload: ChangePlanRequest, db: Session = Depends(get_db)
) -> SubscriptionResponse:
    try:
        subscription = billing_use_cases.change_plan(
            db, organization_id=organization_id, new_plan_code=payload.plan_code
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return SubscriptionResponse.model_validate(subscription)
