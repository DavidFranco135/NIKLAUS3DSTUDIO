import pytest

from src.domain.cad.templates.box import build_box
from src.domain.cad.templates.generic import build_generic_box
from src.domain.cad.templates.keychain import build_keychain
from src.domain.cad.templates.plate import build_plate
from src.domain.cad.templates.validation import require_positive_dimensions
from src.domain.shared.exceptions import InvalidCADParametersError


def test_keychain_with_hole_and_text_is_valid_and_reduces_volume():
    part = build_keychain(
        width_mm=70, height_mm=35, thickness_mm=4, hole_diameter_mm=5, text="CARLOS"
    )
    solid_box_volume = 70 * 35 * 4
    assert part.is_valid
    assert 0 < part.volume < solid_box_volume


def test_keychain_without_text_still_valid():
    part = build_keychain(
        width_mm=60, height_mm=30, thickness_mm=4, hole_diameter_mm=4, text=None
    )
    assert part.is_valid


def test_keychain_rejects_hole_too_large_for_plate():
    with pytest.raises(InvalidCADParametersError):
        build_keychain(width_mm=20, height_mm=20, thickness_mm=4, hole_diameter_mm=15, text=None)


def test_plate_with_and_without_text_is_valid():
    plain = build_plate(width_mm=100, height_mm=50, thickness_mm=3, text=None)
    labeled = build_plate(width_mm=100, height_mm=50, thickness_mm=3, text="LOJA")
    assert plain.is_valid
    assert labeled.is_valid
    assert labeled.volume > plain.volume


def test_hollow_box_has_less_volume_than_solid_box():
    part = build_box(width_mm=60, height_mm=40, thickness_mm=30, wall_mm=2)
    assert part.is_valid
    assert 0 < part.volume < 60 * 40 * 30


def test_box_rejects_wall_too_thick():
    with pytest.raises(InvalidCADParametersError):
        build_box(width_mm=10, height_mm=10, thickness_mm=10, wall_mm=8)


def test_generic_box_matches_solid_volume():
    part = build_generic_box(width_mm=20, height_mm=10, thickness_mm=5)
    assert part.is_valid
    assert part.volume == pytest.approx(20 * 10 * 5)


@pytest.mark.parametrize("width,height,thickness", [(0, 10, 10), (10, -5, 10), (10, 10, 5000)])
def test_require_positive_dimensions_rejects_out_of_range(width, height, thickness):
    with pytest.raises(InvalidCADParametersError):
        require_positive_dimensions(width_mm=width, height_mm=height, thickness_mm=thickness)
