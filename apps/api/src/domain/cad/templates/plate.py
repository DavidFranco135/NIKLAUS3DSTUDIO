import build123d as bd

from src.domain.cad.templates.validation import require_positive_dimensions

_CORNER_RADIUS_RATIO = 0.04
_TEXT_HEIGHT_RATIO = 0.22
_TEXT_DEPTH_MM = 0.6


def build_plate(
    *, width_mm: float, height_mm: float, thickness_mm: float, text: str | None
) -> bd.Part:
    """A flat rectangular plate (slightly rounded corners), optionally with

    text embossed on the front — placas/letreiros simples (ARCHITECTURE.md
    section 11 covers a dedicated, more capable text-3D module later).
    """
    require_positive_dimensions(width_mm=width_mm, height_mm=height_mm, thickness_mm=thickness_mm)

    corner_radius = min(width_mm, height_mm) * _CORNER_RADIUS_RATIO

    with bd.BuildPart() as part:
        with bd.BuildSketch():
            bd.RectangleRounded(width_mm, height_mm, corner_radius)
        bd.extrude(amount=thickness_mm)

        if text:
            top_face = part.faces().sort_by(bd.Axis.Z)[-1]
            with bd.BuildSketch(top_face):
                bd.Text(text, font_size=min(width_mm, height_mm) * _TEXT_HEIGHT_RATIO)
            bd.extrude(amount=_TEXT_DEPTH_MM)

    return part.part
