from src.domain.ai.ports import CADProvider, GenerationResult, ProviderHealth
from src.domain.ai.spec import StructuredSpecification
from src.infrastructure.ai_providers.mocks.stl_box import generate_box_stl


class MockBoxCADProvider(CADProvider):
    """Placeholder CAD engine: turns exact dimensions into a plain box STL.

    Stands in for the real OpenSCAD/build123d integration (Fase 7). Good
    enough to prove the orchestrator picks CAD over generative 3D whenever
    the user gives precise measurements.
    """

    name = "mock_box_cad"

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(healthy=True)

    def create_parametric_model(self, spec: StructuredSpecification) -> GenerationResult:
        dims = spec.dimensions
        if not dims.is_fully_specified():
            raise ValueError("MockBoxCADProvider requires width/height/thickness in mm")

        stl_bytes = generate_box_stl(dims.width_mm, dims.height_mm, dims.thickness_mm)
        return GenerationResult(
            file_bytes=stl_bytes,
            mime_type="model/stl",
            kind="model_stl",
            metadata={
                "provider": self.name,
                "placeholder": True,
                "dimensions_mm": dims.model_dump(),
                "note": "Caixa retangular placeholder — motor CAD real (OpenSCAD) chega na Fase 7.",
            },
        )
