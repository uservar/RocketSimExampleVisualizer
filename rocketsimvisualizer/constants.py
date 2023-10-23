import numpy as np

# standard soccar field
SOCCAR_EXTENT_X = 4096
SOCCAR_EXTENT_Y = 5120
SOCCAR_EXTENT_Z = 2048

# standard hoops field
HOOPS_EXTENT_X = 8900 / 3.0
HOOPS_EXTENT_Y = 3581
HOOPS_EXTENT_Z = 1820

# Snowday puck
PUCK_RADIUS = 114.25
PUCK_HEIGHT = 62.5

# boost pad cylinder
PAD_CYL_HEIGHT = 95
pad_CYL_RAD_BIG = 208
PAD_CYL_RAD_SMALL = 144

# boost pad box dimensions
PAD_SQ_HEIGHT = 64
PAD_SQ_RAD_BIG = 160
PAD_SQ_RAD_SMALL = 120

# multiplied by 2 because btBoxShape is initialized with half extents
pad_sq_dims_big = np.array([PAD_SQ_RAD_BIG, PAD_SQ_RAD_BIG, PAD_SQ_HEIGHT]) * 2
pad_sq_dims_small = np.array([PAD_SQ_RAD_SMALL, PAD_SQ_RAD_SMALL, PAD_SQ_HEIGHT]) * 2

# box mesh data
box_verts = np.array([
    [-0.5, -0.5, -0.5],
    [0.5, -0.5, -0.5],
    [0.5, 0.5, -0.5],
    [-0.5, 0.5, -0.5],
    [-0.5, -0.5, 0.5],
    [0.5, -0.5, 0.5],
    [0.5, 0.5, 0.5],
    [-0.5, 0.5, 0.5]])

box_faces = np.array([
    [0, 1, 2],
    [0, 2, 3],
    [0, 1, 4],
    [1, 5, 4],
    [1, 2, 5],
    [2, 5, 6],
    [2, 3, 6],
    [3, 6, 7],
    [0, 3, 7],
    [0, 4, 7],
    [4, 5, 7],
    [5, 6, 7]])

box_colors = np.array([
    [.2, .2, .2, 1],
    [.2, .2, .2, 1],
    [.6, .6, .6, 1],
    [.6, .6, .6, 1],
    [.4, .4, .4, 1],
    [.4, .4, .4, 1],
    [.6, .6, .6, 1],
    [.6, .6, .6, 1],
    [1.4, 1.4, 1.4, 1],
    [1.4, 1.4, 1.4, 1],
    [1, 1, 1, 1],
    [1, 1, 1, 1],
])


# set all np arrays above to read-only
for var_name in dir():
    var = locals()[var_name]
    if isinstance(var, np.ndarray):
        var.flags.writeable = False
