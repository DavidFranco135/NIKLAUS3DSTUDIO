from src.domain.ai.ports import GenerationResult, ImageInput, ImageTo3DProvider, ProviderHealth
from src.domain.ai.spec import StructuredSpecification
from src.infrastructure.ai_providers.mocks.stl_box import generate_box_stl

_PLACEHOLDER_SIZE_MM = 50.0


class MockImageTo3DProvider(ImageTo3DProvider):
    """Development-only stand-in for a real image-to-3D engine (Hunyuan3D,

    TRELLIS, Stable Fast 3D, SPAR3D — none integrated yet, see AI-LICENSES.md).
    Ignores the image entirely and returns a placeholder cube — this proves
    the upload → job → orchestrator → version pipeline end to end, but it is
    NOT 3D reconstruction and must never be presented to a user as one.
    """

    name = "mock_image_to_3d"

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            healthy=True,
            detail=(
                "Provider de DESENVOLVIMENTO — gera um cubo placeholder, "
                "não reconstrói a imagem."
            ),
        )

    def generate_from_image(
        self, image: ImageInput, spec: StructuredSpecification
    ) -> GenerationResult:
        stl_bytes = generate_box_stl(
            _PLACEHOLDER_SIZE_MM, _PLACEHOLDER_SIZE_MM, _PLACEHOLDER_SIZE_MM
        )
        return GenerationResult(
            file_bytes=stl_bytes,
            mime_type="model/stl",
            kind="model_stl",
            metadata={
                "provider": self.name,
                "placeholder": True,
                "development_only": True,
                "note": (
                    "MOCK DE DESENVOLVIMENTO — não é uma reconstrução 3D real da imagem "
                    f"enviada ({image.mime_type}). Devolve sempre o mesmo cubo placeholder. "
                    "Nenhum modelo generativo real foi executado (ver docs/AI.md)."
                ),
            },
        )
