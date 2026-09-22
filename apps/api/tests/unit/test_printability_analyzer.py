import trimesh

from src.domain.printability.analyzer import analyze_printability


def _stl_bytes(mesh: trimesh.Trimesh) -> bytes:
    return mesh.export(file_type="stl")


def test_clean_box_has_no_issues():
    box_bytes = _stl_bytes(trimesh.creation.box(extents=[10, 10, 10]))
    report = analyze_printability(box_bytes, "model_stl")
    assert report.is_watertight
    assert report.is_manifold
    assert report.issues == []


def test_tiny_model_is_flagged_too_small():
    box_bytes = _stl_bytes(trimesh.creation.box(extents=[0.2, 0.2, 0.2]))
    report = analyze_printability(box_bytes, "model_stl")
    codes = [issue.code for issue in report.issues]
    assert "TOO_SMALL" in codes


def test_oversized_model_is_flagged_too_large():
    box_bytes = _stl_bytes(trimesh.creation.box(extents=[400, 10, 10]))
    report = analyze_printability(box_bytes, "model_stl")
    codes = [issue.code for issue in report.issues]
    assert "TOO_LARGE" in codes


def test_thin_shell_is_flagged_thin_wall():
    outer = trimesh.creation.box(extents=[10, 10, 10])
    inner = trimesh.creation.box(extents=[9.4, 9.4, 9.4])
    inner.invert()
    shell = trimesh.util.concatenate([outer, inner])

    report = analyze_printability(_stl_bytes(shell), "model_stl")
    codes = [issue.code for issue in report.issues]
    assert "THIN_WALL" in codes
    assert report.min_wall_thickness_mm < 0.5


def test_wide_cap_on_narrow_pillar_is_flagged_overhang():
    pillar = trimesh.creation.box(extents=[4, 4, 20])
    pillar.apply_translation([0, 0, 10])
    cap = trimesh.creation.box(extents=[20, 20, 4])
    cap.apply_translation([0, 0, 22])
    combined = trimesh.util.concatenate([pillar, cap])

    report = analyze_printability(_stl_bytes(combined), "model_stl")
    codes = [issue.code for issue in report.issues]
    assert "OVERHANG" in codes
    assert report.overhang_area_ratio > 0.2
