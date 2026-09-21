from src.domain.ai.ports import GenerationResult, ImageInput, ImageTo3DProvider, ProviderHealth
from src.domain.ai.spec import StructuredSpecification
from src.infrastructure.ai_providers.stubs._not_configured import (
    not_configured_health,
    raise_not_configured,
)

_MODEL_NAME = "TRELLIS"


class TrellisProvider(ImageTo3DProvider):
    """Placeholder adapter for Microsoft Research TRELLIS (image-to-3D).

    Código costuma ser MIT, mas os pesos publicados podem ter condição
    própria — confirmar no model card antes de integrar de verdade (ver
    docs/AI-LICENSES.md).
    """

    name = "trellis"

    def health_check(self) -> ProviderHealth:
        return not_configured_health(_MODEL_NAME)

    def generate_from_image(
        self, image: ImageInput, spec: StructuredSpecification
    ) -> GenerationResult:
        raise_not_configured(_MODEL_NAME)
