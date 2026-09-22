from dataclasses import dataclass, field


@dataclass(frozen=True)
class PrintabilityIssue:
    code: str
    severity: str  # "info" | "warning" | "error"
    detail: str
    auto_fixable: bool = False


@dataclass(frozen=True)
class PrintabilityReport:
    """Never a single quality score — a list of concrete, actionable

    problems, per ARCHITECTURE.md section 12/13. `is_manifold`/`is_watertight`/
    `volume_mm3` mirror Fase 8's mesh quality checks (which already ran and
    blocked the job before this report is ever produced, in the AI Orchestrator
    flow) — kept here too so this module is honestly complete on its own for
    any future caller that isn't going through that pipeline.
    """

    is_manifold: bool
    is_watertight: bool
    volume_mm3: float
    bounding_box_mm: tuple[float, float, float]
    overhang_area_ratio: float
    max_overhang_angle_deg: float
    min_wall_thickness_mm: float | None
    issues: list[PrintabilityIssue] = field(default_factory=list)
