from rocketsim import Angle, Vec3
from rocketsim.sim import Arena, CarConfig, GameMode, Team, CarControls

from rocketsimvisualizer import Visualizer

import tomli

with open("rsvconfig.toml", "rb") as file:
    config_dict = tomli.load(file)


def main():

    # setup rocketsim arena
    tick_rate = 120
    tick_skip = 2
    arena = Arena(GameMode.Soccar, tick_rate)
    print(f"Arena tick rate: {arena.get_tick_rate()}")

    # setup ball initial state
    ball = arena.get_ball()
    ball.pos = Vec3(500, 500, 1500)
    ball.vel = Vec3(0, 0, 0.1)
    arena.ball = ball
    print("Set ball state")

    # setup rocketsim cars
    car_ids = []
    for i in range(2):
        team = Team.Blue if i % 2 else Team.Orange
        car_id = arena.add_car(team, CarConfig.Octane)

        car = arena.get_car(car_id)
        car.boost = 100
        car.pos = Vec3(car_id * 75, car_id * 75, 20)  # don't spawn in the same place

        # fix some weird initialization issues
        car.is_jumping = False
        car.has_jumped = False
        car.has_flipped = False

        arena.set_car(car_id, car)

        car_ids.append(car_id)
        print(f"Car added to team {team} with id {car_id}")

    v = Visualizer(arena, car_ids, tick_rate=tick_rate, tick_skip=tick_skip,
                   step_arena=True,  # set to False in case tick updates happen elsewhere
                   overwrite_controls=True,
                   config_dict=config_dict)
    v.animation()


if __name__ == "__main__":
    main()
