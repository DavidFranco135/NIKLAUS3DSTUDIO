from src.domain.billing.ports import BillingProvider
from src.infrastructure.billing_providers.mock import MockBillingProvider

# Um único provider, sem lista de fallback — igual ao CAD paramétrico
# (Fase 7): não existe "provider secundário" que faça sentido aqui. Trocar
# por um StripeBillingProvider real é mudar esta linha, nada mais —
# domain/application/HTTP não sabem que o provider mudou.
_BILLING_PROVIDER: BillingProvider = MockBillingProvider()


def get_billing_provider() -> BillingProvider:
    return _BILLING_PROVIDER
