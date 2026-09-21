from src.domain.ai.ports import GenerationResult, ImageInput, ImageTo3DProvider, ProviderHealth
from src.domain.ai.spec import StructuredSpecification
from src.infrastructure.ai_providers.stubs._not_configured import (
    not_configured_health,
    raise_not_configured,
)

_MODEL_NAME = "SPAR3D"


class SPAR3DProvider(ImageTo3DProvider):
    """Placeholder adapter for Stability AI's SPAR3D (image-to-3D).

    Mesma família de licenciamento do Stable Fast 3D — reconfirmar termos
    vigentes antes de integrar de verdade (ver docs/AI-LICENSES.md).
    """

    name = "spar3d"

    def health_check(self) -> ProviderHealth:
        return not_configured_health(_MODEL_NAME)

    def generate_from_image(
        self, image: ImageInput, spec: StructuredSpecification
    ) -> GenerationResult:
        raise_not_configured(_MODEL_NAME)
