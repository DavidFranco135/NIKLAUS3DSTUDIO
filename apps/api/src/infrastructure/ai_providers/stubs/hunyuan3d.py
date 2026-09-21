from src.domain.ai.ports import (
    GenerationResult,
    ImageInput,
    ImageTo3DProvider,
    ProviderHealth,
    TextTo3DProvider,
)
from src.domain.ai.spec import StructuredSpecification
from src.infrastructure.ai_providers.stubs._not_configured import (
    not_configured_health,
    raise_not_configured,
)

_MODEL_NAME = "Hunyuan3D"


class Hunyuan3DProvider(ImageTo3DProvider, TextTo3DProvider):
    """Placeholder adapter for Tencent Hunyuan3D — supports both image-to-3D

    and text-to-3D upstream. Licença própria (Tencent Hunyuan Community
    License) ainda não confirmada para uso comercial na nossa escala — ver
    docs/AI-LICENSES.md antes de implementar de verdade.
    """

    name = "hunyuan3d"

    def health_check(self) -> ProviderHealth:
        return not_configured_health(_MODEL_NAME)

    def generate_from_image(
        self, image: ImageInput, spec: StructuredSpecification
    ) -> GenerationResult:
        raise_not_configured(_MODEL_NAME)

    def generate_from_text(self, spec: StructuredSpecification) -> GenerationResult:
        raise_not_configured(_MODEL_NAME)
