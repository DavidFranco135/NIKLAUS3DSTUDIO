from dataclasses import dataclass


@dataclass(frozen=True)
class QuoteInputs:
    """Per-piece numbers the profile's policy factors don't carry —

    material price and machine depreciation are properties of a specific
    material/printer, not of a cost profile, so they're supplied here.
    Today these come from the user (no real slicer/printer catalog is wired
    up yet — Fase 10 is stub-only); once the Slicer Engine and a printer
    catalog exist, an application-layer use case can populate this same
    dataclass automatically instead of taking it from a request body — the
    calculator itself doesn't change.
    """

    material_cost: float
    print_time_hours: float
    machine_cost_per_hour: float
    energy_kwh: float
    labor_hours: float
