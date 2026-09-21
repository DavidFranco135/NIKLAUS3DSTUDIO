import build123d as bd

from src.domain.cad.templates.validation import require_positive_dimensions


def build_generic_box(*, width_mm: float, height_mm: float, thickness_mm: float) -> bd.Part:
    """Plain solid box — fallback when the object type isn't a recognized

    template but the user still gave exact dimensions (classify_task already
    decided PARAMETRIC_CAD is the right engine; this is what runs when no
    more specific template keyword matched).
    """
    require_positive_dimensions(width_mm=width_mm, height_mm=height_mm, thickness_mm=thickness_mm)

    with bd.BuildPart() as part:
        bd.Box(width_mm, height_mm, thickness_mm)

    return part.part
