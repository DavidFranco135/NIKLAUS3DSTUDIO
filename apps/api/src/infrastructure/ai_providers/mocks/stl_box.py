_FACES: tuple[tuple[tuple[int, int, int], tuple[int, int, int, int]], ...] = (
    ((0, 0, -1), (0, 1, 2, 3)),
    ((0, 0, 1), (4, 7, 6, 5)),
    ((0, -1, 0), (0, 4, 5, 1)),
    ((0, 1, 0), (3, 2, 6, 7)),
    ((-1, 0, 0), (0, 3, 7, 4)),
    ((1, 0, 0), (1, 5, 6, 2)),
)


def generate_box_stl(
    width_mm: float, height_mm: float, thickness_mm: float, *, name: str = "box"
) -> bytes:
    """Builds a minimal, valid ASCII STL for a rectangular box.

    Placeholder geometry for the Fase 4 mock CAD provider — proves the
    orchestrator's pipeline end to end without depending on OpenSCAD (that
    real integration is Fase 7).
    """
    x, y, z = width_mm, height_mm, thickness_mm
    vertices = [
        (0, 0, 0),
        (x, 0, 0),
        (x, y, 0),
        (0, y, 0),
        (0, 0, z),
        (x, 0, z),
        (x, y, z),
        (0, y, z),
    ]

    lines = [f"solid {name}"]
    for normal, (a, b, c, d) in _FACES:
        # (a, c, b) / (a, d, c), not the more "obvious" (a, b, c) / (a, c, d):
        # the latter winds every face inward, giving a mesh that's watertight
        # and internally consistent but uniformly inside-out (negative signed
        # volume) — found via Fase 8's real mesh validation, not by eye.
        for triangle in ((a, c, b), (a, d, c)):
            lines.append(f"facet normal {normal[0]} {normal[1]} {normal[2]}")
            lines.append("outer loop")
            for idx in triangle:
                vx, vy, vz = vertices[idx]
                lines.append(f"vertex {vx} {vy} {vz}")
            lines.append("endloop")
            lines.append("endfacet")
    lines.append(f"endsolid {name}")
    return ("\n".join(lines) + "\n").encode("ascii")
