import numpy as np
import trimesh

MAX_RAY_SAMPLES = 300
_RAY_OFFSET_MM = 1e-3


def analyze_min_wall_thickness(
    mesh: trimesh.Trimesh, *, max_samples: int = MAX_RAY_SAMPLES
) -> float | None:
    """Casts a ray inward from a sample of face centroids and measures the

    distance to the first opposite surface — an approximation of local wall
    thickness (real slicers use denser/smarter sampling; this is a bounded,
    representative sample, not exhaustive). Returns None if no ray hit
    anything (shouldn't happen for a watertight mesh, but a mesh this module
    receives may not always be one).
    """
    total_faces = len(mesh.faces)
    if total_faces == 0:
        return None

    face_centers = mesh.triangles_center
    face_normals = mesh.face_normals

    if total_faces > max_samples:
        rng = np.random.default_rng(seed=0)
        sample_idx = rng.choice(total_faces, max_samples, replace=False)
    else:
        sample_idx = np.arange(total_faces)

    origins = face_centers[sample_idx] - face_normals[sample_idx] * _RAY_OFFSET_MM
    directions = -face_normals[sample_idx]

    locations, index_ray, _index_tri = mesh.ray.intersects_location(origins, directions)
    if len(locations) == 0:
        return None

    min_thickness = None
    for location, ray_index in zip(locations, index_ray, strict=True):
        distance = float(np.linalg.norm(location - origins[ray_index]))
        if min_thickness is None or distance < min_thickness:
            min_thickness = distance
    return min_thickness
