from dataclasses import dataclass

from src.domain.shared.exceptions import InvalidEntitlementError

_LIMIT_TYPES = {"boolean", "numeric", "unlimited"}


@dataclass(frozen=True)
class Entitlement:
    key: str
    limit_type: str
    bool_value: bool | None = None
    numeric_value: float | None = None

    def __post_init__(self) -> None:
        if self.limit_type not in _LIMIT_TYPES:
            raise InvalidEntitlementError(
                f"limit_type inválido: {self.limit_type!r}. Esperado um de {sorted(_LIMIT_TYPES)}."
            )


def is_feature_enabled(entitlement: Entitlement) -> bool:
    """Só faz sentido para `limit_type="boolean"` — qualquer outro tipo é

    tratado como "não é uma feature flag" (False), nunca como erro: um
    caller que confundir tipos deve receber uma resposta segura (acesso
    negado), não uma exceção.
    """
    return entitlement.limit_type == "boolean" and bool(entitlement.bool_value)


def get_numeric_limit(entitlement: Entitlement) -> float | None:
    """None significa "sem limite" — tanto para `limit_type="unlimited"`

    quanto para um `numeric_value` nulo por acidente (mesma semântica seria
    esconder um bug, mas o lado seguro para o usuário é não bloquear por um
    dado ausente; quem cadastra o plano é responsável por preencher o valor).
    """
    if entitlement.limit_type == "unlimited":
        return None
    if entitlement.limit_type == "numeric":
        return entitlement.numeric_value
    return None
