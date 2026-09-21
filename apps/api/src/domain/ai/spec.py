from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(StrEnum):
    PARAMETRIC_CAD = "PARAMETRIC_CAD"
    TEXT_TO_GENERATIVE_3D = "TEXT_TO_GENERATIVE_3D"


class Dimensions(BaseModel):
    width_mm: float | None = None
    height_mm: float | None = None
    thickness_mm: float | None = None

    def is_fully_specified(self) -> bool:
        return None not in (self.width_mm, self.height_mm, self.thickness_mm)


class StructuredSpecification(BaseModel):
    """Extracted from the user's free-text prompt by the (mocked, in Fase 4) NLU step.

    Never trusted as an instruction to execute directly — only as typed, validated
    data consumed by the classifier and by provider adapters.
    """

    object_type: str | None = None
    dimensions: Dimensions = Field(default_factory=Dimensions)
    text: str | None = None
    hole_diameter_mm: float | None = None
    material_hint: str | None = None
    output_format: str = "model_stl"
    extra: dict[str, Any] = Field(default_factory=dict)
