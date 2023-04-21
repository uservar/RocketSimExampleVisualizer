from rocketsimvisualizer import VisualizerThread, CompositeController
import RocketSim as rs
import tomli

with open("rsvconfig.toml", "rb") as file:
    config_dict = tomli.load(file)


def main():
    # init rocketsim
    meshes_path = "collision_meshes"
    rs.init(meshes_path)

    # setup rocketsim arena
    arena = rs.Arena(rs.GameMode.SOCCAR)
    print(f"Arena tick rate: {arena.tick_rate}")

    # set mutators
    mutator_config = arena.get_mutator_config()
    mutator_config.boost_used_per_second = 0  # infinite boost
    arena.set_mutator_config(mutator_config)

    # set goal score callback
    arena.set_goal_score_callback(lambda *args, **kwargs: arena.reset_kickoff(), None)

    # setup rocketsim cars
    for i in range(2):
        team = rs.Team.BLUE if i % 2 else rs.Team.ORANGE
        car = arena.add_car(team, rs.CarConfig(0))
        print(f"Car added to team {team} with id {car.id}")

    # start visualizer
    v = VisualizerThread(arena,  # required, the rest is optional
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
