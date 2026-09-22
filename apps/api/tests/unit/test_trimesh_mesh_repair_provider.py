import trimesh

from src.domain.ai.ports import MeshRef, OptimizeOptions, RepairOptions
from src.domain.mesh.operations import load_mesh
from src.infrastructure.ai_providers.real.trimesh_mesh_repair import TrimeshMeshRepairProvider


def _mesh_ref(mesh: trimesh.Trimesh) -> MeshRef:
    return MeshRef(
        storage_key="org/x/some.stl",
        mime_type="model/stl",
        kind="model_stl",
        file_bytes=mesh.export(file_type="stl"),
    )


def test_repair_mesh_fills_hole_and_reports_metadata():
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    mesh.faces = mesh.faces[1:]
    mesh.process()
    provider = TrimeshMeshRepairProvider()

    result = provider.repair_mesh(_mesh_ref(mesh), RepairOptions())

    assert "fill_holes" in result.metadata["repairs_applied"]
    assert result.metadata["is_watertight"] is True
    assert load_mesh(result.file_bytes, "model_stl").is_watertight


def test_optimize_mesh_reduces_face_count():
    mesh = trimesh.creation.icosphere(subdivisions=3)
    provider = TrimeshMeshRepairProvider()

    result = provider.optimize_mesh(_mesh_ref(mesh), OptimizeOptions(target_triangle_count=200))

    optimized = load_mesh(result.file_bytes, "model_stl")
    assert len(optimized.faces) < len(mesh.faces)
    assert result.metadata["face_count"] == len(optimized.faces)


def test_health_check_reports_healthy():
    assert TrimeshMeshRepairProvider().health_check().healthy is True
