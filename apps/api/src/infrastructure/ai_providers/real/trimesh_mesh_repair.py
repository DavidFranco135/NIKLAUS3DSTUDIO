from src.domain.ai.ports import (
    MeshRef,
    MeshRepairProvider,
    MeshResult,
    OptimizeOptions,
    ProviderHealth,
    RepairOptions,
)
from src.domain.mesh.operations import (
    compute_volume_mm3,
    export_mesh,
    fill_holes,
    fix_normals,
    is_manifold,
    is_watertight,
    load_mesh,
    remove_degenerate_faces,
    simplify,
)

_DEFAULT_SIMPLIFY_RATIO = 0.5


class TrimeshMeshRepairProvider(MeshRepairProvider):
    """Real mesh repair/optimization via trimesh (MIT license, no GPU — see

    AI-LICENSES.md). Standalone provider matching the port designed in Fase 5;
    the AI Orchestrator's own post-generation step uses
    `domain/mesh/quality_pipeline.py` directly instead of going through this
    provider, since that step always wants the same safe repairs and doesn't
    need the fuller `RepairOptions`/`OptimizeOptions` flexibility this offers
    for a future direct "repair my upload" feature.
    """

    name = "trimesh_mesh_repair"

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(healthy=True)

    def repair_mesh(self, mesh: MeshRef, options: RepairOptions) -> MeshResult:
        loaded = load_mesh(mesh.file_bytes, mesh.kind)
        repairs_applied: list[str] = []

        if options.remove_degenerate_faces and loaded.nondegenerate_faces().sum() < len(
            loaded.faces
        ):
            remove_degenerate_faces(loaded)
            repairs_applied.append("remove_degenerate_faces")

        if options.fill_holes and not is_watertight(loaded):
            fill_holes(loaded)
            repairs_applied.append("fill_holes")

        if options.fix_normals and not loaded.is_winding_consistent:
            fix_normals(loaded)
            repairs_applied.append("fix_normals")

        return MeshResult(
            file_bytes=export_mesh(loaded, mesh.kind),
            mime_type=mesh.mime_type,
            kind=mesh.kind,
            metadata={
                "provider": self.name,
                "repairs_applied": repairs_applied,
                "is_watertight": is_watertight(loaded),
                "is_manifold": is_manifold(loaded),
                "volume_mm3": compute_volume_mm3(loaded),
            },
        )

    def optimize_mesh(self, mesh: MeshRef, options: OptimizeOptions) -> MeshResult:
        loaded = load_mesh(mesh.file_bytes, mesh.kind)
        operations_applied: list[str] = []

        if options.simplify:
            ratio = _DEFAULT_SIMPLIFY_RATIO
            if options.target_triangle_count:
                ratio = min(1.0, options.target_triangle_count / max(1, len(loaded.faces)))
            loaded = simplify(loaded, target_ratio=ratio)
            operations_applied.append("simplify")

        return MeshResult(
            file_bytes=export_mesh(loaded, mesh.kind),
            mime_type=mesh.mime_type,
            kind=mesh.kind,
            metadata={
                "provider": self.name,
                "operations_applied": operations_applied,
                "face_count": len(loaded.faces),
            },
        )
