from rocketsimvisualizer import KeyboardController, GenericController, GL2DTextItem
from rocketsimvisualizer.soccar_field import soccar_field_v, soccar_field_f
from rocketsimvisualizer.constants import *

from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.opengl.shaders import ShaderProgram, VertexShader, FragmentShader
from OpenGL.GL import *

import pyqtgraph as pg
import pyqtgraph.opengl as gl

import RocketSim as rs

import numpy as np

import threading
import time
import math

import pathlib
import tomli

current_dir = pathlib.Path(__file__).parent

with open(current_dir / "rsvconfig-default.toml", "rb") as file:
    default_config_dict = tomli.load(file)

# disable vsync
_format = QtGui.QSurfaceFormat()
_format.setSwapInterval(0)
QtGui.QSurfaceFormat.setDefaultFormat(_format)

cShader = ShaderProgram('cShader', [
    VertexShader("""
        varying vec3 normal;
        varying vec4 pos;

        void main() {
            normal = normalize(gl_Normal);
            gl_FrontColor = gl_Color;
            gl_BackColor = gl_Color;
            gl_Position = ftransform();
            pos = gl_Vertex;
        }
    """),
    FragmentShader("""
        varying vec3 normal;
        varying vec4 pos;

        void main() {
            vec3 blue = vec3(0.0, 0.4, 0.8);
            vec3 orange = vec3(1.0, 0.2, 0.1);
            float xyNorm_2 = pow(normal.x, 2.0) + pow(normal.y, 2.0);
            vec3 normPos = vec3(pos[0] / 4096.0, pos[1] / 6000.0, pos[2] / 2048.0);
            vec3 color = max(normPos.y, 0.0) * orange - min(normPos.y, 0.0) * blue;
            color = 0.25 * xyNorm_2 * color;
            gl_FragColor = vec4(color, 1.0);
        }
    """)
])


class Visualizer:
    def __init__(self, arena, fps=60,
                 tick_rate=120, tick_skip=2,
                 step_arena=False,
                 enable_debug_text=True,
                 overwrite_controls=False,
                 config_dict: dict = None,
                 controller_class: GenericController = None):

        self.app = pg.mkQApp()
        self.w = gl.GLViewWidget()
        self.w.setWindowTitle("pyqtgraph visualizer")
        self.w.setGeometry(0, 50, 1280, 720)
        self.w.show()

        self.arena = arena
        self.fps = fps
        self.tick_rate = tick_rate
        self.tick_skip = tick_skip
        self.step_arena = step_arena
        self.enable_debug_text = enable_debug_text
        self.overwrite_controls = overwrite_controls
        self.config_dict = config_dict

        self.car_index = 0  # index of the car we control/spectate
        self.target_index = -1  # item to track with target cam
        self.manual_swivel = False  # wether or not to allow manual camera swivel
        self.target_cam = True  # general form of ball cam
        self.free_cam = False  # don't use player cam

        if self.config_dict is None:
            print("Using default configs")
            self.config_dict = default_config_dict

        self.cam_dict = self.config_dict["CAMERA"]
        self.input_dict = self.config_dict["INPUT"]

        if controller_class is None:
            controller_class = KeyboardController

        self.controller = controller_class(self.input_dict)

        GenericController.switch_car = lambda *args: self.switch_car()
        GenericController.cycle_targets = lambda *args: self.cycle_targets()
        GenericController.toggle_target_cam = lambda *args: self.toggle_target_cam()
        GenericController.toggle_free_cam = lambda *args: self.toggle_free_cam()

        self.app.focusChanged.connect(self.controller.reset_controls)

        self.w.mousePressEvent = self.mousePressEvent
        self.w.mouseReleaseEvent = self.mouseReleaseEvent

        self.white_color = np.array((1, 1, 1, 1))
        self.black_color = np.array((0, 0, 0, 1))

        self.blue_color = np.array([0, 0.4, 0.8, 1])
        self.orange_color = np.array([1, 0.2, 0.1, 1])

        # initial camera settings
        self.w.opts["fov"] = self.cam_dict["FOV"]
        self.w.opts["distance"] = self.cam_dict["DISTANCE"]
        self.w.show()

        # text info
        self.text_item = GL2DTextItem(font_size=11)
        self.text_item.setDepthValue(2)
        self.w.addItem(self.text_item)

        # Add surface grids
        grid_spacing = 512

        if self.arena.game_mode == rs.GameMode.SOCCAR:
            # ground grids
            grid_item = gl.GLGridItem()
            grid_item.setSize(SOCCAR_EXTENT_X * 2, SOCCAR_EXTENT_Y * 2, 1)
            grid_item.setSpacing(grid_spacing, grid_spacing, 1)
            self.w.addItem(grid_item)

            # ceiling grid
            grid_item = gl.GLGridItem()
            grid_item.setSize(SOCCAR_EXTENT_X * 2, SOCCAR_EXTENT_Y * 2, 1)
            grid_item.setSpacing(grid_spacing, grid_spacing, 1)
            grid_item.translate(0, 0, SOCCAR_EXTENT_Z)
            self.w.addItem(grid_item)

            # side wall grids
            for sign in (1, -1):
                grid_item = gl.GLGridItem()
                grid_item.setSize(SOCCAR_EXTENT_Z, SOCCAR_EXTENT_Y * 2, 1)
                grid_item.setSpacing(grid_spacing, grid_spacing, 1)
                grid_item.rotate(90, 0, 1, 0)
                grid_item.translate(sign * SOCCAR_EXTENT_X, 0, SOCCAR_EXTENT_Z / 2)
                self.w.addItem(grid_item)

            # Create soccar_field
            mi_kwargs = {"smooth": False, "drawFaces": True, "drawEdges": True,
                         "edgeColor": (0.125, 0.125, 0.125, 1),
                         "shader": cShader,
                         "glOptions": {GL_DEPTH_TEST: False, GL_BLEND: True, GL_CULL_FACE: True,
                                       'glBlendFunc': (GL_SRC_ALPHA, GL_ONE)}}

            soccar_field_mi = gl.GLMeshItem(vertexes=soccar_field_v,
                                            faces=soccar_field_f, **mi_kwargs)
            self.w.addItem(soccar_field_mi)

        # Create ball geometry
        ball_radius = self.arena.ball.get_radius()
        ball_md = gl.MeshData.sphere(rows=8, cols=16, radius=ball_radius)
        self.ball_mi = gl.GLMeshItem(meshdata=ball_md, smooth=False,
                                     drawFaces=True, drawEdges=True,
                                     color=(0.1, 0.1, 0.1, 1),
                                     edgeColor=self.white_color)
        self.w.addItem(self.ball_mi)

        # Create ground projection for the ball
        ball_proj_md = gl.MeshData.cylinder(rows=1, cols=16, length=0, radius=round(ball_radius))
        self.ball_proj = gl.GLMeshItem(meshdata=ball_proj_md, smooth=False, drawFaces=False,
                                       drawEdges=True, edgeColor=self.white_color)
        self.w.addItem(self.ball_proj)

        self.pads_mi = []
        for pad in arena.get_boost_pads():
            # pad hitbox
            pad_sq_dims = pad_sq_dims_big if pad.is_big else pad_sq_dims_small
            pad_box_verts = box_verts * pad_sq_dims
            pad_box_edge_color = self.white_color if pad.is_big else self.white_color / 2
            pad_box_mi = gl.GLMeshItem(vertexes=pad_box_verts, faces=box_faces,
                                       drawFaces=False, drawEdges=True,
                                       edgeColor=pad_box_edge_color)
            pad_pos = pad.get_pos()
            pad_box_mi.translate(-pad_pos.x, pad_pos.y, pad_pos.z)
            self.pads_mi.append(pad_box_mi)
            self.w.addItem(pad_box_mi)

        self.cars_mi = []
        self.init_cars()

        self.tick_time = time.perf_counter()
        self.fps_t0 = time.perf_counter()
        self.update()

    def init_cars(self):

        if self.cars_mi:
            self.w.items = [i for i in self.w.items if i not in self.cars_mi]
            self.cars_mi.clear()

        # Create car geometry
        for car in self.arena.get_cars():

            # car hitbox as mesh
            car_config = car.get_config()
            hitbox_size = car_config.hitbox_size.as_numpy()
            hitbox_offset = car_config.hitbox_pos_offset.as_numpy()

            hitbox_verts = box_verts * hitbox_size + hitbox_offset * [-1, 1, 1]

            car_mi = gl.GLMeshItem(vertexes=hitbox_verts, faces=box_faces,
                                   smooth=False, drawFaces=True, drawEdges=True,
                                   edgeColor=self.white_color)

            self.w.addItem(car_mi)
            self.cars_mi.append(car_mi)

            # axis item
            axis_item = gl.GLAxisItem()
            axis_item.rotate(90, 0, 0, 1)
            axis_item.scale(*(hitbox_size / 2 + hitbox_offset), local=False)
            axis_item.setDepthValue(1)
            axis_item.setGLOptions({GL_DEPTH_TEST: False})
            axis_item.setParentItem(car_mi)

            # wheels
            for wheel_pair in (car_config.front_wheels, car_config.back_wheels):
                for sign in (1, -1):
                    wheel_radius = wheel_pair.wheel_radius
                    wheel_pos = -wheel_pair.connection_point_offset.as_numpy()
                    wheel_pos[1] *= sign
                    wheel_pos[2] += wheel_radius + 4  # guesstimate of compressed suspension
                    wheel_md = gl.MeshData.cylinder(rows=1, cols=8, length=0,
                                                    radius=round(wheel_radius))
                    wheel_mi = gl.GLMeshItem(meshdata=wheel_md, drawFaces=False, drawEdges=True,
                                             smooth=False, edgeColor=self.white_color)
                    wheel_mi.translate(*wheel_pos)
                    wheel_mi.rotate(90, 1, 0, 0, local=True)
                    wheel_mi.setParentItem(car_mi)

    def get_cam_targets(self):
        if not self.cars_mi:
            return [self.ball_mi]
        targets = self.cars_mi + [self.ball_mi]
        targets.pop(self.car_index)
        return targets

    def get_cam_target(self):
        targets = self.get_cam_targets()
        return targets[self.target_index]

    def cycle_targets(self):
        targets = self.get_cam_targets()
        self.target_index = (self.target_index + 1) % len(targets)

    def switch_car(self):
        cars = self.arena.get_cars()
        if self.car_index < len(cars):
            if self.overwrite_controls:
                # reset car controls before switching cars
                cars[self.car_index].set_controls(rs.CarControls())
            self.car_index = (self.car_index + 1) % len(self.cars_mi)

    def toggle_target_cam(self):
        self.target_cam = not self.target_cam

    def toggle_free_cam(self):
        self.free_cam = not self.free_cam

    def mousePressEvent(self, ev):
        lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
        self.w.mousePos = lpos
        self.manual_swivel = True

    def mouseReleaseEvent(self, ev):
        self.manual_swivel = False

    def update_boost_pad_data(self):
        for i, pad in enumerate(self.arena.get_boost_pads()):
            pad_state = pad.get_state()
            self.pads_mi[i].show() if pad_state.is_active else self.pads_mi[i].hide()

    def update_ball_data(self):

        # plot ball data
        ball_state = self.arena.ball.get_state()

        # approx ball spin
        ball_angvel_np = np.array([ball_state.ang_vel.x, -ball_state.ang_vel.y, ball_state.ang_vel.z])
        rot_angle = np.linalg.norm(ball_angvel_np)
        rot_axis = ball_angvel_np / max(1e-9, rot_angle)
        delta_rot_angle = rot_angle * self.tick_skip / self.tick_rate

        self.ball_mi.rotate(delta_rot_angle / math.pi * 180, *rot_axis, local=False)

        # location
        ball_transform = self.ball_mi.transform()
        ball_transform[0, 3] = -ball_state.pos.x
        ball_transform[1, 3] = ball_state.pos.y
        ball_transform[2, 3] = ball_state.pos.z
        self.ball_mi.setTransform(ball_transform)

        # ball ground projection
        self.ball_proj.resetTransform()
        self.ball_proj.translate(-ball_state.pos.x, ball_state.pos.y, 0)

    def update_cars_data(self):

        cars = self.arena.get_cars()

        if len(cars) != len(self.cars_mi):
            self.init_cars()

        for i, car in enumerate(cars):

            car_state = car.get_state()
            car_angles = car_state.rot_mat.as_angle()

            self.cars_mi[i].resetTransform()

            # location
            self.cars_mi[i].translate(-car_state.pos.x, car_state.pos.y, car_state.pos.z)

            # rotation
            self.cars_mi[i].rotate(car_angles.yaw / math.pi * 180, 0, 0, -1, local=True)
            self.cars_mi[i].rotate(car_angles.pitch / math.pi * 180, 0, 1, 0, local=True)
            self.cars_mi[i].rotate(car_angles.roll / math.pi * 180, -1, 0, 0, local=True)

            # visual indicator for going supersonic
            self.cars_mi[i].opts["edgeColor"] = self.black_color if car_state.is_supersonic else self.white_color

            car_color = self.blue_color if car.team == rs.Team.BLUE else self.orange_color
            hitbox_colors = box_colors * car_color
            self.cars_mi[i].opts["meshdata"].setFaceColors(hitbox_colors)

    def update_camera_data(self):

        if self.free_cam:
            return

        # calculate target cam values
        if self.target_cam and not self.manual_swivel:
            cam_pos = self.w.cameraPosition()
            target_pos = self.get_cam_target().transform().matrix()[:3, 3]
            rel_target_pos = (target_pos - cam_pos) * [-1, 1, 1]
            rel_target_pos_norm = np.linalg.norm(rel_target_pos)

            target_azimuth = math.atan2(rel_target_pos[1], rel_target_pos[0])

            target_elevation = 0
            if rel_target_pos_norm != 0:
                target_elevation = math.asin(rel_target_pos[2] / rel_target_pos_norm)

            smaller_target_elevation = target_elevation * 2 / 3

            self.w.setCameraParams(azimuth=-target_azimuth / math.pi * 180,
                                   elevation=self.cam_dict["ANGLE"] - smaller_target_elevation / math.pi * 180)

        if self.cars_mi:
            car_index = self.car_index % len(self.cars_mi)
            car = self.arena.get_cars()[car_index]
            car_state = car.get_state()

            # center camera around the car
            self.w.opts["center"] = pg.Vector(-car_state.pos.x, car_state.pos.y,
                                              car_state.pos.z + self.cam_dict["HEIGHT"])

            if not self.target_cam and not self.manual_swivel:
                # non-target_cam cam
                car_vel_2d_norm = math.sqrt(car_state.vel.y ** 2 + car_state.vel.x ** 2)
                if car_vel_2d_norm > 50:  # don't be sensitive to near 0 vel dir changes
                    car_vel_azimuth = math.atan2(car_state.vel.y, car_state.vel.x)
                    self.w.setCameraParams(azimuth=-car_vel_azimuth / math.pi * 180,
                                           elevation=self.cam_dict["ANGLE"])

    def update_text_data(self):
        text = ""

        # fps
        fps = 1 / (time.perf_counter() - self.fps_t0)
        text += f"fps = {fps:.0f}\n"

        ball_state = self.arena.ball.get_state()
        var_names = ["ball_state"]

        # car info
        if self.cars_mi:
            car_index = self.car_index % len(self.cars_mi)
            car = self.arena.get_cars()[car_index]
            car_state = car.get_state()
            var_names += ["car_state"]

        for var_name in var_names:
            var = locals()[var_name]
            text += f"\n{var_name}:\n"
            for key in dir(var):
                value = getattr(var, key)
                if not key.startswith("_"):
                    if not isinstance(value, (bool, int)):
                        try:
                            text += f"{key} = {value:.2f}\n"
                        except TypeError:
                            pass
                    else:
                        text += f"{key} = {value}\n"

        self.text_item.text = text
        self.fps_t0 = time.perf_counter()

    def update_plot_data(self):
        self.update_boost_pad_data()
        self.update_ball_data()
        self.update_cars_data()
        self.update_camera_data()
        if self.enable_debug_text:
            self.update_text_data()

    def update(self):
        # only set car controls if overwrite_controls is true and there's at least one car
        if self.overwrite_controls and self.cars_mi:
            car_index = self.car_index % len(self.cars_mi)
            controls = self.controller.get_controls()
            controls.clamp_fix()
            cars = self.arena.get_cars()
            if car_index < len(cars):
                car = self.arena.get_cars()[car_index]
                car.set_controls(controls)

        # only call arena.step() if running in standalone mode
        if self.step_arena:
            self.arena.step(self.tick_skip)

        self.update_plot_data()

    def tick(self):
        while (1 / self.fps - (time.perf_counter() - self.tick_time)) > 1e-6:
            pass
        self.tick_time = time.perf_counter()
        self.update()

    def animation(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.tick)
        timer.start()
        self.app.exec()


class VisualizerThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        super(VisualizerThread, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.initialized = False
        self.visualizer: Visualizer = None

    def run(self):
        self.visualizer = Visualizer(*self.args, **self.kwargs)
        self.initialized = True
        self.visualizer.animation()
