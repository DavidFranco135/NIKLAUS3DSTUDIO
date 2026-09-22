import pytest
import trimesh

from src.domain.printability.overhang import analyze_overhangs


def test_box_resting_on_bed_has_no_overhang():
    box = trimesh.creation.box(extents=[10, 10, 10])
    ratio, max_angle = analyze_overhangs(box)
    assert ratio == 0.0
    assert max_angle == 0.0


def test_cylinder_resting_on_bed_has_no_overhang():
    cylinder = trimesh.creation.cylinder(radius=5, height=10)
    ratio, max_angle = analyze_overhangs(cylinder)
    assert ratio == 0.0
    assert max_angle == 0.0


def test_wide_cap_on_a_narrow_pillar_is_flagged_as_overhang():
    pillar = trimesh.creation.box(extents=[4, 4, 20])
    pillar.apply_translation([0, 0, 10])
    cap = trimesh.creation.box(extents=[20, 20, 4])
    cap.apply_translation([0, 0, 22])
    combined = trimesh.util.concatenate([pillar, cap])

    ratio, max_angle = analyze_overhangs(combined)
    assert ratio > 0.2
    assert max_angle == pytest.approx(90.0, abs=1.0)
