from src.domain.ai.classifier import classify_task
from src.domain.ai.spec import Dimensions, StructuredSpecification, TaskType


def test_classifies_as_parametric_cad_when_dimensions_are_exact():
    spec = StructuredSpecification(dimensions=Dimensions(width_mm=70, height_mm=35, thickness_mm=4))
    assert classify_task(spec) == TaskType.PARAMETRIC_CAD


def test_classifies_as_generative_when_dimensions_are_missing():
    spec = StructuredSpecification(object_type="statue")
    assert classify_task(spec) == TaskType.TEXT_TO_GENERATIVE_3D


def test_classifies_as_generative_when_dimensions_are_partial():
    spec = StructuredSpecification(dimensions=Dimensions(width_mm=70, height_mm=35))
    assert classify_task(spec) == TaskType.TEXT_TO_GENERATIVE_3D
