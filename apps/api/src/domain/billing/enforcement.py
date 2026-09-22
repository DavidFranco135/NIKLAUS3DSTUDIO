from dataclasses import dataclass

from src.domain.billing.entitlements import Entitlement, get_numeric_limit, is_feature_enabled


@dataclass(frozen=True)
class LimitCheckResult:
    allowed: bool
    key: str
    current_usage: float | None
    limit: float | None
    reason: str | None = None


def check_numeric_limit(*, current_usage: float, entitlement: Entitlement) -> LimitCheckResult:
    """Nunca chamado pelo módulo de billing sozinho — quem sabe contar seu

    próprio recurso (projetos, jobs de IA, armazenamento) é o módulo dono
    dele; billing só recebe o número já contado e compara contra o
    entitlement do plano atual. Isso evita billing precisar importar
    `ProjectRepository`/`AIJobRepository`/etc. — nenhuma dependência
    circular entre módulos de negócio e o módulo de billing.
    """
    limit = get_numeric_limit(entitlement)
    if limit is None:
        return LimitCheckResult(
            allowed=True, key=entitlement.key, current_usage=current_usage, limit=None
        )
    allowed = current_usage < limit
    return LimitCheckResult(
        allowed=allowed,
        key=entitlement.key,
        current_usage=current_usage,
        limit=limit,
        reason=None
        if allowed
        else f"Limite de '{entitlement.key}' atingido: {current_usage}/{limit}.",
    )


def check_feature_flag(entitlement: Entitlement) -> LimitCheckResult:
    allowed = is_feature_enabled(entitlement)
    return LimitCheckResult(
        allowed=allowed,
        key=entitlement.key,
        current_usage=None,
        limit=None,
        reason=None if allowed else f"Recurso '{entitlement.key}' não disponível no plano atual.",
    )
