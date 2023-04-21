from pathlib import Path
import numpy as np


def get_arena_mesh(meshes_path="collision_meshes", subfolder="soccar"):
    soccar_field_v = []
    soccar_field_f = []

    resolved_path = Path(meshes_path).resolve()

    for file_path in (resolved_path / subfolder).glob("*.cmf"):
        with open(file_path, "rb") as file:
            num_tris, num_verts = np.fromfile(file, "i", count=2)
            tris = np.fromfile(file, "3i", count=num_tris)
            verts = np.fromfile(file, "3f", count=num_verts) * 50

            soccar_field_f += list(tris + len(soccar_field_v))
            soccar_field_v += list(verts)

    return soccar_field_v, soccar_field_f
