import os
import tempfile

import build123d as bd

from src.domain.ai.ports import CADProvider, GenerationResult, ProviderHealth
from src.domain.ai.spec import StructuredSpecification
from src.domain.cad.templates.box import build_box
from src.domain.cad.templates.generic import build_generic_box
from src.domain.cad.templates.keychain import build_keychain
from src.domain.cad.templates.plate import build_plate
from src.domain.shared.exceptions import InvalidCADParametersError

_DEFAULT_KEYCHAIN_HOLE_MM = 4.0


def _export_stl_bytes(part: bd.Part) -> bytes:
    fd, path = tempfile.mkstemp(suffix=".stl")
    os.close(fd)
    try:
        bd.export_stl(part, path)
        with open(path, "rb") as stl_file:
            return stl_file.read()
    finally:
        os.remove(path)


class Build123DCADProvider(CADProvider):
    """Real parametric CAD engine (build123d — OCCT/BREP kernel, Apache-2.0/

    LGPL, see AI-LICENSES.md). Picks a template by `spec.object_type`, builds
    real solid geometry (booleans, fillets, text embossing — not a hand-rolled
    box like the Fase 4 mock), and exports a genuine STL.
    """

    name = "build123d_cad"

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(healthy=True)

    def create_parametric_model(self, spec: StructuredSpecification) -> GenerationResult:
        dims = spec.dimensions
        if not dims.is_fully_specified():
            raise InvalidCADParametersError(
                "Build123DCADProvider requer width/height/thickness em mm"
            )

        object_type = (spec.object_type or "").lower()
        if object_type == "keychain":
            hole_diameter_mm = spec.hole_diameter_mm or _DEFAULT_KEYCHAIN_HOLE_MM
            part = build_keychain(
                width_mm=dims.width_mm,
                height_mm=dims.height_mm,
                thickness_mm=dims.thickness_mm,
                hole_diameter_mm=hole_diameter_mm,
                text=spec.text,
            )
            template_used = "keychain"
        elif object_type in ("plate", "sign"):
            part = build_plate(
                width_mm=dims.width_mm,
                height_mm=dims.height_mm,
                thickness_mm=dims.thickness_mm,
                text=spec.text,
            )
            template_used = "plate"
        elif object_type == "box":
            part = build_box(
                width_mm=dims.width_mm, height_mm=dims.height_mm, thickness_mm=dims.thickness_mm
            )
            template_used = "box"
        else:
            part = build_generic_box(
                width_mm=dims.width_mm, height_mm=dims.height_mm, thickness_mm=dims.thickness_mm
            )
            template_used = "generic_box"

        if not part.is_valid:
            raise InvalidCADParametersError(
                f"Geometria inválida gerada pelo template '{template_used}' "
                f"para {dims.model_dump()}"
            )

        stl_bytes = _export_stl_bytes(part)
        return GenerationResult(
            file_bytes=stl_bytes,
            mime_type="model/stl",
            kind="model_stl",
            metadata={
                "provider": self.name,
                "template": template_used,
                "volume_mm3": part.volume,
                "dimensions_mm": dims.model_dump(),
            },
        )
