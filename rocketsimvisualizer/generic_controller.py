import RocketSim


class GenericController:

    def __init__(self, input_dict):
        self.input_dict = input_dict
        self.is_pressed_dict = {input_key: False for input_key in self.input_dict.values()}
        self.controls = RocketSim.CarControls()
        self.target_cam = False

    def reset_controls(self):
        for key in self.is_pressed_dict.keys():
            self.is_pressed_dict[key] = False
        self.controls = RocketSim.CarControls()

    def get_controls(self):
        return self.controls

    # These two methods will be overwritten later
    @classmethod
    def switch_car():
        pass

    @classmethod
    def cycle_targets():
        pass
