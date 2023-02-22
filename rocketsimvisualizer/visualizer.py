from rocketsimvisualizer.models import obj
import RocketSim

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
    def __init__(self, arena,
                 tick_rate=120, tick_skip=2,
                 step_arena=False, overwrite_controls=False,
                 config_dict=None):
        self.arena = arena
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
        self.target_cam = False
        self.w.opts["fov"] = self.cam_dict["FOV"]
        self.w.opts["distance"] = self.cam_dict["DISTANCE"]
        self.w.show()

        # Add ground grid
        gz = gl.GLGridItem()
        gz.setSize(8192, 10240 + 880 * 2, 1)
        gz.setSpacing(100, 100, 100)
        self.w.addItem(gz)

        # debug info
        self.text_item = gl.GLTextItem(pos=(0, 0, 60))

        self.default_edge_color = (1, 1, 1, 1)

        # Create stadium 3d model
        stadium_object = obj.OBJ(current_dir / "models/field_simplified.obj")
        md = gl.MeshData(vertexes=stadium_object.vertices, faces=stadium_object.faces)
        m4 = gl.GLMeshItem(meshdata=md, smooth=False, drawFaces=False, drawEdges=True,
                           edgeColor=self.default_edge_color)
        m4.rotate(90, 0, 0, 1)
        self.w.addItem(m4)

        # Create ball geometry
        ball_radius = self.arena.ball.get_radius() * 50
        ball_md = gl.MeshData.sphere(rows=8, cols=16, radius=ball_radius)
        self.ball = gl.GLMeshItem(meshdata=ball_md, smooth=False, drawFaces=True, drawEdges=True,
                                  edgeColor=self.default_edge_color, color=(0.1, 0.1, 0.1, 1))
        self.w.addItem(self.ball)

        # Create ground projection for the ball
        ball_proj_md = gl.MeshData.cylinder(rows=1, cols=16, length=0, radius=round(ball_radius))
        self.ball_proj = gl.GLMeshItem(meshdata=ball_proj_md, smooth=False, drawFaces=False,
                                       drawEdges=True, edgeColor=self.default_edge_color)
        self.w.addItem(self.ball_proj)

        # Create boost geometry
        big_boost_md = gl.MeshData.cylinder(rows=1, cols=4, length=64, radius=160)
        small_boost_md = gl.MeshData.cylinder(rows=1, cols=4, length=64, radius=144)

        self.boost_pads = []
        for pad in arena.get_boost_pads():
            pad_pos = pad.get_pos()
            boost_md = big_boost_md if pad.is_big else small_boost_md
            boost_mesh = gl.GLMeshItem(meshdata=boost_md, drawFaces=False, drawEdges=True,
                                       edgeColor=self.default_edge_color)
            boost_mesh.rotate(45, 0, 0, 1)
            boost_mesh.translate(-pad_pos.x, pad_pos.y, pad_pos.z)
            self.boost_pads.append(boost_mesh)
            self.w.addItem(boost_mesh)

        # Create car geometry
        car_object = obj.OBJ(current_dir / "models/Octane_decimated.obj")
        car_md = gl.MeshData(vertexes=car_object.vertices, faces=car_object.faces)

        car_hitbox_object = obj.OBJ(current_dir / "models/OctaneHitbox.obj")
        car_hitbox_md = gl.MeshData(vertexes=car_hitbox_object.vertices,
                                    faces=car_hitbox_object.faces)

        self.cars = []
        for car in arena.get_cars():
            car_color = (0, 0.4, 0.8, 1) if car.team == 0 else (1, 0.2, 0.1, 1)

            car_mesh = gl.GLMeshItem(meshdata=car_md, smooth=False,
                                     drawFaces=True, drawEdges=True,
                                     color=car_color, edgeColor=self.default_edge_color)

            hitbox_mesh = gl.GLMeshItem(meshdata=car_hitbox_md, smooth=False,
                                        drawFaces=False, drawEdges=True, color=car_color,
                                        edgeColor=self.default_edge_color)
            hitbox_mesh.setParentItem(car_mesh)
            self.cars.append(car_mesh)
            self.w.addItem(car_mesh)

        # index of the car we control/spectate
        self.car_index = 0

        # item to track with target cam
        self.target_index = -1

        # connect key press events to update our controls
        self.is_pressed_dict = {input_key: False for input_key in self.input_dict.values()}
        self.controls = RocketSim.CarControls()
        self.w.sigKeyPress.connect(self.update_controls)
        self.w.sigKeyRelease.connect(self.release_controls)
        self.app.focusChanged.connect(self.reset_controls)

        self.update()

    def get_cam_targets(self):
        if not self.cars:
            return [self.ball]
        targets = self.cars + [self.ball]
        targets.pop(self.car_index)
        return targets

    def get_cam_target(self):
        targets = self.get_cam_targets()
        self.target_index = self.target_index % len(targets)
        return targets[self.target_index]

    def reset_controls(self):
        for key in self.is_pressed_dict.keys():
            self.is_pressed_dict[key] = False
        self.controls = RocketSim.CarControls()

    def release_controls(self, event):
        self.update_controls(event, is_pressed=False)

    def update_controls(self, event, is_pressed=True):
        key = keys_mapping[event.key()]
        if key in self.input_dict.keys():
            self.is_pressed_dict[self.input_dict[key]] = is_pressed

        if self.input_dict.get(key, None) == "SWITCH_CAR" and is_pressed:
            if self.overwrite_controls:  # reset car controls before switching cars
                self.arena.get_cars()[self.car_index].set_controls(RocketSim.CarControls())
            self.car_index = (self.car_index + 1) % len(self.cars)

        if self.input_dict.get(key, None) == "TARGET_CAM" and is_pressed:
            self.target_cam = not self.target_cam

        if self.input_dict.get(key, None) == "CYCLE_TARGETS" and is_pressed:
            self.target_index = (self.target_index + 1) % len(self.get_cam_targets())

        self.controls.throttle = self.is_pressed_dict["FORWARD"] - self.is_pressed_dict["BACKWARD"]
        self.controls.steer = self.is_pressed_dict["RIGHT"] - self.is_pressed_dict["LEFT"]
        self.controls.roll = self.is_pressed_dict["ROLL_RIGHT"] - self.is_pressed_dict["ROLL_LEFT"]
        self.controls.pitch = -self.controls.throttle
        self.controls.yaw = self.controls.steer
        self.controls.jump = self.is_pressed_dict["JUMP"]
        self.controls.handbrake = self.is_pressed_dict["POWERSLIDE"]
        self.controls.boost = self.is_pressed_dict["BOOST"]

    def update_boost_pad_data(self):
        for i, pad in enumerate(self.arena.get_boost_pads()):
            pad_state = pad.get_state()
            self.boost_pads[i].show() if pad_state.is_active else self.boost_pads[i].hide()

    def update_ball_data(self):

        # plot ball data
        ball_state = self.arena.ball.get_state()

        # location
        ball_transform = self.ball.transform()
        ball_transform[0, 3] = -ball_state.pos.x
        ball_transform[1, 3] = ball_state.pos.y
        ball_transform[2, 3] = ball_state.pos.z
        self.ball.setTransform(ball_transform)

        # approx ball spin
        ball_angvel_np = np.array([ball_state.ang_vel.x, ball_state.ang_vel.y, ball_state.ang_vel.z])
        ball_delta_rot = ball_angvel_np * self.tick_skip / self.tick_rate

        self.ball.rotate(ball_delta_rot[2] / math.pi * 180, 0, 0, -1, local=True)
        self.ball.rotate(ball_delta_rot[0] / math.pi * 180, 0, 1, 0, local=True)
        self.ball.rotate(ball_delta_rot[1] / math.pi * 180, 1, 0, 0, local=True)

        # ball ground projection
        self.ball_proj.resetTransform()
        self.ball_proj.translate(-ball_state.pos.x, ball_state.pos.y, 0)

    def update_cars_data(self):

        for i, car in enumerate(self.arena.get_cars()):

            car_state = car.get_state()
            car_angles = car_state.angles

            self.cars[i].resetTransform()

            # location
            self.cars[i].translate(-car_state.pos.x, car_state.pos.y, car_state.pos.z)

            # rotation
            self.cars[i].rotate(car_angles.yaw / math.pi * 180, 0, 0, -1, local=True)
            self.cars[i].rotate(car_angles.pitch / math.pi * 180, 0, -1, 0, local=True)
            self.cars[i].rotate(car_angles.roll / math.pi * 180, 1, 0, 0, local=True)

            # visual indicator for going supersonic
            self.cars[i].opts["edgeColor"] = (0, 0, 0, 1) if car_state.is_supersonic else self.default_edge_color

    def update_camera_data(self):

        # calculate target cam values
        if self.target_cam:
            cam_pos = self.w.cameraPosition()
            target_pos = self.get_cam_target().transform().matrix()[:3, 3]
            rel_target_pos = -target_pos[0] + cam_pos[0], target_pos[1] - cam_pos[1], target_pos[2] - cam_pos[2]
            rel_target_pos_norm = np.linalg.norm(rel_target_pos)

            target_azimuth = math.atan2(rel_target_pos[1], rel_target_pos[0])

            target_elevation = 0
            if rel_target_pos_norm != 0:
                target_elevation = math.asin(rel_target_pos[2] / rel_target_pos_norm)

            smaller_target_elevation = target_elevation * 2 / 3

            self.w.setCameraParams(azimuth=-target_azimuth / math.pi * 180,
                                   elevation=self.cam_dict["ANGLE"] - smaller_target_elevation / math.pi * 180)

        if self.cars:

            car = self.arena.get_cars()[self.car_index]
            car_state = car.get_state()

            # center camera around the car
            self.w.opts["center"] = pg.Vector(-car_state.pos.x, car_state.pos.y, car_state.pos.z + self.cam_dict["HEIGHT"])

            # debug info
            self.text_item.text = f"{car_state.boost=:.1f}"
            self.text_item.setParentItem(self.cars[self.car_index])

            if not self.target_cam:
                # non-target_cam cam
                car_vel_2d_norm = math.sqrt(car_state.vel.y ** 2 + car_state.vel.x ** 2)
                if car_vel_2d_norm > 50:  # don't be sensitive to near 0 vel dir changes
                    car_vel_azimuth = math.atan2(car_state.vel.y, car_state.vel.x)
                    self.w.setCameraParams(azimuth=-car_vel_azimuth / math.pi * 180,
                                           elevation=self.cam_dict["ANGLE"])

    def update_plot_data(self):
        self.update_boost_pad_data()
        self.update_ball_data()
        self.update_cars_data()
        self.update_camera_data()

    def update(self):

        # only set car controls if overwrite_controls is true and there's at least one car
        if self.overwrite_controls and self.cars:
            self.arena.get_cars()[self.car_index].set_controls(self.controls)

        # only call arena.step() if running in standalone mode
        if self.step_arena:
            self.arena.step(self.tick_skip)

        self.update_plot_data()

    def animation(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(16)
        self.app.exec()
