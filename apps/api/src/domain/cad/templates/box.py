import build123d as bd

from src.domain.cad.templates.validation import require_positive_dimensions
from src.domain.shared.exceptions import InvalidCADParametersError

_DEFAULT_WALL_MM = 2.0


def build_box(
    *, width_mm: float, height_mm: float, thickness_mm: float, wall_mm: float = _DEFAULT_WALL_MM
) -> bd.Part:
    """An open-top hollow container (organizador/caixa) — walls of `wall_mm`,

    open on top. `thickness_mm` here is the box's overall height, matching
    the generic width/height/thickness spec used across all templates.
    """
    require_positive_dimensions(width_mm=width_mm, height_mm=height_mm, thickness_mm=thickness_mm)
    if wall_mm <= 0 or wall_mm * 2 >= min(width_mm, height_mm, thickness_mm):
        raise InvalidCADParametersError(
            f"wall_mm={wall_mm} incompatível com {width_mm}x{height_mm}x{thickness_mm}mm"
        )

    with bd.BuildPart() as part:
        bd.Box(width_mm, height_mm, thickness_mm)
        top_face = part.faces().sort_by(bd.Axis.Z)[-1]
        bd.offset(part.part, amount=-wall_mm, openings=top_face)

    return part.part
