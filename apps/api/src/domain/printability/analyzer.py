from src.domain.mesh.operations import (
    compute_volume_mm3,
    is_manifold,
    is_watertight,
    load_mesh,
)
from src.domain.printability.overhang import DEFAULT_OVERHANG_THRESHOLD_DEG, analyze_overhangs
from src.domain.printability.report import PrintabilityIssue, PrintabilityReport
from src.domain.printability.thin_walls import analyze_min_wall_thickness

DEFAULT_MIN_WALL_THICKNESS_MM = 0.8
MIN_REASONABLE_DIMENSION_MM = 0.4
MAX_REASONABLE_DIMENSION_MM = 300.0
_MINOR_OVERHANG_RATIO = 0.05
_MAJOR_OVERHANG_RATIO = 0.20


def analyze_printability(
    file_bytes: bytes,
    kind: str,
    *,
    overhang_threshold_deg: float = DEFAULT_OVERHANG_THRESHOLD_DEG,
    min_wall_thickness_mm: float = DEFAULT_MIN_WALL_THICKNESS_MM,
) -> PrintabilityReport:
    """Concrete, actionable problems — never a single quality score

    (ARCHITECTURE.md section 12/13). The `is_manifold`/`is_watertight`/
    `volume_mm3` checks here duplicate what Fase 8's `quality_pipeline`
    already gates on in the AI Orchestrator flow (so those particular issues
    won't normally appear there) — kept so this analyzer is honestly
    self-contained for any future standalone caller (e.g. "check my upload").
    """
    mesh = load_mesh(file_bytes, kind)
    issues: list[PrintabilityIssue] = []

    manifold = is_manifold(mesh)
    watertight = is_watertight(mesh)
    volume_mm3 = compute_volume_mm3(mesh)
    bounding_box_mm = tuple(float(v) for v in mesh.extents)

    if not watertight:
        issues.append(
            PrintabilityIssue(
                code="NON_WATERTIGHT",
                severity="error",
                detail="Modelo não é watertight — não pode ser fatiado com segurança.",
                auto_fixable=True,
            )
        )
    if not manifold:
        issues.append(
            PrintabilityIssue(
                code="NON_MANIFOLD",
                severity="error",
                detail="Modelo não é 2-manifold.",
                auto_fixable=True,
            )
        )
    if volume_mm3 <= 0:
        issues.append(
            PrintabilityIssue(
                code="NEGATIVE_OR_ZERO_VOLUME",
                severity="error",
                detail=f"Volume calculado é {volume_mm3:.2f}mm³ — malha degenerada ou vazia.",
                auto_fixable=True,
            )
        )

    if min(bounding_box_mm) < MIN_REASONABLE_DIMENSION_MM:
        issues.append(
            PrintabilityIssue(
                code="TOO_SMALL",
                severity="warning",
                detail=(
                    f"Dimensão mínima de {min(bounding_box_mm):.2f}mm é menor que um bico "
                    f"típico de {MIN_REASONABLE_DIMENSION_MM}mm."
                ),
            )
        )
    if max(bounding_box_mm) > MAX_REASONABLE_DIMENSION_MM:
        issues.append(
            PrintabilityIssue(
                code="TOO_LARGE",
                severity="warning",
                detail=(
                    f"Dimensão máxima de {max(bounding_box_mm):.1f}mm excede o limite genérico "
                    f"de {MAX_REASONABLE_DIMENSION_MM}mm (sem perfil de impressora ainda — "
                    "ver Fase de Impressoras)."
                ),
            )
        )

    overhang_area_ratio, max_overhang_angle_deg = analyze_overhangs(
        mesh, threshold_deg=overhang_threshold_deg
    )
    if overhang_area_ratio > _MINOR_OVERHANG_RATIO:
        severity = "error" if overhang_area_ratio > _MAJOR_OVERHANG_RATIO else "warning"
        issues.append(
            PrintabilityIssue(
                code="OVERHANG",
                severity=severity,
                detail=(
                    f"Overhang em {overhang_area_ratio * 100:.1f}% da superfície "
                    f"(ângulo máx. ~{max_overhang_angle_deg:.0f}° a partir da vertical) — "
                    "provavelmente precisa de suporte."
                ),
            )
        )

    min_wall_mm = analyze_min_wall_thickness(mesh)
    if min_wall_mm is not None and min_wall_mm < min_wall_thickness_mm:
        issues.append(
            PrintabilityIssue(
                code="THIN_WALL",
                severity="warning",
                detail=(
                    f"Parede de {min_wall_mm:.2f}mm detectada "
                    f"(mínimo recomendado: {min_wall_thickness_mm}mm)."
                ),
            )
        )

    return PrintabilityReport(
        is_manifold=manifold,
        is_watertight=watertight,
        volume_mm3=volume_mm3,
        bounding_box_mm=bounding_box_mm,
        overhang_area_ratio=overhang_area_ratio,
        max_overhang_angle_deg=max_overhang_angle_deg,
        min_wall_thickness_mm=min_wall_mm,
        issues=issues,
    )
