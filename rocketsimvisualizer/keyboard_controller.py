from rocketsimvisualizer import GenericController

from pyqtgraph.Qt import QtCore, QtGui
from collections import defaultdict

import RocketSim


# Get key mappings from Qt namespace
qt_keys = (
    (getattr(QtCore.Qt, attr), attr[4:])
    for attr in dir(QtCore.Qt)
    if attr.startswith("Key_")
)
keys_mapping = defaultdict(lambda: "unknown", qt_keys)


class KeyboardController(GenericController):
    def __init__(self, input_dict):
        super().__init__(input_dict)

        self.app = QtGui.QGuiApplication.instance()
        self.w = self.app.topLevelWidgets()[0]
        self.w.keyPressEvent = self.update_controls
        self.w.keyReleaseEvent = self.release_controls

    def release_controls(self, event):
        if event.isAutoRepeat():
            return
        self.update_controls(event, is_pressed=False)

    def update_controls(self, event, is_pressed=True):
        if event.isAutoRepeat():
            return
        key = keys_mapping[event.key()]
        if key in self.input_dict.keys():
            self.is_pressed_dict[self.input_dict[key]] = is_pressed

        if self.input_dict.get(key, None) == "TARGET_CAM" and is_pressed:
            self.target_cam = not self.target_cam

        if self.input_dict.get(key, None) == "SWITCH_CAR" and is_pressed:
            self.switch_car()

        if self.input_dict.get(key, None) == "CYCLE_TARGETS" and is_pressed:
            self.cycle_targets()

        self.controls.throttle = self.is_pressed_dict["FORWARD"] - self.is_pressed_dict["BACKWARD"]
        self.controls.steer = self.is_pressed_dict["RIGHT"] - self.is_pressed_dict["LEFT"]
        self.controls.roll = self.is_pressed_dict["ROLL_RIGHT"] - self.is_pressed_dict["ROLL_LEFT"]
        self.controls.pitch = -self.controls.throttle
        self.controls.yaw = self.controls.steer
        self.controls.jump = self.is_pressed_dict["JUMP"]
        self.controls.handbrake = self.is_pressed_dict["POWERSLIDE"]
        self.controls.boost = self.is_pressed_dict["BOOST"]
