from rocketsim import Angle, Vec3
from rocketsim.sim import Arena, CarConfig, GameMode, Team, CarControls

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.opengl as gl
import models.obj as obj

import numpy as np
import math
# import time

from collections import defaultdict

# TODO: put these settings in a .ini file
INPUT_KEYS = {"Z": "FORWARD",
              "S": "BACKWARD",
              "D": "RIGHT",
              "Q": "LEFT",
              "Alt": "ROLL_RIGHT",
              "Shift": "ROLL_LEFT",
              "U": "JUMP",
              "I": "POWERSLIDE",
              "M": "BOOST",
              "B": "BALL_CAM",
              "Space": "SWITCH_CAR"}

CAM_FOV = 110
CAM_DISTANCE = 270
CAM_HEIGHT = 110
CAM_ANGLE = 3

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
                 step_arena=True, overwrite_controls=True):
        self.arena = arena
        self.car_ids = car_ids
        self.tick_rate = tick_rate
        self.tick_skip = tick_skip
        self.step_arena = step_arena
        self.overwrite_controls = overwrite_controls

        self.app = pg.mkQApp()

        # window settings
        self.w = KeyPressWindow()
        self.w.setWindowTitle("pyqtgraph visualizer")
        self.w.setGeometry(0, 50, 1280, 720)

        # initial camera settings
        self.ball_cam = True
        self.w.opts["fov"] = CAM_FOV
        self.w.opts["distance"] = CAM_DISTANCE
        self.w.show()

        # Add ground grid
        gz = gl.GLGridItem()
        gz.setSize(8192, 10240 + 880 * 2, 1)
        gz.setSpacing(100, 100, 100)
        self.w.addItem(gz)

        # Create stadium 3d model
        stadium_object = obj.OBJ("models/field_simplified.obj")
        md = gl.MeshData(vertexes=stadium_object.vertices, faces=stadium_object.faces)
        m4 = gl.GLMeshItem(meshdata=md, smooth=False, drawFaces=False, drawEdges=True, edgeColor=(1, 1, 1, 1))
        m4.rotate(90, 0, 0, 1)
        self.w.addItem(m4)

        # index of the car we control/spectate
        self.car_index = 0

        # Create car geometry
        car_object = obj.OBJ("models/Octane_decimated.obj")
        md = gl.MeshData(vertexes=car_object.vertices, faces=car_object.faces)

        self.cars = []
        for i, car_id in enumerate(self.car_ids):
            team = i % 2  # workaround until we get car.team
            car_color = (0, 0.4, 0.8, 1) if team == 0 else (1, 0.2, 0.1, 1)
            car_mesh = gl.GLMeshItem(meshdata=md, smooth=False, drawFaces=True,
                                     drawEdges=True, color=car_color, edgeColor=(1, 1, 1, 1))
            self.cars.append(car_mesh)
            self.w.addItem(car_mesh)
            print(f"Car geometry added for id {car_id}")

        # Create ball geometry
        ball_md = gl.MeshData.sphere(rows=8, cols=16, radius=91.25)
        self.ball = gl.GLMeshItem(
            meshdata=ball_md, smooth=False, drawFaces=True, drawEdges=True, edgeColor=(1, 1, 1, 1), color=(0.1, 0.1, 0.1, 1)
        )
        self.w.addItem(self.ball)

        # connect key press events to update our controls
        self.is_pressed_dict = {input_key: False for input_key in INPUT_KEYS.values()}
        self.controls = CarControls()
        self.w.sigKeyPress.connect(self.update_controls)
        self.w.sigKeyRelease.connect(self.release_controls)
        self.app.focusChanged.connect(self.reset_controls)

        self.update()

    def reset_controls(self):
        for key in self.is_pressed_dict.keys():
            self.is_pressed_dict[key] = False
        self.controls = CarControls()

    def release_controls(self, event):
        self.update_controls(event, is_pressed=False)

    def update_controls(self, event, is_pressed=True):
        key = keys_mapping[event.key()]
        if key in INPUT_KEYS.keys():
            self.is_pressed_dict[INPUT_KEYS[key]] = is_pressed

        if key in INPUT_KEYS.keys() and INPUT_KEYS[key] == "SWITCH_CAR" and is_pressed:
            if self.overwrite_controls:  # reset car controls before switching cars
                self.arena.set_car_controls(self.car_ids[self.car_index], CarControls())
            self.car_index = (self.car_index + 1) % len(self.cars)

        if key in INPUT_KEYS.keys() and INPUT_KEYS[key] == "BALL_CAM" and is_pressed:
            self.ball_cam = not self.ball_cam

        self.controls.throttle = self.is_pressed_dict["FORWARD"] - self.is_pressed_dict["BACKWARD"]
        self.controls.steer = self.is_pressed_dict["RIGHT"] - self.is_pressed_dict["LEFT"]
        self.controls.roll = self.is_pressed_dict["ROLL_RIGHT"] - self.is_pressed_dict["ROLL_LEFT"]
        self.controls.pitch = -self.controls.throttle
        self.controls.yaw = self.controls.steer
        self.controls.jump = self.is_pressed_dict["JUMP"]
        self.controls.handbrake = self.is_pressed_dict["POWERSLIDE"]
        self.controls.boost = self.is_pressed_dict["BOOST"]

    def set_plot_data(self):

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

        # plot car data
        for i, car_id in enumerate(self.car_ids):

            car = self.arena.get_car(car_id)
            car_pos = car.get_pos()
            car_vel = car.get_vel()
            car_angles = car.get_angles()

            self.cars[i].resetTransform()

            # location
            self.cars[i].translate(-car_pos.x, car_pos.y, car_pos.z)

            # rotation
            self.cars[i].rotate(car_angles.yaw / math.pi * 180, 0, 0, -1, local=True)
            self.cars[i].rotate(car_angles.pitch / math.pi * 180, 0, -1, 0, local=True)
            self.cars[i].rotate(car_angles.roll / math.pi * 180, 1, 0, 0, local=True)

            # set camera around a certain car
            if i == self.car_index:
                self.w.opts["fov"] = CAM_FOV + car.is_supersonic * 5

                # center camera around the car
                self.w.opts["center"] = pg.Vector(-car_pos.x, car_pos.y, car_pos.z + CAM_HEIGHT)

                # calculate ball cam values
                if self.ball_cam:
                    cam_pos = self.w.cameraPosition()
                    rel_ball_pos = ball_pos.x + cam_pos[0], ball_pos.y - cam_pos[1], ball_pos.z - cam_pos[2]
                    rel_ball_pos_norm = np.linalg.norm(rel_ball_pos)

                    ball_azimuth = math.atan2(rel_ball_pos[1], rel_ball_pos[0])

                    ball_elevation = 0
                    if rel_ball_pos_norm != 0:
                        ball_elevation = math.asin(rel_ball_pos[2] / rel_ball_pos_norm)

                    smaller_ball_elevation = ball_elevation * 0.5

                    self.w.setCameraParams(azimuth=-ball_azimuth / math.pi * 180,
                                           elevation=CAM_ANGLE - smaller_ball_elevation / math.pi * 180)
                else:
                    # car cam
                    car_vel_2d_norm = math.sqrt(car_vel.y ** 2 + car_vel.x ** 2)
                    if car_vel_2d_norm > 50:  # don't be sensitive to near 0 vel dir changes
                        car_vel_azimuth = math.atan2(car_vel.y, car_vel.x)
                        self.w.setCameraParams(azimuth=-car_vel_azimuth / math.pi * 180,
                                               elevation=CAM_ANGLE)

    def update(self):
        # start_time = time.time_ns()

        if self.overwrite_controls:
            self.arena.set_car_controls(self.car_ids[self.car_index], self.controls)

        if self.step_arena:
            self.arena.step(self.tick_skip)

        self.set_plot_data()

        # end_time = time.time_ns()

    def animation(self, step_arena=False):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(16)
        self.app.exec()


def main():

    # setup rocketsim arena
    tick_rate = 120
    tick_skip = 2
    arena = Arena(GameMode.Soccar, tick_rate)
    print(f"Arena tick rate: {arena.get_tick_rate()}")

    # setup ball initial state
    ball = arena.get_ball()
    ball.pos = Vec3(500, 500, 1500)
    ball.vel = Vec3(0, 0, 0.1)
    arena.ball = ball
    print("Set ball state")

    # setup rocketsim cars
    car_ids = []
    for i in range(2):
        team = Team.Blue if i % 2 else Team.Orange
        car_id = arena.add_car(team, CarConfig.Octane)

        # workaround to set unlimited boost
        car = arena.get_car(car_id)
        car.boost = 1e8
        car.pos = Vec3(car_id * 75, car_id * 75, 25)  # don't spawn in the same place
        arena.set_car(car_id, car)

        car_ids.append(car_id)
        print(f"Car added to team {team} with id {car_id}")

    v = Visualizer(arena, car_ids, tick_rate=tick_rate, tick_skip=tick_skip,
                   step_arena=True,  # set to False in case tick updates happen elsewhere
                   overwrite_controls=True)
    v.animation()


if __name__ == "__main__":
    main()
