from src.domain.ai.ports import GenerationResult, ImageInput, ImageTo3DProvider, ProviderHealth
from src.domain.ai.spec import StructuredSpecification
from src.infrastructure.ai_providers.stubs._not_configured import (
    not_configured_health,
    raise_not_configured,
)

_MODEL_NAME = "Stable Fast 3D"


class StableFast3DProvider(ImageTo3DProvider):
    """Placeholder adapter for Stability AI's Stable Fast 3D (image-to-3D).

    A Stability AI Community License historicamente exige "membership" pago
    acima de um limite de receita — reconfirmar antes de integrar de verdade
    (ver docs/AI-LICENSES.md).
    """

    name = "stable_fast_3d"

    def health_check(self) -> ProviderHealth:
        return not_configured_health(_MODEL_NAME)

    def generate_from_image(
        self, image: ImageInput, spec: StructuredSpecification
    ) -> GenerationResult:
        raise_not_configured(_MODEL_NAME)
