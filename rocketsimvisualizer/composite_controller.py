from rocketsimvisualizer import GenericController, KeyboardController, XboxController


class CompositeController(GenericController):
    def __init__(self, input_dict):
        super().__init__(input_dict)
        self.kc = KeyboardController(input_dict)
        self.xc = XboxController(input_dict)

        self.kc.switch_car = lambda *args: self.switch_car()
        self.kc.cycle_targets = lambda *args: self.cycle_targets()

        self.xc.switch_car = self.switch_car
        self.xc.cycle_targets = self.cycle_targets

    def reset_controls(self):
        self.kc.reset_controls()
        self.xc.reset_controls()

    def get_controls(self):
        self.target_cam = self.kc.target_cam or self.xc.target_cam

        self.controls.throttle = self.kc.controls.throttle + self.xc.controls.throttle
        self.controls.steer = self.kc.controls.steer + self.xc.controls.steer
        self.controls.roll = self.kc.controls.roll + self.xc.controls.roll
        self.controls.pitch = self.kc.controls.pitch + self.xc.controls.pitch
        self.controls.yaw = self.kc.controls.yaw + self.xc.controls.yaw
        self.controls.jump = self.kc.controls.jump or self.xc.controls.jump
        self.controls.handbrake = self.kc.controls.handbrake or self.xc.controls.handbrake
        self.controls.boost = self.kc.controls.boost or self.xc.controls.boost

        self.controls.clamp_fix()

        return self.controls
