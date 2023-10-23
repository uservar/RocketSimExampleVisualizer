from rocketsimvisualizer import KeyboardController, GenericController, GL2DTextItem
from rocketsimvisualizer.arena_mesh import get_arena_mesh
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
import platform

from time import sleep

if platform.system() == "Windows":
    python_version_minor = int(platform.python_version_tuple()[1])
    if python_version_minor < 11:
        import sleep_until

        def sleep(dt):
            sleep_until.sleep_until(time.time() + dt)

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
    def __init__(self, arena,
                 meshes_path="collision_meshes",
                 fps=60,
                 step_arena=False,
                 tick_skip: int = None,
                 enable_debug_text=True,
                 overwrite_controls=False,
                 config_dict: dict = None,
                 controller_class: GenericController = None,
                 **kwargs):

        self.app = pg.mkQApp()
        self.w = gl.GLViewWidget()
        self.w.setWindowTitle("pyqtgraph visualizer")
        self.w.setGeometry(0, 50, 1280, 720)

        self.arena = arena
        self.meshes_path = meshes_path
        self.fps = fps
        self.tick_skip = round(tick_skip)
        self.step_arena = step_arena
        self.enable_debug_text = enable_debug_text
        self.overwrite_controls = overwrite_controls
        self.config_dict = config_dict

        self.car_id = None  # id of the car we control/spectate
        self.target_id = 0  # item to track with target cam, 0 for ball otherwise a car id
        self.manual_swivel = False  # used when moving the camera manually
        self.target_cam = True  # general form of ball cam that can track other cars too
        self.free_cam = False  # don't use player cam

        if tick_skip is None:
            self.tick_skip = round(self.arena.tick_rate / fps)

        if self.config_dict is None:
            print("Using default configs")
            self.config_dict = default_config_dict

        self.cam_dict = self.config_dict["CAMERA"]
        self.input_dict = self.config_dict["INPUT"]

        if controller_class is None:
            controller_class = KeyboardController

        self.controller = controller_class(self.input_dict)

        GenericController.switch_car = lambda *args: self.switch_car()
        GenericController.switch_target = lambda *args: self.switch_target()
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
        self.addItem(self.text_item)

        grid_x_subdivs = 4
        grid_y_subdivs = 5
        grid_z_subdivs = 2

        if self.arena.game_mode != rs.GameMode.THE_VOID:
            if self.arena.game_mode == rs.GameMode.HOOPS:
                field_type = "hoops"
                FIELD_EXTENT_X = HOOPS_EXTENT_X
                FIELD_EXTENT_Y = HOOPS_EXTENT_Y
                FIELD_EXTENT_Z = HOOPS_EXTENT_Z
            else:
                field_type = "soccar"
                FIELD_EXTENT_X = SOCCAR_EXTENT_X
                FIELD_EXTENT_Y = SOCCAR_EXTENT_Y
                FIELD_EXTENT_Z = SOCCAR_EXTENT_Z

            # ground grids
            grid_item = gl.GLGridItem()
            grid_item.setSize(FIELD_EXTENT_X * 2, FIELD_EXTENT_Y * 2, 1)
            grid_item.setSpacing(FIELD_EXTENT_X / grid_x_subdivs, FIELD_EXTENT_Y / grid_y_subdivs, 1)
            self.addItem(grid_item)

            # ceiling grid
            grid_item = gl.GLGridItem()
            grid_item.setSize(FIELD_EXTENT_X * 2, FIELD_EXTENT_Y * 2, 1)
            grid_item.setSpacing(FIELD_EXTENT_X / grid_x_subdivs, FIELD_EXTENT_Y / grid_y_subdivs, 1)
            grid_item.translate(0, 0, FIELD_EXTENT_Z)
            self.addItem(grid_item)

            # side wall grids
            for sign in (1, -1):
                grid_item = gl.GLGridItem()
                grid_item.setSize(FIELD_EXTENT_Z, FIELD_EXTENT_Y * 2, 1)
                grid_item.setSpacing(FIELD_EXTENT_Z / grid_z_subdivs, FIELD_EXTENT_Y / grid_y_subdivs, 1)
                grid_item.rotate(90, 0, 1, 0)
                grid_item.translate(sign * FIELD_EXTENT_X, 0, FIELD_EXTENT_Z / 2)
                self.addItem(grid_item)

            # Create soccar_field
            mi_kwargs = {"smooth": False, "drawFaces": True, "drawEdges": True,
                         "edgeColor": (0.125, 0.125, 0.125, 1),
                         "shader": cShader,
                         "glOptions": {GL_DEPTH_TEST: False, GL_BLEND: True, GL_CULL_FACE: True,
                                       'glBlendFunc': (GL_SRC_ALPHA, GL_ONE)}}

            soccar_field_v, soccar_field_f = get_arena_mesh(self.meshes_path, field_type)
            soccar_field_mi = gl.GLMeshItem(vertexes=soccar_field_v,
                                            faces=soccar_field_f, **mi_kwargs)
            self.addItem(soccar_field_mi)

        # Create ball geometry
        if self.arena.game_mode == rs.GameMode.SNOWDAY:
            ball_radius = PUCK_RADIUS
            ball_md = gl.MeshData.cylinder(rows=2, cols=16, radius=(
                PUCK_RADIUS, PUCK_RADIUS), length=PUCK_HEIGHT)
            ball_md._vertexes = np.array(ball_md._vertexes) - np.array([0, 0, PUCK_HEIGHT / 2])
            # print(ball_md._vertexes)
            # quit()
        else:
            ball_radius = self.arena.ball.get_radius()
            ball_md = gl.MeshData.sphere(rows=8, cols=16, radius=ball_radius)
        self.ball_mi = gl.GLMeshItem(meshdata=ball_md, smooth=False,
                                     drawFaces=True, drawEdges=True,
                                     color=(0.1, 0.1, 0.1, 1),
                                     edgeColor=self.white_color)
        self.addItem(self.ball_mi)

        # Create ground projection for the ball
        ball_proj_md = gl.MeshData.cylinder(rows=1, cols=16, length=0, radius=round(ball_radius))
        self.ball_proj = gl.GLMeshItem(meshdata=ball_proj_md, smooth=False, drawFaces=False,
                                       drawEdges=True, edgeColor=self.white_color)
        self.addItem(self.ball_proj)

        self.pads_mi = []
        self.init_pads()

        self.car_mi_dict = {}
        self.init_cars()

        self.fps_t0 = time.perf_counter()
        self.tick_time = time.perf_counter()
        self.tick_time_drift = 0

    def init_cars(self):

        if self.car_mi_dict:
            self.w.items = [i for i in self.w.items if i not in self.car_mi_dict.values()]
            self.car_mi_dict.clear()

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

            self.addItem(car_mi)
            self.car_mi_dict[car.id] = car_mi

            # axis item
            axis_item = gl.GLAxisItem()
            axis_item.rotate(90, 0, 0, 1)
            axis_item.scale(*(hitbox_size / 2 + hitbox_offset), local=False)
            axis_item.setDepthValue(1)
            axis_item.setGLOptions({GL_DEPTH_TEST: False})
            axis_item.setParentItem(car_mi)

            # wheels
            for wheel_pair in (car_config.front_wheels, car_config.back_wheels):
                wheel_radius = wheel_pair.wheel_radius
                wheel_md = gl.MeshData.cylinder(rows=1, cols=8, length=0,
                                                radius=round(wheel_radius))
                for sign in (1, -1):
                    wheel_mi = gl.GLMeshItem(meshdata=wheel_md, drawFaces=False, drawEdges=True,
                                             smooth=False, edgeColor=self.white_color)
                    wheel_pos = -wheel_pair.connection_point_offset.as_numpy()
                    wheel_pos[1] *= sign
                    wheel_pos[2] += wheel_radius + 4  # guesstimate of compressed suspension
                    wheel_mi.translate(*wheel_pos)
                    wheel_mi.rotate(90, 1, 0, 0, local=True)
                    wheel_mi.setParentItem(car_mi)

        if self.car_id not in self.car_mi_dict:
            self.switch_car()

        if self.target_id != 0 and self.target_id not in self.car_mi_dict:
            self.switch_target()

    def init_pads(self):

        if self.pads_mi:
            self.w.items = [i for i in self.w.items if i not in self.pads_mi]
            self.pads_mi.clear()

        big_pad_box_md = gl.MeshData(vertexes=box_verts * pad_sq_dims_big, faces=box_faces)
        small_pad_box_md = gl.MeshData(vertexes=box_verts * pad_sq_dims_small, faces=box_faces)

        for pad in self.arena.get_boost_pads():
            # pad hitbox
            pad_box_md = big_pad_box_md if pad.is_big else small_pad_box_md
            pad_box_edge_color = self.white_color if pad.is_big else self.white_color / 2
            pad_box_mi = gl.GLMeshItem(meshdata=pad_box_md, drawFaces=False, drawEdges=True,
                                       edgeColor=pad_box_edge_color)
            pad_pos = pad.get_pos()
            pad_box_mi.translate(-pad_pos.x, pad_pos.y, pad_pos.z)
            self.pads_mi.append(pad_box_mi)
            self.addItem(pad_box_mi)

    def get_cam_targets(self):
        targets = {0: self.ball_mi}
        if not self.car_mi_dict:
            return targets
        targets = {**targets, **self.car_mi_dict}
        targets.pop(self.car_id)
        return targets

    def get_cam_target(self):
        targets = self.get_cam_targets()
        return targets[self.target_id]

    def switch_target(self):
        targets = self.get_cam_targets()
        sorted_target_ids = sorted(targets)
        if self.target_id in sorted_target_ids:
            target_index = sorted_target_ids.index(self.target_id)
            target_index = (target_index + 1) % len(sorted_target_ids)
            self.target_id = sorted_target_ids[target_index]
        elif self.target_id == 0:
            self.target_id = sorted_target_ids[0]
        else:
            self.target_id = 0

    def switch_car(self):
        if self.overwrite_controls and self.car_id:
            # reset car controls before switching cars
            car = self.arena.get_car_from_id(self.car_id, None)
            if car:
                car.set_controls(rs.CarControls())

        if self.car_mi_dict:
            sorted_car_mi_ids = sorted(self.car_mi_dict)
            if self.car_id in sorted_car_mi_ids:
                car_index = sorted_car_mi_ids.index(self.car_id)
                car_index = (car_index + 1) % len(sorted_car_mi_ids)
                self.car_id = sorted_car_mi_ids[car_index]
            elif len(sorted_car_mi_ids) > 0:
                self.car_id = sorted_car_mi_ids[0]
            else:
                self.car_id = None

        if self.car_id == self.target_id:
            self.switch_target()

    def toggle_target_cam(self):
        self.target_cam = not self.target_cam

    def toggle_free_cam(self):
        self.free_cam = not self.free_cam

    def addItem(self, item):
        self.w.items.append(item)

        if self.w.isValid():
            item.initialize()

        item._setView(self.w)
        item.update = lambda *args: None

    def mousePressEvent(self, ev):
        lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
        self.w.mousePos = lpos
        self.manual_swivel = True

    def mouseReleaseEvent(self, ev):
        self.manual_swivel = False

    def update_boost_pad_data(self):
        pads = self.arena.get_boost_pads()

        if len(pads) != len(self.pads_mi):
            self.init_pads()

        for i, pad in enumerate(pads):
            pad_state = pad.get_state()
            if i < len(self.pads_mi):
                self.pads_mi[i].show() if pad_state.is_active else self.pads_mi[i].hide()

    def update_ball_data(self):

        # plot ball data
        ball_state = self.arena.ball.get_state()
        ball_angles = ball_state.rot_mat.as_angle()

        self.ball_mi.resetTransform()

        # location
        self.ball_mi.translate(-ball_state.pos.x, ball_state.pos.y, ball_state.pos.z)

        # rotation
        self.ball_mi.rotate(ball_angles.yaw / math.pi * 180, 0, 0, -1, local=True)
        self.ball_mi.rotate(ball_angles.pitch / math.pi * 180, 0, 1, 0, local=True)
        self.ball_mi.rotate(ball_angles.roll / math.pi * 180, -1, 0, 0, local=True)

        # ball ground projection
        self.ball_proj.resetTransform()
        self.ball_proj.translate(-ball_state.pos.x, ball_state.pos.y, 0)

    def update_cars_data(self):

        cars = self.arena.get_cars()

        if set([car.id for car in cars]) != set(self.car_mi_dict.keys()):
            self.init_cars()

        for car in cars:
            if car.id not in self.car_mi_dict:
                continue

            car_state = car.get_state()
            car_angles = car_state.rot_mat.as_angle()

            self.car_mi_dict[car.id].resetTransform()

            # location
            self.car_mi_dict[car.id].translate(-car_state.pos.x, car_state.pos.y, car_state.pos.z)

            # rotation
            self.car_mi_dict[car.id].rotate(car_angles.yaw / math.pi * 180, 0, 0, -1, local=True)
            self.car_mi_dict[car.id].rotate(car_angles.pitch / math.pi * 180, 0, 1, 0, local=True)
            self.car_mi_dict[car.id].rotate(car_angles.roll / math.pi * 180, -1, 0, 0, local=True)

            # visual indicator for going supersonic
            edge_color = self.black_color if car_state.is_supersonic else self.white_color
            self.car_mi_dict[car.id].opts["edgeColor"] = edge_color

            car_color = self.blue_color if car.team == rs.Team.BLUE else self.orange_color
            hitbox_colors = box_colors * car_color
            self.car_mi_dict[car.id].opts["meshdata"].setFaceColors(hitbox_colors)

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
            self.w.opts["azimuth"] = -target_azimuth / math.pi * 180
            self.w.opts["elevation"] = self.cam_dict["ANGLE"] - smaller_target_elevation / math.pi * 180

        if self.car_mi_dict:

            car = self.arena.get_car_from_id(self.car_id, None)
            if car:
                car_state = car.get_state()
                # center camera around the car
                self.w.opts["center"] = pg.Vector(-car_state.pos.x, car_state.pos.y,
                                                  car_state.pos.z + self.cam_dict["HEIGHT"])

                if not self.target_cam and not self.manual_swivel:
                    # non-target_cam cam
                    car_vel_2d_norm = math.sqrt(car_state.vel.y ** 2 + car_state.vel.x ** 2)
                    if car_vel_2d_norm > 50:  # don't be sensitive to near 0 vel dir changes
                        car_vel_azimuth = math.atan2(car_state.vel.y, car_state.vel.x)
                        self.w.opts["azimuth"] = -car_vel_azimuth / math.pi * 180
                        self.w.opts["elevation"] = self.cam_dict["ANGLE"]

    def update_text_data(self):
        text = ""

        # fps
        fps = 0
        fps_t0 = time.perf_counter()
        if fps_t0 != self.fps_t0:
            fps = 1 / (fps_t0 - self.fps_t0)
        self.fps_t0 = fps_t0
        text += f"fps = {fps:.0f}\n"
        text += f"tick_time_drift = {self.tick_time_drift * 1000:.3f} ms\n"

        ball_state = self.arena.ball.get_state()
        var_names = ["ball_state"]

        # car info
        if self.car_mi_dict:
            car = self.arena.get_car_from_id(self.car_id, None)
            car_state = car.get_state()
            last_controls = car_state.last_controls
            var_names += ["car_state", "last_controls"]

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

    def update_plot_data(self):
        self.update_boost_pad_data()
        self.update_ball_data()
        self.update_cars_data()
        self.update_camera_data()
        if self.enable_debug_text:
            self.update_text_data()
        self.w.update()

    def update_controls(self):
        controls = self.controller.get_controls()
        controls.clamp_fix()
        car = self.arena.get_car_from_id(self.car_id, None)
        if car:
            car.set_controls(controls)

    def update(self):
        # only set car controls if overwrite_controls is true and there's at least one car
        if self.overwrite_controls and self.car_mi_dict:
            self.update_controls()

        # only call arena.step() if running in standalone mode
        if self.step_arena:
            self.arena.step(self.tick_skip)

        self.update_plot_data()

    def tick(self):
        while True:
            wait_t0 = time.perf_counter()
            tick_time_dt = wait_t0 - self.tick_time
            desired_dt = 1 / self.fps - tick_time_dt - self.tick_time_drift
            if desired_dt < 1e-7:
                break
            elif desired_dt > 5e-4:  # sleep_unfil is innacurate below this threshold on windows
                sleep(desired_dt - 5e-4)
        tick_time = time.perf_counter()
        self.tick_time_drift += tick_time - self.tick_time - 1 / self.fps
        self.tick_time_drift = max(min(self.tick_time_drift, 1 / self.fps), - 1 / self.fps)
        self.tick_time = tick_time
        self.update()

    def start(self):
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
        self.visualizer.start()
