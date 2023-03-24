from rocketsimvisualizer import VisualizerThread, CompositeController
import pyrocketsim as RS
import tomli


with open("rsvconfig.toml", "rb") as file:
    config_dict = tomli.load(file)


def main():
    # Initialize RocketSim (loads arena collision meshes, etc.)
    RS.init()

    # setup rocketsim arena
    tick_rate = 120
    tick_skip = 2
    arena = RS.Arena(RS.SOCCAR, tick_rate)
    print(f"Arena tick rate: {arena.tick_rate}")

    # setup ball initial state
    ball_state = arena.ball.get_state()
    ball_state.pos = RS.Vec(500, 500, 1500)
    ball_state.vel = RS.Vec(0, 0, 0.1)
    arena.ball.set_state(ball_state)
    print("Set ball state")

    # setup rocketsim cars
    for i in range(2):
        team = RS.BLUE if i % 2 else RS.ORANGE
        car = arena.add_car(team, RS.OCTANE)
        car_state = car.get_state()
        car_state.boost = 100
        car_state.pos = RS.Vec(car.id * 200, car.id * 200, 200)
        car_state.vel = RS.Vec(100, 100, 100)
        car_state.ang_vel = RS.Vec(0, 0, 5.5)
        car.set_state(car_state)
        print(f"Car added to team {team} with id {car.id}")

    # controller to use
    controller_class = CompositeController

    v = VisualizerThread(arena, fps=60,
                         tick_rate=tick_rate, tick_skip=tick_skip,
                         step_arena=True,  # set to False in case tick updates happen elsewhere
                         overwrite_controls=True,
                         config_dict=config_dict, controller_class=controller_class)
    v.start()


if __name__ == "__main__":
    main()
