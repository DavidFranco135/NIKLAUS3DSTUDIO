from src.domain.shared.exceptions import InvalidSubscriptionTransitionError

# Vocabulário emprestado do Stripe de propósito (ARCHITECTURE.md, nota
# "Status na Fase 18A") — para quando um StripeBillingProvider existir, não
# precisar remapear nenhum valor. `canceled` é terminal, sem transição de
# volta — mesmo espírito de `domain/orders/status.py`.
_TRANSITIONS: dict[str, set[str]] = {
    "trialing": {"active", "canceled"},
    "active": {"past_due", "canceled"},
    "past_due": {"active", "canceled"},
    "canceled": set(),
}


def validate_transition(current: str, new: str) -> None:
    if current not in _TRANSITIONS:
        raise InvalidSubscriptionTransitionError(f"Status atual desconhecido: {current!r}.")
    if new not in _TRANSITIONS:
        raise InvalidSubscriptionTransitionError(f"Status inválido: {new!r}.")
    if new not in _TRANSITIONS[current]:
        raise InvalidSubscriptionTransitionError(
            f"Não é possível ir de '{current}' para '{new}'."
        )
