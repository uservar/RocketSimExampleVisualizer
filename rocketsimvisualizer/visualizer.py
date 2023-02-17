from rocketsimvisualizer.models import obj
from rocketsim import Angle, Vec3
from rocketsim.sim import Arena, CarConfig, GameMode, Team, CarControls

from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
import pyqtgraph.opengl as gl

import numpy as np
import math

from collections import defaultdict
import pathlib
import tomli

current_dir = pathlib.Path(__file__).parent

with open(current_dir / "rsvconfig-default.toml", "rb") as file:
    default_config_dict = tomli.load(file)

# Get key mappings from Qt namespace
qt_keys = (
    (getattr(QtCore.Qt, attr), attr[4:])
    for attr in dir(QtCore.Qt)
    if attr.startswith("Key_")
)
keys_mapping = defaultdict(lambda: "unknown", qt_keys)


class KeyPressWindow(gl.GLViewWidget):
    sigKeyPress = QtCore.pyqtSignal(object)
    sigKeyRelease = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        self.sigKeyPress.emit(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        self.sigKeyRelease.emit(event)


class Visualizer:
    def __init__(self, arena, car_ids,
                 tick_rate=120, tick_skip=2,
                 step_arena=False, overwrite_controls=False,
                 config_dict=None):
        self.arena = arena
        self.car_ids = car_ids
        self.tick_rate = tick_rate
        self.tick_skip = tick_skip
        self.step_arena = step_arena
        self.overwrite_controls = overwrite_controls

        if config_dict is None:
            print("Using default configs")
            config_dict = default_config_dict

        self.input_dict = config_dict["INPUT"]
        self.cam_dict = config_dict["CAMERA"]

        self.app = pg.mkQApp()

        # window settings
        self.w = KeyPressWindow()
        self.w.setWindowTitle("pyqtgraph visualizer")
        self.w.setGeometry(0, 50, 1280, 720)

        # initial camera settings
        self.TARGET_CAM = True
        self.w.opts["fov"] = self.cam_dict["FOV"]
        self.w.opts["distance"] = self.cam_dict["DISTANCE"]
        self.w.show()

        # Add ground grid
        gz = gl.GLGridItem()
        gz.setSize(8192, 10240 + 880 * 2, 1)
        gz.setSpacing(100, 100, 100)
        self.w.addItem(gz)

        self.default_edge_color = (1, 1, 1, 1)

        # Create stadium 3d model
        stadium_object = obj.OBJ(current_dir / "models/field_simplified.obj")
        md = gl.MeshData(vertexes=stadium_object.vertices, faces=stadium_object.faces)
        m4 = gl.GLMeshItem(meshdata=md, smooth=False, drawFaces=False, drawEdges=True,
                           edgeColor=self.default_edge_color)
        m4.rotate(90, 0, 0, 1)
        self.w.addItem(m4)

        # Create ball geometry
        ball_md = gl.MeshData.sphere(rows=8, cols=16, radius=91.25)
        self.ball = gl.GLMeshItem(meshdata=ball_md, smooth=False, drawFaces=True, drawEdges=True,
                                  edgeColor=self.default_edge_color, color=(0.1, 0.1, 0.1, 1))
        self.w.addItem(self.ball)

        # index of the car we control/spectate
        self.car_index = 0

        # Create car geometry
        car_object = obj.OBJ(current_dir / "models/Octane_decimated.obj")
        car_md = gl.MeshData(vertexes=car_object.vertices, faces=car_object.faces)

        self.cars = []
        for i, car_id in enumerate(self.car_ids):
            team = i % 2  # workaround until we get car.team
            car_color = (0, 0.4, 0.8, 1) if team == 0 else (1, 0.2, 0.1, 1)
            car_mesh = gl.GLMeshItem(meshdata=car_md, smooth=False, drawFaces=True, drawEdges=True,
                                     color=car_color, edgeColor=self.default_edge_color)
            self.cars.append(car_mesh)
            self.w.addItem(car_mesh)
            car_debug_info = gl.GLTextItem(pos=(0, 0, 50))
            car_debug_info.setParentItem(car_mesh)

        # item to track with target cam
        self.target_index = -1

        # connect key press events to update our controls
        self.is_pressed_dict = {input_key: False for input_key in self.input_dict.values()}
        self.controls = CarControls()
        self.w.sigKeyPress.connect(self.update_controls)
        self.w.sigKeyRelease.connect(self.release_controls)
        self.app.focusChanged.connect(self.reset_controls)

        self.update()

    def get_targets(self):
        targets = self.cars + [self.ball]
        del targets[self.car_index]
        return targets

    def reset_controls(self):
        for key in self.is_pressed_dict.keys():
            self.is_pressed_dict[key] = False
        self.controls = CarControls()

    def release_controls(self, event):
        self.update_controls(event, is_pressed=False)

    def update_controls(self, event, is_pressed=True):
        key = keys_mapping[event.key()]
        if key in self.input_dict.keys():
            self.is_pressed_dict[self.input_dict[key]] = is_pressed

        if self.input_dict.get(key, None) == "SWITCH_CAR" and is_pressed:
            if self.overwrite_controls:  # reset car controls before switching cars
                self.arena.set_car_controls(self.car_ids[self.car_index], CarControls())
            self.car_index = (self.car_index + 1) % len(self.cars)

        if self.input_dict.get(key, None) == "TARGET_CAM" and is_pressed:
            self.TARGET_CAM = not self.TARGET_CAM

        if self.input_dict.get(key, None) == "CYCLE_TARGETS" and is_pressed:
            self.target_index = (self.target_index + 1) % len(self.cars)

        self.controls.throttle = self.is_pressed_dict["FORWARD"] - self.is_pressed_dict["BACKWARD"]
        self.controls.steer = self.is_pressed_dict["RIGHT"] - self.is_pressed_dict["LEFT"]
        self.controls.roll = self.is_pressed_dict["ROLL_RIGHT"] - self.is_pressed_dict["ROLL_LEFT"]
        self.controls.pitch = -self.controls.throttle
        self.controls.yaw = self.controls.steer
        self.controls.jump = self.is_pressed_dict["JUMP"]
        self.controls.handbrake = self.is_pressed_dict["POWERSLIDE"]
        self.controls.boost = self.is_pressed_dict["BOOST"]

    def update_ball_data(self):

        # plot ball data
        ball = self.arena.get_ball()
        ball_pos = ball.get_pos()

        # location
        ball_transform = self.ball.transform()
        ball_transform[0, 3] = -ball_pos.x
        ball_transform[1, 3] = ball_pos.y
        ball_transform[2, 3] = ball_pos.z
        self.ball.setTransform(ball_transform)

        # approx ball spin
        ball_angvel = ball.get_angvel()
        ball_angvel_np = np.array([ball_angvel.x, ball_angvel.y, ball_angvel.z])
        ball_delta_rot = ball_angvel_np * self.tick_skip / self.tick_rate

        self.ball.rotate(ball_delta_rot[2] / math.pi * 180, 0, 0, -1, local=True)
        self.ball.rotate(ball_delta_rot[0] / math.pi * 180, 0, 1, 0, local=True)
        self.ball.rotate(ball_delta_rot[1] / math.pi * 180, 1, 0, 0, local=True)

    def update_cars_data(self):

        for i, car_id in enumerate(self.car_ids):

            car = self.arena.get_car(car_id)
            car_pos = car.get_pos()
            car_angles = car.get_angles()

            self.cars[i].resetTransform()

            # location
            self.cars[i].translate(-car_pos.x, car_pos.y, car_pos.z)

            # rotation
            self.cars[i].rotate(car_angles.yaw / math.pi * 180, 0, 0, -1, local=True)
            self.cars[i].rotate(car_angles.pitch / math.pi * 180, 0, -1, 0, local=True)
            self.cars[i].rotate(car_angles.roll / math.pi * 180, 1, 0, 0, local=True)

    def update_camera_data(self):

        car = self.arena.get_car(self.car_ids[self.car_index])
        car_pos = car.get_pos()
        car_vel = car.get_vel()

        car_debug_info = f"{car.boost = }"
        self.cars[self.car_index].childItems()[0].text = car_debug_info

        self.cars[self.car_index].opts["edgeColor"] = (0, 0, 0, 1) if car.is_supersonic else self.default_edge_color

        # center camera around the car
        self.w.opts["center"] = pg.Vector(-car_pos.x, car_pos.y, car_pos.z + self.cam_dict["HEIGHT"])

        # calculate target cam values
        if self.TARGET_CAM:
            cam_pos = self.w.cameraPosition()
            target_pos = self.get_targets()[self.target_index].transform().matrix()[:3, 3]
            rel_target_pos = -target_pos[0] + cam_pos[0], target_pos[1] - cam_pos[1], target_pos[2] - cam_pos[2]
            rel_target_pos_norm = np.linalg.norm(rel_target_pos)

            target_azimuth = math.atan2(rel_target_pos[1], rel_target_pos[0])

            target_elevation = 0
            if rel_target_pos_norm != 0:
                target_elevation = math.asin(rel_target_pos[2] / rel_target_pos_norm)

            smaller_target_elevation = target_elevation * 2 / 3

            self.w.setCameraParams(azimuth=-target_azimuth / math.pi * 180,
                                   elevation=self.cam_dict["ANGLE"] - smaller_target_elevation / math.pi * 180)
        else:
            # car cam / first person view
            car_vel_2d_norm = math.sqrt(car_vel.y ** 2 + car_vel.x ** 2)
            if car_vel_2d_norm > 50:  # don't be sensitive to near 0 vel dir changes
                car_vel_azimuth = math.atan2(car_vel.y, car_vel.x)
                self.w.setCameraParams(azimuth=-car_vel_azimuth / math.pi * 180,
                                       elevation=self.cam_dict["ANGLE"])

    def update_plot_data(self):
        self.update_ball_data()
        self.update_cars_data()
        self.update_camera_data()

    def update(self):

        # only set car controls if overwrite_controls is true and there's at least one car
        if self.overwrite_controls and self.car_ids:
            self.arena.set_car_controls(self.car_ids[self.car_index], self.controls)

        # only call arena.step() if running in standalone mode
        if self.step_arena:
            self.arena.step(self.tick_skip)

        self.update_plot_data()

    def animation(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(16)
        self.app.exec()
