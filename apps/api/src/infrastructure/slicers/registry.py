from src.domain.ai.ports import SlicerProvider
from src.infrastructure.slicers.orcaslicer.adapter import OrcaSlicerCLIProvider
from src.infrastructure.slicers.prusaslicer.adapter import PrusaSlicerCLIProvider

# Nenhum binário de slicer está instalado nesta máquina, e a licença AGPL-3.0
# de ambos os candidatos não foi confirmada com jurídico para uso em SaaS
# (ver docs/AI-LICENSES.md) — diferente do registry de ai_providers, não há
# nenhum provider funcional nesta lista ainda (nem um "mock" faz sentido
# aqui: fatiar de verdade é o próprio ponto do slicer, não algo que valha
# simular). Ordem = prioridade de fallback quando um adapter real existir.
_SLICER_PROVIDERS: list[SlicerProvider] = [
    PrusaSlicerCLIProvider(),
    OrcaSlicerCLIProvider(),
]


def get_slicer_providers() -> list[SlicerProvider]:
    return _SLICER_PROVIDERS
