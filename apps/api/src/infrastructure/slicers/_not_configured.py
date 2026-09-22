from typing import NoReturn

from src.domain.ai.ports import ProviderHealth
from src.domain.shared.exceptions import ProviderNotConfiguredError

_MESSAGE = (
    "{engine} não está configurado: nenhum binário CLI está instalado nesta "
    "infraestrutura e a licença AGPL-3.0 do projeto não foi confirmada com "
    "jurídico para uso em SaaS antes de ser habilitado (ver docs/AI-LICENSES.md)."
)


def not_configured_health(engine_name: str) -> ProviderHealth:
    return ProviderHealth(healthy=False, detail=_MESSAGE.format(engine=engine_name))


def raise_not_configured(engine_name: str) -> NoReturn:
    raise ProviderNotConfiguredError(_MESSAGE.format(engine=engine_name))
