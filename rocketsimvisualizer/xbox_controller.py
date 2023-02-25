from rocketsimvisualizer import GenericController

from inputs import get_gamepad
import math
import threading

MAX_TRIG_VAL = math.pow(2, 8)
MAX_JOY_VAL = math.pow(2, 15)


class XboxController(GenericController):
    def __init__(self, input_dict):
        super().__init__(input_dict)
        # TODO: implement input_dict functionality to determine bindings
        self.LeftJoystickY = 0
        self.LeftJoystickX = 0
        self.RightJoystickY = 0
        self.RightJoystickX = 0
        self.LeftTrigger = 0
        self.RightTrigger = 0
        self.LeftBumper = 0
        self.RightBumper = 0
        self.A = 0
        self.X = 0
        self.Y = 0
        self.B = 0
        self.LeftThumb = 0
        self.RightThumb = 0
        self.Back = 0
        self.Start = 0
        self.LeftDPad = 0
        self.RightDPad = 0
        self.UpDPad = 0
        self.DownDPad = 0

        self.y_pressed = False
        self.start_pressed = False
        self.back_pressed = False

        self._monitor_thread = threading.Thread(target=self._monitor_controller, args=())
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

    def read(self):  # return the buttons/triggers that you care about in this method
        return {
            "leftX": self.LeftJoystickX,
            "leftY": self.LeftJoystickY,
            "A": bool(self.A),
            "B": bool(self.B),
            "X": bool(self.X),
            "Y": bool(self.Y),
            "LT": self.LeftTrigger,
            "RT": self.RightTrigger,
            "RB": self.RightBumper,
            "LB": self.LeftBumper,
            "START": bool(self.Start),
            "BACK": bool(self.Back)
        }

    def _monitor_controller(self):
        while True:
            try:
                events = get_gamepad()
            except Exception as e:
                print(e)
                return
            for event in events:
                if event.code == 'ABS_Y':
                    # normalize between -1 and 1
                    self.LeftJoystickY = event.state / XboxController.MAX_JOY_VAL
                elif event.code == 'ABS_X':
                    self.LeftJoystickX = event.state / XboxController.MAX_JOY_VAL
                elif event.code == 'ABS_RY':
                    self.RightJoystickY = event.state / XboxController.MAX_JOY_VAL
                elif event.code == 'ABS_RX':
                    self.RightJoystickX = event.state / XboxController.MAX_JOY_VAL
                elif event.code == 'ABS_Z':
                    # normalize between 0 and 1
                    self.LeftTrigger = event.state / XboxController.MAX_TRIG_VAL
                elif event.code == 'ABS_RZ':
                    self.RightTrigger = event.state / XboxController.MAX_TRIG_VAL
                elif event.code == 'BTN_TL':
                    self.LeftBumper = event.state
                elif event.code == 'BTN_TR':
                    self.RightBumper = event.state
                elif event.code == 'BTN_SOUTH':
                    self.A = event.state
                elif event.code == 'BTN_NORTH':
                    self.Y = event.state  # previously switched with X
                elif event.code == 'BTN_WEST':
                    self.X = event.state  # previously switched with Y
                elif event.code == 'BTN_EAST':
                    self.B = event.state
                elif event.code == 'BTN_THUMBL':
                    self.LeftThumb = event.state
                elif event.code == 'BTN_THUMBR':
                    self.RightThumb = event.state
                elif event.code == 'BTN_SELECT':
                    self.Back = event.state
                elif event.code == 'BTN_START':
                    self.Start = event.state
                elif event.code == 'BTN_TRIGGER_HAPPY1':
                    self.LeftDPad = event.state
                elif event.code == 'BTN_TRIGGER_HAPPY2':
                    self.RightDPad = event.state
                elif event.code == 'BTN_TRIGGER_HAPPY3':
                    self.UpDPad = event.state
                elif event.code == 'BTN_TRIGGER_HAPPY4':
                    self.DownDPad = event.state

            self.update_controls()

    def update_controls(self):
        controls = self.read()

        self.controls.throttle = controls['RT'] or -controls['LT']
        self.controls.steer = controls["leftX"]
        self.controls.roll = controls['RB'] or -controls['LB']
        self.controls.pitch = -controls["leftY"]
        self.controls.yaw = controls["leftX"]
        self.controls.jump = controls["A"]
        self.controls.handbrake = controls["X"]
        self.controls.boost = controls["B"]

        if controls['Y'] and not self.y_pressed:
            self.target_cam = not self.target_cam
            self.y_pressed = True

        if controls['START'] and not self.start_pressed:
            self.start_pressed = True
            self.cycle_targets()

        if controls['BACK'] and not self.back_pressed:
            self.back_pressed = True
            self.switch_car()

        if not controls['START'] and self.start_pressed:
            self.start_pressed = False
        if not controls['BACK'] and self.back_pressed:
            self.back_pressed = False
        if not controls['Y'] and self.y_pressed:
            self.y_pressed = False
