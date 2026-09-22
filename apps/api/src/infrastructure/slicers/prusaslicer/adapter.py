from src.domain.ai.ports import MeshRef, ProviderHealth, SlicerProvider
from src.domain.slicing.profiles import MaterialProfile, PrinterProfile
from src.domain.slicing.report import SliceResult
from src.infrastructure.slicers._not_configured import not_configured_health, raise_not_configured

_ENGINE_NAME = "PrusaSlicer CLI"


class PrusaSlicerCLIProvider(SlicerProvider):
    """Placeholder adapter for the PrusaSlicer CLI (AGPL-3.0). Primeiro

    candidato do roadmap (ARCHITECTURE.md §13) — implementa a interface real
    de `SlicerProvider`, mas nunca baixa/executa o binário: falta confirmar
    com jurídico a cláusula de uso via rede da AGPL para uma plataforma SaaS
    (ver docs/AI-LICENSES.md) antes de instalar e invocar o CLI de verdade.
    """

    name = "prusaslicer_cli"

    def health_check(self) -> ProviderHealth:
        return not_configured_health(_ENGINE_NAME)

    def slice(
        self, mesh: MeshRef, printer: PrinterProfile, material: MaterialProfile
    ) -> SliceResult:
        raise_not_configured(_ENGINE_NAME)
