from rocketsimvisualizer.constants import *
import numpy as np

soccar_corner_vertices = np.fromfile("assets/soccar_field/soccar_corner_vertices.bin", "<3f") * 100
soccar_corner_ids = np.fromfile("assets/soccar_field/soccar_corner_ids.bin", "<3i")

soccar_goal_vertices = np.fromfile("assets/soccar_field/soccar_goal_vertices.bin", "<3f") * 100
soccar_goal_ids = np.fromfile("assets/soccar_field/soccar_goal_ids.bin", "<3i")

soccar_ramps_0_vertices = np.fromfile("assets/soccar_field/soccar_ramps_0_vertices.bin", "<3f") * 100
soccar_ramps_0_ids = np.fromfile("assets/soccar_field/soccar_ramps_0_ids.bin", "<3i")

soccar_ramps_1_vertices = np.fromfile("assets/soccar_field/soccar_ramps_1_vertices.bin", "<3f") * 100
soccar_ramps_1_ids = np.fromfile("assets/soccar_field/soccar_ramps_1_ids.bin", "<3i")

corners_v = [soccar_corner_vertices]
corners_v.append(soccar_corner_vertices * [-1, 1, 1])
corners_v.append(soccar_corner_vertices * [1, -1, 1])
corners_v.append(soccar_corner_vertices * [-1, -1, 1])
corners_v = np.concatenate(corners_v)

corners_f = [soccar_corner_ids]
corners_f.append(soccar_corner_ids + len(soccar_corner_vertices))
corners_f.append(soccar_corner_ids + len(soccar_corner_vertices) * 2)
corners_f.append(soccar_corner_ids + len(soccar_corner_vertices) * 3)
corners_f = np.concatenate(corners_f)

goals_v = np.concatenate([soccar_goal_vertices + [0, -EXTENT_Y, 0],
                          soccar_goal_vertices * [1, -1, 1] + [0, EXTENT_Y, 0]])
goals_f = np.concatenate([soccar_goal_ids, soccar_goal_ids + len(soccar_goal_vertices)])

ramps_0_v = np.concatenate([soccar_ramps_0_vertices, soccar_ramps_0_vertices * [-1, 1, 1]])
ramps_0_f = np.concatenate([soccar_ramps_0_ids, soccar_ramps_0_ids + len(soccar_ramps_0_vertices)])

ramps_1_v = np.concatenate([soccar_ramps_1_vertices, soccar_ramps_1_vertices * [-1, 1, 1]])
ramps_1_f = np.concatenate([soccar_ramps_1_ids, soccar_ramps_1_ids + len(soccar_ramps_1_vertices)])

soccar_field_v = np.concatenate([corners_v, goals_v, ramps_0_v, ramps_1_v])

soccar_field_f = [corners_f,
                  goals_f + len(corners_v),
                  ramps_0_f + len(corners_v) + len(goals_v),
                  ramps_1_f + len(corners_v) + len(goals_v) + len(ramps_0_v)]
soccar_field_f = np.concatenate(soccar_field_f)
