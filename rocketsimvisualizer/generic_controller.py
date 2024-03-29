import RocketSim as rs


class GenericController:

    def __init__(self, input_dict):
        self.input_dict = input_dict
        self.is_pressed_dict = {input_key: False for input_key in self.input_dict.values()}
        self.controls = rs.CarControls()

    def reset_controls(self):
        for key in self.is_pressed_dict.keys():
            self.is_pressed_dict[key] = False
        self.controls = rs.CarControls()

    def get_controls(self):
        return self.controls

    # These methods will be overwritten later
    @classmethod
    def switch_car():
        pass

    @classmethod
    def switch_target():
        pass

    @classmethod
    def toggle_target_cam():
        pass

    @classmethod
    def toggle_free_cam():
        pass
