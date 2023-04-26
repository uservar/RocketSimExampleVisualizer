from rocketsimvisualizer import Visualizer, CompositeController
import RocketSim as rs
import tomli

with open("rsvconfig.toml", "rb") as file:
    config_dict = tomli.load(file)


def sign(x):
    return -1 if x < 0 else 1


class AtbaVisualizer(Visualizer):

    def update_controls(self):
        car = self.arena.get_car_from_id(self.car_id)
        car_state = car.get_state()
        ball_state = self.arena.ball.get_state()

        ball_pos = ball_state.pos.as_numpy()
        car_pos = car_state.pos.as_numpy()
        car_rot_mat = car_state.rot_mat.as_numpy()

        ball_pos_relative_to_car = ball_pos - car_pos
        ball_pos_local_to_car = car_rot_mat.dot(ball_pos_relative_to_car)

        controls = rs.CarControls()
        controls.steer = sign(ball_pos_local_to_car[1])
        controls.throttle = 1

        car.set_controls(controls)


def main():
    # init rocketsim
    meshes_path = "collision_meshes"
    rs.init(meshes_path)

    # setup rocketsim arena
    arena = rs.Arena(rs.GameMode.SOCCAR)
    print(f"Arena tick rate: {arena.tick_rate}")

    # set goal score callback
    arena.set_goal_score_callback(lambda *args, **kwargs: arena.reset_kickoff(), None)

    # setup rocketsim cars
    for i in range(1):
        team = rs.Team.BLUE if i % 2 else rs.Team.ORANGE
        car = arena.add_car(team, rs.CarConfig(0))
        print(f"Car added to team {team} with id {car.id}")

    # start visualizer
    v = AtbaVisualizer(arena,  # required, the rest is optional
                       meshes_path=meshes_path,  # relative path "collision_meshes" by default
                       fps=60,  # 60 by default
                       step_arena=True,  # False by default, handle physics ticks
                       tick_skip=2,  # tick_rate / fps by default, used if step_arena is True
                       enable_debug_text=True,  # True by default, render debug info
                       overwrite_controls=True,  # False by default, use Keyboard/Controller
                       config_dict=config_dict,  # None by default, camera/input config
                       controller_class=CompositeController)  # None by default, controller type
    v.start()


if __name__ == "__main__":
    main()
