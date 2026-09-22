from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SliceResult:
    estimated_time_seconds: float
    filament_length_mm: float
    filament_weight_g: float
    layer_count: int
    support_material_used: bool
    gcode_file_bytes: bytes
    metadata: dict[str, Any]
