from typing import NoReturn

from src.domain.ai.ports import ProviderHealth
from src.domain.shared.exceptions import ProviderNotConfiguredError

_MESSAGE = (
    "{model} não está configurado: requer infraestrutura de GPU e confirmação de licença "
    "de uso comercial antes de ser habilitado (ver docs/AI-LICENSES.md)."
)


def not_configured_health(model_name: str) -> ProviderHealth:
    return ProviderHealth(healthy=False, detail=_MESSAGE.format(model=model_name))


def raise_not_configured(model_name: str) -> NoReturn:
    raise ProviderNotConfiguredError(_MESSAGE.format(model=model_name))
