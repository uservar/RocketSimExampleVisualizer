from rocketsimvisualizer import VisualizerThread, CompositeController
import pyrocketsim as rs
import tomli


with open("rsvconfig.toml", "rb") as file:
    config_dict = tomli.load(file)


def main():
    # Initialize RocketSim (loads arena collision meshes, etc.)
    rs.init()

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

    v = VisualizerThread(arena, fps=60,
                         tick_rate=tick_rate,
                         tick_skip=tick_skip,
                         step_arena=True,  # False by default, handle physics ticks
                         overwrite_controls=True,  # False by default, use Keyboard/Controller
                         config_dict=config_dict, controller_class=controller_class)
    v.start()


if __name__ == "__main__":
    main()
