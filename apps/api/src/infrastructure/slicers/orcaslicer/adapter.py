from src.domain.ai.ports import MeshRef, ProviderHealth, SlicerProvider
from src.domain.slicing.profiles import MaterialProfile, PrinterProfile
from src.domain.slicing.report import SliceResult
from src.infrastructure.slicers._not_configured import not_configured_health, raise_not_configured

_ENGINE_NAME = "OrcaSlicer CLI"


class OrcaSlicerCLIProvider(SlicerProvider):
    """Placeholder adapter for the OrcaSlicer CLI (AGPL-3.0). Segundo

    candidato do roadmap (ARCHITECTURE.md §13) — mesma situação do
    `PrusaSlicerCLIProvider`: interface real implementada, binário nunca
    baixado/executado, pendente confirmação jurídica da AGPL para SaaS.
    """

    name = "orcaslicer_cli"

    def health_check(self) -> ProviderHealth:
        return not_configured_health(_ENGINE_NAME)

    def slice(
        self, mesh: MeshRef, printer: PrinterProfile, material: MaterialProfile
    ) -> SliceResult:
        raise_not_configured(_ENGINE_NAME)
