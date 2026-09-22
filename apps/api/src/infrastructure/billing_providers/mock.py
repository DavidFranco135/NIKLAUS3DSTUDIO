import json
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.domain.ai.ports import ProviderHealth
from src.domain.billing.ports import BillingEventRef, PlanRef, SubscriptionRef
from src.domain.shared.exceptions import InvalidWebhookPayloadError

_PERIOD_LENGTH_DAYS = 30

# Só existe porque o fluxo de webhook precisa de *alguma* verificação de
# assinatura para exercitar o caminho de código real — nunca é um segredo
# de produção, e o MockBillingProvider nunca fala com uma rede de verdade.
_MOCK_WEBHOOK_SECRET = "mock-dev-secret"  # noqa: S105


class MockBillingProvider:
    """Implementação em processo, sem rede, sem cobrança real — mesmo

    padrão de MockImageTo3DProvider (Fase 4): existe para provar que o
    pipeline de billing funciona de ponta a ponta antes de qualquer conta
    Stripe existir. Datas e ids são gerados aqui exatamente como o Stripe
    faria (para que trocar de provider depois não exija remapeamento).
    """

    name = "mock_billing"

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            healthy=True, detail="Mock billing provider — sem rede, sem cobrança real."
        )

    def create_subscription(
        self, *, organization_id: UUID, plan: PlanRef, trial_period_days: int | None
    ) -> SubscriptionRef:
        now = datetime.now(UTC)
        trial_end = now + timedelta(days=trial_period_days) if trial_period_days else None
        return SubscriptionRef(
            external_subscription_id=f"mock_sub_{uuid.uuid4().hex[:16]}",
            external_customer_id=f"mock_cus_{uuid.uuid4().hex[:16]}",
            status="trialing" if trial_end else "active",
            current_period_start=now,
            current_period_end=now + timedelta(days=_PERIOD_LENGTH_DAYS),
            trial_end=trial_end,
        )

    def cancel_subscription(
        self, *, subscription_ref: SubscriptionRef, at_period_end: bool
    ) -> SubscriptionRef:
        new_status = subscription_ref.status if at_period_end else "canceled"
        return SubscriptionRef(
            external_subscription_id=subscription_ref.external_subscription_id,
            external_customer_id=subscription_ref.external_customer_id,
            status=new_status,
            current_period_start=subscription_ref.current_period_start,
            current_period_end=subscription_ref.current_period_end,
            trial_end=subscription_ref.trial_end,
        )

    def change_plan(
        self, *, subscription_ref: SubscriptionRef, new_plan: PlanRef
    ) -> SubscriptionRef:
        return subscription_ref

    def get_subscription(self, *, subscription_ref: SubscriptionRef) -> SubscriptionRef:
        return subscription_ref

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str) -> bool:
        return signature_header == _MOCK_WEBHOOK_SECRET

    def parse_webhook_event(self, *, payload: bytes) -> BillingEventRef:
        try:
            data = json.loads(payload)
            event_type = data["type"]
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError) as exc:
            raise InvalidWebhookPayloadError(f"Payload de webhook inválido: {exc}") from exc

        organization_id = data.get("organization_id")
        return BillingEventRef(
            external_event_id=data.get("id") or f"mock_evt_{uuid.uuid4().hex[:16]}",
            event_type=event_type,
            organization_id=uuid.UUID(organization_id) if organization_id else None,
            raw_payload=data,
        )
