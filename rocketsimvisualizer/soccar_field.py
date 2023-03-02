from pathlib import Path
import numpy as np


soccar_field_v = []
soccar_field_f = []

for file_path in Path("collision_meshes/soccar").glob("*.cmf"):
    with open(file_path, "rb") as file:
        num_tris, num_verts = np.fromfile(file, "i", count=2)
        tris = np.fromfile(file, "3i", count=num_tris)
        verts = np.fromfile(file, "3f", count=num_verts) * 50

        soccar_field_f += list(tris + len(soccar_field_v))
        soccar_field_v += list(verts)
