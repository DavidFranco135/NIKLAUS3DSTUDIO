import pytest
import trimesh

from src.domain.printability.thin_walls import analyze_min_wall_thickness


def test_solid_cube_reports_thickness_close_to_its_extent():
    box = trimesh.creation.box(extents=[10, 10, 10])
    thickness = analyze_min_wall_thickness(box)
    assert thickness == pytest.approx(10.0, abs=0.1)


def test_solid_box_reports_thickness_close_to_its_shortest_extent():
    box = trimesh.creation.box(extents=[10, 10, 4])
    thickness = analyze_min_wall_thickness(box)
    assert thickness == pytest.approx(4.0, abs=0.1)


def test_thin_shell_wall_is_detected():
    outer = trimesh.creation.box(extents=[10, 10, 10])
    inner = trimesh.creation.box(extents=[9.4, 9.4, 9.4])
    inner.invert()
    shell = trimesh.util.concatenate([outer, inner])

    thickness = analyze_min_wall_thickness(shell)
    assert thickness == pytest.approx(0.3, abs=0.05)


def test_empty_mesh_returns_none():
    empty = trimesh.Trimesh(vertices=[], faces=[])
    assert analyze_min_wall_thickness(empty) is None
