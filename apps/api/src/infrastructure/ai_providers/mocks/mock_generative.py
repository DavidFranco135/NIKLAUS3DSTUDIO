from src.domain.ai.ports import GenerationResult, ProviderHealth, TextTo3DProvider
from src.domain.ai.spec import StructuredSpecification
from src.domain.shared.exceptions import ProviderUnavailableError
from src.infrastructure.ai_providers.mocks.stl_box import generate_box_stl

_PLACEHOLDER_SIZE_MM = 50.0


class AlwaysFailingMockProvider(TextTo3DProvider):
    """Simulates a generative provider that is down — exists to exercise fallback."""

    name = "mock_generative_unavailable"

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(healthy=False, detail="simulated outage")

    def generate_from_text(self, spec: StructuredSpecification) -> GenerationResult:
        raise ProviderUnavailableError(f"{self.name} is simulated as unavailable")


class PlaceholderMockProvider(TextTo3DProvider):
    """Stands in for a real generative model (Hunyuan3D/TRELLIS/... — Fase 5).

    Always returns the same placeholder cube; the point is proving the
    orchestrator's dispatch/fallback/result pipeline, not shape quality.
    """

    name = "mock_generative_placeholder"

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(healthy=True)

    def generate_from_text(self, spec: StructuredSpecification) -> GenerationResult:
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
                    "Cubo placeholder — nenhum modelo generativo real integrado ainda "
                    "(Hunyuan3D/TRELLIS/Stable Fast 3D/SPAR3D chegam na Fase 5/6)."
                ),
                "requested_object_type": spec.object_type,
            },
        )
