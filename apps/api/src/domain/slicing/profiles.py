from dataclasses import dataclass


@dataclass(frozen=True)
class PrinterProfile:
    """Minimal machine constraints a slicer needs to build its config —

    not the full `Printer` business entity (that's a DB-backed model from
    a later phase, Estoque/Impressoras). Just the pure value object a
    `SlicerProvider.slice()` call takes as input.
    """

    name: str
    bed_size_mm: tuple[float, float, float]
    nozzle_diameter_mm: float
    max_height_mm: float


@dataclass(frozen=True)
class MaterialProfile:
    name: str
    filament_diameter_mm: float
    density_g_cm3: float
    cost_per_kg: float
