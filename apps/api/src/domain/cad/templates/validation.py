from src.domain.shared.exceptions import InvalidCADParametersError

MIN_DIMENSION_MM = 1.0
MAX_DIMENSION_MM = 1000.0


def require_positive_dimensions(*, width_mm: float, height_mm: float, thickness_mm: float) -> None:
    dimensions = (("width_mm", width_mm), ("height_mm", height_mm), ("thickness_mm", thickness_mm))
    for name, value in dimensions:
        if not (MIN_DIMENSION_MM <= value <= MAX_DIMENSION_MM):
            raise InvalidCADParametersError(
                f"{name}={value} fora do intervalo permitido "
                f"[{MIN_DIMENSION_MM}, {MAX_DIMENSION_MM}] mm"
            )
