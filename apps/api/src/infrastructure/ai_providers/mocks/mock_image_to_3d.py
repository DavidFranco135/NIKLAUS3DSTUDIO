from src.domain.ai.ports import GenerationResult, ImageInput, ImageTo3DProvider, ProviderHealth
from src.domain.ai.spec import StructuredSpecification
from src.infrastructure.ai_providers.mocks.stl_box import generate_box_stl

_PLACEHOLDER_SIZE_MM = 50.0


class MockImageTo3DProvider(ImageTo3DProvider):
    """Stands in for Hunyuan3D/TRELLIS/Stable Fast 3D/SPAR3D (Fase 6).

    Ignores the image entirely and returns the same placeholder cube as the
    text-to-3D mock — proves the port/orchestrator wiring, not image
    understanding.
    """

    name = "mock_image_to_3d"

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(healthy=True)

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
                "note": (
                    "Cubo placeholder — a imagem recebida (" + image.mime_type + ") foi "
                    "ignorada. Nenhum modelo real de imagem-para-3D integrado ainda (Fase 6)."
                ),
            },
        )
