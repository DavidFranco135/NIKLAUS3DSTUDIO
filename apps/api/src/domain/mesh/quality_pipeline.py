from dataclasses import dataclass, field

from src.domain.mesh.operations import (
    compute_area_mm2,
    compute_volume_mm3,
    count_components,
    export_mesh,
    fill_holes,
    fix_normals,
    is_manifold,
    is_watertight,
    load_mesh,
    remove_degenerate_faces,
)


@dataclass(frozen=True)
class MeshQualityReport:
    is_watertight: bool
    is_manifold: bool
    component_count: int
    volume_mm3: float
    area_mm2: float
    repairs_applied: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)


def run_quality_pipeline(file_bytes: bytes, kind: str) -> tuple[bytes, MeshQualityReport]:
    """Loads the mesh, applies the repairs that are always safe (degenerate

    faces, holes, normals — never silently drops geometry like disconnected
    components would), and reports what's left. Not the Printability Engine
    (Fase 9, which will also check overhangs/wall thickness/print-bed fit) —
    this is the structural, geometry-level pass described in ARCHITECTURE.md
    section 12.
    """
    mesh = load_mesh(file_bytes, kind)
    repairs_applied: list[str] = []

    if mesh.nondegenerate_faces().sum() < len(mesh.faces):
        remove_degenerate_faces(mesh)
        repairs_applied.append("remove_degenerate_faces")

    if not is_watertight(mesh):
        fill_holes(mesh)
        repairs_applied.append("fill_holes")

    # A mesh can be internally winding-consistent (every face agrees with its
    # neighbors) while still being uniformly inside-out — all normals point
    # inward, giving a negative signed volume. `is_winding_consistent` alone
    # misses that case, so a negative volume also triggers the same fix.
    if not mesh.is_winding_consistent or mesh.volume < 0:
        fix_normals(mesh)
        repairs_applied.append("fix_normals")

    component_count = count_components(mesh)
    volume_mm3 = compute_volume_mm3(mesh)
    watertight = is_watertight(mesh)
    manifold = is_manifold(mesh)

    blocking_issues = []
    if not watertight:
        blocking_issues.append(
            "Malha não é watertight mesmo após tentativa de reparo (fill_holes)."
        )
    if not manifold:
        blocking_issues.append("Malha não é 2-manifold mesmo após tentativa de reparo.")
    if volume_mm3 <= 0:
        blocking_issues.append(f"Volume calculado é {volume_mm3}mm³ — malha degenerada ou vazia.")

    report = MeshQualityReport(
        is_watertight=watertight,
        is_manifold=manifold,
        component_count=component_count,
        volume_mm3=volume_mm3,
        area_mm2=compute_area_mm2(mesh),
        repairs_applied=repairs_applied,
        blocking_issues=blocking_issues,
    )
    repaired_bytes = export_mesh(mesh, kind) if repairs_applied else file_bytes
    return repaired_bytes, report
