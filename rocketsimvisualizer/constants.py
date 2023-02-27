import numpy as np

# boost pad cylinder
pad_cyl_height = 95
pad_cyl_rad_big = 208
pad_cyl_rad_small = 144

# boost pad box dimensions
# multiplied by 2 because btBoxShape is initialized with half extents
pad_sq_dims_big = np.array([160, 160, 64]) * 2
pad_sq_dims_small = np.array([120, 120, 64]) * 2

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
