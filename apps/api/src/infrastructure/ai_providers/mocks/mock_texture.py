from src.domain.ai.ports import MeshRef, ProviderHealth, TextureProvider, TextureResult, TextureSpec
from src.infrastructure.ai_providers.mocks.solid_color_png import generate_solid_color_png

_PLACEHOLDER_RGB = (160, 160, 160)
_PLACEHOLDER_RESOLUTION_PX = 64


class MockTextureProvider(TextureProvider):
    """Stands in for a real texture-generation model. Returns a flat gray

    square PNG regardless of input — no such model is integrated yet.
    """

    name = "mock_texture"

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(healthy=True)

    def generate_texture(self, mesh: MeshRef, spec: TextureSpec) -> TextureResult:
        png_bytes = generate_solid_color_png(
            _PLACEHOLDER_RESOLUTION_PX, _PLACEHOLDER_RESOLUTION_PX, _PLACEHOLDER_RGB
        )
        return TextureResult(
            file_bytes=png_bytes,
            mime_type="image/png",
            metadata={
                "provider": self.name,
                "placeholder": True,
                "note": "Textura cinza-sólida placeholder — nenhum modelo de textura integrado.",
                "requested_prompt": spec.prompt,
            },
        )
