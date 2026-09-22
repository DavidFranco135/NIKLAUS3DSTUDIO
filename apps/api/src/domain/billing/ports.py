from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.domain.ai.ports import ProviderHealth


@dataclass(frozen=True)
class PlanRef:
    code: str
    external_price_id: str | None = None


@dataclass(frozen=True)
class SubscriptionRef:
    external_subscription_id: str | None
    external_customer_id: str | None
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_end: datetime | None = None


@dataclass(frozen=True)
class BillingEventRef:
    external_event_id: str
    event_type: str
    organization_id: UUID | None
    raw_payload: dict[str, Any]


class BillingProvider(Protocol):
    """Not an AI model — a subscription/payment backend (mock today, Stripe

    later) wrapped behind the same provider convention (`name` +
    `health_check`) as every other pluggable engine in this codebase.
    """

    name: str

    def health_check(self) -> ProviderHealth: ...

    def create_subscription(
        self, *, organization_id: UUID, plan: PlanRef, trial_period_days: int | None
    ) -> SubscriptionRef: ...

    def cancel_subscription(
        self, *, subscription_ref: SubscriptionRef, at_period_end: bool
    ) -> SubscriptionRef: ...

    def change_plan(
        self, *, subscription_ref: SubscriptionRef, new_plan: PlanRef
    ) -> SubscriptionRef: ...

    def get_subscription(self, *, subscription_ref: SubscriptionRef) -> SubscriptionRef: ...

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str) -> bool: ...

    def parse_webhook_event(self, *, payload: bytes) -> BillingEventRef: ...
