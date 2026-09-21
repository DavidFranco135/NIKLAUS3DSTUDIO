import pytest

from src.domain.ai.spec import Dimensions, StructuredSpecification
from src.domain.shared.exceptions import InvalidCADParametersError
from src.infrastructure.ai_providers.real.build123d_cad import Build123DCADProvider


def _spec(
    object_type: str | None,
    *,
    text: str | None = None,
    hole_diameter_mm: float | None = None,
    **dims_kwargs,
) -> StructuredSpecification:
    return StructuredSpecification(
        object_type=object_type,
        dimensions=Dimensions(**dims_kwargs),
        text=text,
        hole_diameter_mm=hole_diameter_mm,
    )


def test_keychain_spec_produces_real_stl_with_hole_and_text():
    provider = Build123DCADProvider()
    spec = _spec(
        "keychain", width_mm=70, height_mm=35, thickness_mm=4, text="CARLOS", hole_diameter_mm=5
    )

    result = provider.create_parametric_model(spec)

    assert result.kind == "model_stl"
    assert len(result.file_bytes) > 84
    assert result.metadata["template"] == "keychain"
    assert result.metadata["provider"] == "build123d_cad"
    assert "placeholder" not in result.metadata


def test_keychain_without_hole_specified_gets_a_default():
    provider = Build123DCADProvider()
    spec = _spec("keychain", width_mm=60, height_mm=30, thickness_mm=4)

    result = provider.create_parametric_model(spec)
    assert result.metadata["template"] == "keychain"


def test_plate_and_sign_object_types_use_plate_template():
    provider = Build123DCADProvider()
    for object_type in ("plate", "sign"):
        spec = _spec(object_type, width_mm=100, height_mm=50, thickness_mm=3)
        result = provider.create_parametric_model(spec)
        assert result.metadata["template"] == "plate"


def test_box_object_type_uses_box_template():
    provider = Build123DCADProvider()
    spec = _spec("box", width_mm=60, height_mm=40, thickness_mm=30)
    result = provider.create_parametric_model(spec)
    assert result.metadata["template"] == "box"


def test_unknown_object_type_falls_back_to_generic_box():
    provider = Build123DCADProvider()
    spec = _spec("gear", width_mm=20, height_mm=20, thickness_mm=5)
    result = provider.create_parametric_model(spec)
    assert result.metadata["template"] == "generic_box"


def test_raises_when_dimensions_are_incomplete():
    provider = Build123DCADProvider()
    spec = StructuredSpecification(object_type="keychain", dimensions=Dimensions(width_mm=70))
    with pytest.raises(InvalidCADParametersError):
        provider.create_parametric_model(spec)
