import pytest
import trimesh

from src.domain.mesh.operations import (
    center,
    compute_area_mm2,
    compute_volume_mm3,
    count_components,
    export_mesh,
    fill_holes,
    fix_normals,
    is_manifold,
    is_watertight,
    keep_largest_component,
    load_mesh,
    remove_degenerate_faces,
    scale,
    simplify,
    smooth,
    subdivide,
)


def _box_stl_bytes(extents=(10, 10, 10)) -> bytes:
    return trimesh.creation.box(extents=extents).export(file_type="stl")


def test_load_and_export_roundtrip():
    mesh = load_mesh(_box_stl_bytes(), "model_stl")
    assert mesh.is_watertight
    exported = export_mesh(mesh, "model_stl")
    reloaded = load_mesh(exported, "model_stl")
    assert reloaded.is_watertight


def test_watertight_and_manifold_true_for_clean_box():
    mesh = load_mesh(_box_stl_bytes(), "model_stl")
    assert is_watertight(mesh)
    assert is_manifold(mesh)


def test_fill_holes_repairs_a_missing_face():
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    mesh.faces = mesh.faces[1:]
    mesh.process()
    assert not is_watertight(mesh)

    fill_holes(mesh)
    assert is_watertight(mesh)


def test_fix_normals_corrects_inside_out_mesh():
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    mesh.invert()
    assert mesh.volume < 0

    fix_normals(mesh)
    assert mesh.volume > 0


def test_remove_degenerate_faces_drops_zero_area_triangles():
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    degenerate_face = [mesh.vertices[0], mesh.vertices[0], mesh.vertices[0]]
    combined = trimesh.util.concatenate(
        [mesh, trimesh.Trimesh(vertices=degenerate_face, faces=[[0, 1, 2]])]
    )
    before = len(combined.faces)

    remove_degenerate_faces(combined)
    assert len(combined.faces) < before


def test_count_components_and_keep_largest():
    big = trimesh.creation.box(extents=[10, 10, 10])
    small = trimesh.creation.box(extents=[2, 2, 2]).apply_translation([50, 0, 0])
    combined = trimesh.util.concatenate([big, small])

    assert count_components(combined) == 2
    largest = keep_largest_component(combined)
    assert largest.volume == pytest.approx(1000, rel=0.01)


def test_simplify_reduces_face_count():
    mesh = trimesh.creation.icosphere(subdivisions=3)
    simplified = simplify(mesh, target_ratio=0.5)
    assert len(simplified.faces) < len(mesh.faces)


def test_subdivide_increases_face_count():
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    subdivided = subdivide(mesh)
    assert len(subdivided.faces) > len(mesh.faces)


def test_smooth_preserves_topology():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    smoothed = smooth(mesh)
    assert len(smoothed.faces) == len(mesh.faces)


def test_scale_and_center():
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    mesh.apply_translation([5, 5, 5])
    center(mesh)
    assert all(abs(c) < 1e-6 for c in mesh.centroid)

    scale(mesh, factor=2.0)
    assert mesh.extents == pytest.approx([20, 20, 20], rel=0.01)


def test_volume_and_area_are_positive_for_clean_box():
    mesh = load_mesh(_box_stl_bytes(), "model_stl")
    assert compute_volume_mm3(mesh) == pytest.approx(1000, rel=0.01)
    assert compute_area_mm2(mesh) > 0
