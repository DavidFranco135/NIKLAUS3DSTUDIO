from src.domain.ai.ports import (
    MeshRef,
    MeshRepairProvider,
    MeshResult,
    OptimizeOptions,
    ProviderHealth,
    RepairOptions,
)


class MockMeshRepairProvider(MeshRepairProvider):
    """Passthrough stand-in for real mesh repair/optimization (trimesh/Open3D,

    Fase 8 — Mesh Processing). Doesn't touch the bytes; a real implementation
    can't be honest about "repaired" without actually parsing the mesh, which
    is exactly the dependency this mock intentionally avoids for now.
    """

    name = "mock_mesh_repair"

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(healthy=True)

    def repair_mesh(self, mesh: MeshRef, options: RepairOptions) -> MeshResult:
        return MeshResult(
            file_bytes=b"",
            mime_type=mesh.mime_type,
            kind="model_stl",
            metadata={
                "provider": self.name,
                "placeholder": True,
                "note": "No-op — reparo real de malha chega na Fase 8 (Mesh Processing).",
                "source_storage_key": mesh.storage_key,
            },
        )

    def optimize_mesh(self, mesh: MeshRef, options: OptimizeOptions) -> MeshResult:
        return MeshResult(
            file_bytes=b"",
            mime_type=mesh.mime_type,
            kind="model_stl",
            metadata={
                "provider": self.name,
                "placeholder": True,
                "note": "No-op — otimização real de malha chega na Fase 8 (Mesh Processing).",
                "source_storage_key": mesh.storage_key,
            },
        )
