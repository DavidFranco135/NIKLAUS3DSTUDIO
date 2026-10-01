from typing import NoReturn

from src.domain.shared.exceptions import ProviderNotConfiguredError
from src.domain.shared.provider_ports import ProviderHealth

_MESSAGE = (
    "{engine} não está configurado: nenhum binário CLI está instalado nesta "
    "infraestrutura e a licença AGPL-3.0 do projeto não foi confirmada com "
    "jurídico para uso em SaaS antes de ser habilitado."
)


def not_configured_health(engine_name: str) -> ProviderHealth:
    return ProviderHealth(healthy=False, detail=_MESSAGE.format(engine=engine_name))


def raise_not_configured(engine_name: str) -> NoReturn:
    raise ProviderNotConfiguredError(_MESSAGE.format(engine=engine_name))
