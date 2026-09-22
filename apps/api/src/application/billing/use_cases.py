from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from src.domain.billing.enforcement import check_numeric_limit
from src.domain.billing.entitlements import Entitlement, get_numeric_limit, is_feature_enabled
from src.domain.billing.ports import PlanRef, SubscriptionRef
from src.domain.billing.subscription_status import validate_transition
from src.domain.shared.exceptions import (
    InvalidWebhookSignatureError,
    LimitExceededError,
    PlanNotFoundError,
    SubscriptionNotFoundError,
)
from src.infrastructure.billing_providers.registry import get_billing_provider
from src.infrastructure.db.models import BillingEvent, Plan, PlanEntitlement, Subscription
from src.infrastructure.db.repositories import (
    AIJobRepository,
    BillingEventRepository,
    FileAssetRepository,
    PlanEntitlementRepository,
    PlanRepository,
    ProjectRepository,
    SubscriptionRepository,
)

# Plano semente de desenvolvimento — NÃO é um plano comercial. Preços e
# planos reais são uma decisão de produto à parte, tomada só depois que esta
# infraestrutura existir (ver ARCHITECTURE.md, nota "Status na Fase 18A").
# Os limites cadastrados nele existem só para o ambiente ter algo para
# testar contra.
DEFAULT_PLAN_CODE = "dev_unlimited"

# Chaves de entitlement conhecidas nesta fase — usadas pelos módulos que já
# têm enforcement ligado (Projetos, AI Jobs, Storage). Novas chaves não
# exigem migration: só uma nova linha em `plan_entitlements`.
KEY_MAX_PROJECTS = "max_projects"
KEY_MAX_AI_JOBS_PER_PERIOD = "max_ai_jobs_per_period"
KEY_MAX_STORAGE_MB = "max_storage_mb"


def _to_domain_entitlement(row: PlanEntitlement) -> Entitlement:
    return Entitlement(
        key=row.key,
        limit_type=row.limit_type,
        bool_value=row.bool_value,
        numeric_value=row.numeric_value,
    )


def _to_ref(subscription: Subscription) -> SubscriptionRef:
    return SubscriptionRef(
        external_subscription_id=subscription.external_subscription_id,
        external_customer_id=subscription.external_customer_id,
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        trial_end=subscription.trial_end,
    )


# Espelha exatamente os valores semeados pela migration
# `a64f7589aaf0_billing_plans_subscriptions_and_events.py` — existe aqui
# também porque ambientes que criam o schema via `Base.metadata.create_all`
# (testes automatizados, notavelmente) nunca rodam migrations, então nunca
# veriam o INSERT da migration. Mudar os valores aqui sem espelhar na
# migration (ou vice-versa) é uma inconsistência a evitar.
_DEV_PLAN_ENTITLEMENTS: list[dict] = [
    {"key": KEY_MAX_PROJECTS, "limit_type": "numeric", "numeric_value": 20},
    {"key": KEY_MAX_AI_JOBS_PER_PERIOD, "limit_type": "numeric", "numeric_value": 50},
    {"key": KEY_MAX_STORAGE_MB, "limit_type": "numeric", "numeric_value": 500},
    {"key": "feature.ai_text_to_3d", "limit_type": "boolean", "bool_value": True},
    {"key": "feature.ai_image_to_3d", "limit_type": "boolean", "bool_value": True},
]


def get_default_plan(db: Session) -> Plan:
    """Cria o plano semente de desenvolvimento na primeira vez que for

    pedido, se ainda não existir — necessário porque nem todo ambiente
    (testes, notavelmente) roda a migration que o semeia; ver o comentário
    de `_DEV_PLAN_ENTITLEMENTS`. Idempotente: chamadas seguintes só leem.
    """
    plan_repo = PlanRepository(db)
    plan = plan_repo.get_by_code(DEFAULT_PLAN_CODE)
    if plan is not None:
        return plan

    plan = Plan(code=DEFAULT_PLAN_CODE, name="Desenvolvimento (interno, sem custo real)")
    db.add(plan)
    db.flush()
    for entitlement in _DEV_PLAN_ENTITLEMENTS:
        db.add(PlanEntitlement(plan_id=plan.id, **entitlement))
    db.commit()
    return plan


def list_plans(db: Session) -> list[Plan]:
    return PlanRepository(db).list_active()


def create_default_subscription(db: Session, *, organization_id: UUID) -> Subscription:
    """Chamado a partir de `register()`/`create_organization()` — toda

    organização nasce com uma assinatura, nunca fica "sem plano" (o que
    deixaria o enforcement indefinido: bloquear tudo, ou liberar tudo?).
    Idempotente: se a organização já tem uma assinatura, devolve a
    existente em vez de duplicar (mesmo espírito de `AIJob.idempotency_key`).
    """
    existing = SubscriptionRepository(db).get_by_organization(organization_id)
    if existing is not None:
        return existing

    plan = get_default_plan(db)
    provider = get_billing_provider()
    ref = provider.create_subscription(
        organization_id=organization_id,
        plan=PlanRef(code=plan.code),
        trial_period_days=plan.trial_period_days,
    )
    subscription = SubscriptionRepository(db).create(
        organization_id=organization_id,
        plan_id=plan.id,
        status=ref.status,
        current_period_start=ref.current_period_start,
        current_period_end=ref.current_period_end,
        trial_start=ref.current_period_start if ref.trial_end else None,
        trial_end=ref.trial_end,
        external_provider=provider.name,
        external_subscription_id=ref.external_subscription_id,
        external_customer_id=ref.external_customer_id,
    )
    db.commit()
    return subscription


def get_subscription(db: Session, *, organization_id: UUID) -> Subscription:
    subscription = SubscriptionRepository(db).get_by_organization(organization_id)
    if subscription is None:
        raise SubscriptionNotFoundError(str(organization_id))
    return subscription


def get_entitlement(db: Session, *, organization_id: UUID, key: str) -> Entitlement:
    subscription = get_subscription(db, organization_id=organization_id)
    row = PlanEntitlementRepository(db).get_for_plan(subscription.plan_id, key)
    if row is None:
        # Chave sem entitlement cadastrado no plano: tratado como "sem
        # acesso" para features booleanas e "zero" para limites numéricos —
        # o lado seguro é nunca liberar por omissão de cadastro.
        return Entitlement(key=key, limit_type="numeric", numeric_value=0)
    return _to_domain_entitlement(row)


def enforce_numeric_limit(
    db: Session, *, organization_id: UUID, key: str, current_usage: float
) -> None:
    entitlement = get_entitlement(db, organization_id=organization_id, key=key)
    result = check_numeric_limit(current_usage=current_usage, entitlement=entitlement)
    if not result.allowed:
        raise LimitExceededError(
            key=key,
            current_usage=current_usage,
            limit=result.limit if result.limit is not None else current_usage,
            message=result.reason or f"Limite de '{key}' atingido.",
        )


def cancel_subscription(
    db: Session, *, organization_id: UUID, at_period_end: bool
) -> Subscription:
    subscription = get_subscription(db, organization_id=organization_id)
    repo = SubscriptionRepository(db)

    if at_period_end:
        # Só marca a intenção — o status muda de verdade quando o período
        # atual terminar (job futuro, fora do escopo desta fase) ou quando
        # um evento de webhook confirmar o cancelamento.
        provider = get_billing_provider()
        provider.cancel_subscription(subscription_ref=_to_ref(subscription), at_period_end=True)
        repo.mark_cancel_at_period_end(subscription, value=True)
    else:
        validate_transition(subscription.status, "canceled")
        provider = get_billing_provider()
        provider.cancel_subscription(subscription_ref=_to_ref(subscription), at_period_end=False)
        repo.mark_canceled_now(subscription)

    db.commit()
    return subscription


def change_plan(db: Session, *, organization_id: UUID, new_plan_code: str) -> Subscription:
    subscription = get_subscription(db, organization_id=organization_id)
    new_plan = PlanRepository(db).get_by_code(new_plan_code)
    if new_plan is None:
        raise PlanNotFoundError(new_plan_code)

    provider = get_billing_provider()
    provider.change_plan(
        subscription_ref=_to_ref(subscription), new_plan=PlanRef(code=new_plan.code)
    )

    SubscriptionRepository(db).update_plan(subscription, plan_id=new_plan.id)
    db.commit()
    return subscription


@dataclass(frozen=True)
class UsageItem:
    key: str
    limit_type: str
    current_usage: float | None
    limit: float | None
    enabled: bool | None


def _current_usage_for_key(
    db: Session, *, organization_id: UUID, key: str, subscription: Subscription
) -> float:
    if key == KEY_MAX_PROJECTS:
        return float(len(ProjectRepository(db).list_for_org(organization_id)))
    if key == KEY_MAX_AI_JOBS_PER_PERIOD:
        return float(
            AIJobRepository(db).count_since(organization_id, subscription.current_period_start)
        )
    if key == KEY_MAX_STORAGE_MB:
        return FileAssetRepository(db).sum_size_bytes_for_org(organization_id) / (1024 * 1024)
    return 0.0


def get_usage_summary(db: Session, *, organization_id: UUID) -> list[UsageItem]:
    subscription = get_subscription(db, organization_id=organization_id)
    rows = PlanEntitlementRepository(db).list_for_plan(subscription.plan_id)

    items = []
    for row in rows:
        entitlement = _to_domain_entitlement(row)
        if entitlement.limit_type == "boolean":
            items.append(
                UsageItem(
                    key=row.key,
                    limit_type="boolean",
                    current_usage=None,
                    limit=None,
                    enabled=is_feature_enabled(entitlement),
                )
            )
        else:
            usage = _current_usage_for_key(
                db, organization_id=organization_id, key=row.key, subscription=subscription
            )
            items.append(
                UsageItem(
                    key=row.key,
                    limit_type=entitlement.limit_type,
                    current_usage=usage,
                    limit=get_numeric_limit(entitlement),
                    enabled=None,
                )
            )
    return items


def process_webhook_event(
    db: Session, *, provider_name: str, payload: bytes, signature_header: str
) -> BillingEvent:
    provider = get_billing_provider()
    if not provider.verify_webhook_signature(payload=payload, signature_header=signature_header):
        raise InvalidWebhookSignatureError("Assinatura do webhook inválida.")

    parsed = provider.parse_webhook_event(payload=payload)

    event_repo = BillingEventRepository(db)
    existing = event_repo.get_by_provider_and_external_id(provider_name, parsed.external_event_id)
    if existing is not None and existing.status == "processed":
        return existing

    event = existing or event_repo.create(
        provider=provider_name,
        external_event_id=parsed.external_event_id,
        event_type=parsed.event_type,
        organization_id=parsed.organization_id,
        payload=parsed.raw_payload,
    )
    db.commit()

    try:
        _apply_billing_event(
            db,
            organization_id=parsed.organization_id,
            event_type=parsed.event_type,
            payload=parsed.raw_payload,
        )
    except Exception as exc:  # noqa: BLE001 — o evento fica registrado como failed, nunca perdido
        event_repo.mark_failed(event, error_message=str(exc))
        db.commit()
        raise

    event_repo.mark_processed(event)
    db.commit()
    return event


def _apply_billing_event(
    db: Session, *, organization_id: UUID | None, event_type: str, payload: dict
) -> None:
    """Só cobre os tipos de evento que o `MockBillingProvider` realmente

    consegue emitir hoje — sincronizar um evento cujo tipo não reconhecemos
    não é um erro (webhooks reais mandam muito mais tipos do que qualquer
    consumidor processa; ignorar o que não interessa é o comportamento
    correto, não uma falha).
    """
    if organization_id is None:
        return
    subscription = SubscriptionRepository(db).get_by_organization(organization_id)
    if subscription is None:
        return

    if event_type == "subscription.updated" and "status" in payload:
        new_status = payload["status"]
        validate_transition(subscription.status, new_status)
        SubscriptionRepository(db).update_status(subscription, status=new_status)
    elif event_type == "subscription.canceled":
        SubscriptionRepository(db).mark_canceled_now(subscription)
