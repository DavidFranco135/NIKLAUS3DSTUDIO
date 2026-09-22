import pytest
import trimesh

from src.domain.mesh.operations import load_mesh
from src.domain.mesh.quality_pipeline import run_quality_pipeline


def test_clean_mesh_passes_with_no_repairs_needed():
    stl_bytes = trimesh.creation.box(extents=[10, 10, 10]).export(file_type="stl")

    repaired_bytes, report = run_quality_pipeline(stl_bytes, "model_stl")

    assert report.blocking_issues == []
    assert report.repairs_applied == []
    assert report.is_watertight
    assert report.is_manifold
    assert report.volume_mm3 == pytest.approx(1000, rel=0.01)
    assert repaired_bytes == stl_bytes


def test_mesh_with_hole_gets_repaired_and_passes():
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    mesh.faces = mesh.faces[1:]
    mesh.process()
    stl_bytes = mesh.export(file_type="stl")

    repaired_bytes, report = run_quality_pipeline(stl_bytes, "model_stl")

    assert "fill_holes" in report.repairs_applied
    assert report.is_watertight
    assert report.blocking_issues == []
    assert load_mesh(repaired_bytes, "model_stl").is_watertight


def test_inside_out_mesh_gets_normals_fixed():
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    mesh.invert()
    stl_bytes = mesh.export(file_type="stl")

    repaired_bytes, report = run_quality_pipeline(stl_bytes, "model_stl")

    assert "fix_normals" in report.repairs_applied
    assert report.volume_mm3 > 0
    assert load_mesh(repaired_bytes, "model_stl").volume > 0


def test_multiple_components_reported_but_not_blocking():
    big = trimesh.creation.box(extents=[10, 10, 10])
    small = trimesh.creation.box(extents=[2, 2, 2]).apply_translation([50, 0, 0])
    stl_bytes = trimesh.util.concatenate([big, small]).export(file_type="stl")

    _repaired_bytes, report = run_quality_pipeline(stl_bytes, "model_stl")

    assert report.component_count == 2
    assert report.blocking_issues == []
