import io

import trimesh

_TRIMESH_FILE_TYPE_BY_KIND = {
    "model_stl": "stl",
    "model_obj": "obj",
}


def load_mesh(file_bytes: bytes, kind: str) -> trimesh.Trimesh:
    file_type = _TRIMESH_FILE_TYPE_BY_KIND.get(kind)
    if file_type is None:
        raise ValueError(f"Unsupported mesh kind for loading: {kind}")
    loaded = trimesh.load(io.BytesIO(file_bytes), file_type=file_type)
    if isinstance(loaded, trimesh.Scene):
        loaded = trimesh.util.concatenate(loaded.dump())
    return loaded


def export_mesh(mesh: trimesh.Trimesh, kind: str) -> bytes:
    file_type = _TRIMESH_FILE_TYPE_BY_KIND.get(kind)
    if file_type is None:
        raise ValueError(f"Unsupported mesh kind for export: {kind}")
    return mesh.export(file_type=file_type)


def is_watertight(mesh: trimesh.Trimesh) -> bool:
    return bool(mesh.is_watertight)


def is_manifold(mesh: trimesh.Trimesh) -> bool:
    """trimesh has no single "is 2-manifold" flag; watertight (every edge

    shared by exactly two faces) plus consistent winding is the practical
    proxy this codebase uses for it.
    """
    return bool(mesh.is_watertight and mesh.is_winding_consistent)


def count_components(mesh: trimesh.Trimesh) -> int:
    return len(mesh.split(only_watertight=False))


def remove_degenerate_faces(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh.update_faces(mesh.nondegenerate_faces())
    return mesh


def fill_holes(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    trimesh.repair.fill_holes(mesh)
    return mesh


def fix_normals(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh.fix_normals()
    return mesh


def keep_largest_component(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    components = mesh.split(only_watertight=False)
    if len(components) <= 1:
        return mesh
    return max(components, key=lambda part: part.volume)


def simplify(mesh: trimesh.Trimesh, *, target_ratio: float) -> trimesh.Trimesh:
    target_faces = max(4, int(len(mesh.faces) * target_ratio))
    return mesh.simplify_quadric_decimation(face_count=target_faces)


def subdivide(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    return mesh.subdivide()


def smooth(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.smoothing.filter_laplacian(mesh.copy())


def compute_volume_mm3(mesh: trimesh.Trimesh) -> float:
    return float(mesh.volume)


def compute_area_mm2(mesh: trimesh.Trimesh) -> float:
    return float(mesh.area)


def scale(mesh: trimesh.Trimesh, *, factor: float) -> trimesh.Trimesh:
    mesh.apply_scale(factor)
    return mesh


def center(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh.apply_translation(-mesh.centroid)
    return mesh
