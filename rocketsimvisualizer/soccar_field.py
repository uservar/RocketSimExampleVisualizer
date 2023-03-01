import numpy as np


soccar_corner_vertices = np.fromfile("assets/soccar_field/soccar_corner_vertices.bin", "<3f") * 100
soccar_corner_ids = np.fromfile("assets/soccar_field/soccar_corner_ids.bin", "<3i")

soccar_goal_vertices = np.fromfile("assets/soccar_field/soccar_goal_vertices.bin", "<3f") * 100
soccar_goal_ids = np.fromfile("assets/soccar_field/soccar_goal_ids.bin", "<3i")

soccar_ramps_0_vertices = np.fromfile("assets/soccar_field/soccar_ramps_0_vertices.bin", "<3f") * 100
soccar_ramps_0_ids = np.fromfile("assets/soccar_field/soccar_ramps_0_ids.bin", "<3i")

soccar_ramps_1_vertices = np.fromfile("assets/soccar_field/soccar_ramps_1_vertices.bin", "<3f") * 100
soccar_ramps_1_ids = np.fromfile("assets/soccar_field/soccar_ramps_1_ids.bin", "<3i")
