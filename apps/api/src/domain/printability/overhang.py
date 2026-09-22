import numpy as np
import trimesh

DEFAULT_OVERHANG_THRESHOLD_DEG = 45.0
BED_CONTACT_EPSILON_MM = 0.05


def analyze_overhangs(
    mesh: trimesh.Trimesh, *, threshold_deg: float = DEFAULT_OVERHANG_THRESHOLD_DEG
) -> tuple[float, float]:
    """Estimates unsupported overhang by face angle — not a certified slicer

    analysis, a heuristic: for each downward-facing triangle (excluding the
    ones resting on the build plate, which need no support), the angle from
    a vertical wall is `90° - threshold_deg` at most before it's flagged.
    A flat downward ceiling scores 90° (worst); a vertical wall scores 0°.

    Returns (overhang_area_ratio, max_overhang_angle_from_vertical_deg).
    """
    normals = mesh.face_normals
    areas = mesh.area_faces
    nz = normals[:, 2]

    min_z = mesh.vertices[:, 2].min()
    face_min_z = mesh.vertices[mesh.faces][:, :, 2].min(axis=1)
    resting_on_bed = face_min_z <= (min_z + BED_CONTACT_EPSILON_MM)

    downward = (nz < -1e-6) & (~resting_on_bed)
    if not downward.any():
        return 0.0, 0.0

    angle_from_vertical = np.degrees(np.arcsin(np.clip(-nz[downward], -1.0, 1.0)))
    is_overhang = angle_from_vertical > (90.0 - threshold_deg)

    total_area = float(areas.sum())
    overhang_area = float(areas[downward][is_overhang].sum()) if is_overhang.any() else 0.0
    max_angle = float(angle_from_vertical.max())

    return (overhang_area / total_area if total_area else 0.0), max_angle
