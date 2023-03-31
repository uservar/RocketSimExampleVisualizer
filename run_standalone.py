from rocketsimvisualizer import VisualizerThread, CompositeController
import RocketSim as rs
import tomli

with open("rsvconfig.toml", "rb") as file:
    config_dict = tomli.load(file)


def main():

    # setup rocketsim arena
    tick_rate = 120
    tick_skip = 2
    arena = rs.Arena(rs.SOCCAR, tick_rate)
    print(f"Arena tick rate: {arena.tick_rate}")

    # setup rocketsim cars
    for i in range(2):
        team = rs.BLUE if i % 2 else rs.ORANGE
        car = arena.add_car(team, rs.OCTANE)
        print(f"Car added to team {team} with id {car.id}")

    # controller to use
    controller_class = CompositeController

    v = VisualizerThread(arena,  # required, the rest is optional
                         fps=60,  # 60 by default
                         tick_rate=tick_rate,  # 120 by default
                         tick_skip=tick_skip,  # 2 by default
                         step_arena=True,  # False by default, handle physics ticks
                         overwrite_controls=True,  # False by default, use Keyboard/Controller
                         config_dict=config_dict,  # None by default, camera/input config
                         controller_class=controller_class)  # None by default, controller type
    v.start()


if __name__ == "__main__":
    main()
