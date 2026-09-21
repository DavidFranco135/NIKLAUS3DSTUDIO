import build123d as bd

from src.domain.cad.templates.validation import require_positive_dimensions
from src.domain.shared.exceptions import InvalidCADParametersError

_CORNER_RADIUS_RATIO = 0.08
_TEXT_HEIGHT_RATIO = 0.28
_TEXT_DEPTH_MM = 0.6
_MIN_HOLE_MARGIN_MM = 6.0
_HOLE_MARGIN_RATIO = 1.5


def build_keychain(
    *,
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    hole_diameter_mm: float,
    text: str | None,
) -> bd.Part:
    """A rounded plate with a mounting hole near one corner and, if `text` is

    given, the text embossed on the front face — the exact example from
    ARCHITECTURE.md section 7 ("chaveiro de 70x35x4mm com o nome CARLOS").
    """
    require_positive_dimensions(width_mm=width_mm, height_mm=height_mm, thickness_mm=thickness_mm)

    corner_radius = min(width_mm, height_mm) * _CORNER_RADIUS_RATIO
    hole_margin = max(hole_diameter_mm * _HOLE_MARGIN_RATIO, _MIN_HOLE_MARGIN_MM)
    if hole_margin * 2 >= min(width_mm, height_mm):
        raise InvalidCADParametersError(
            f"hole_diameter_mm={hole_diameter_mm} grande demais para {width_mm}x{height_mm}mm"
        )

    with bd.BuildPart() as part:
        with bd.BuildSketch():
            bd.RectangleRounded(width_mm, height_mm, corner_radius)
        bd.extrude(amount=thickness_mm)

        hole_x = width_mm / 2 - hole_margin
        hole_y = height_mm / 2 - hole_margin
        with bd.Locations((hole_x, hole_y, 0)):
            bd.Cylinder(hole_diameter_mm / 2, thickness_mm * 3, mode=bd.Mode.SUBTRACT)

        if text:
            top_face = part.faces().sort_by(bd.Axis.Z)[-1]
            with bd.BuildSketch(top_face):
                bd.Text(text, font_size=height_mm * _TEXT_HEIGHT_RATIO)
            bd.extrude(amount=_TEXT_DEPTH_MM)

    return part.part
