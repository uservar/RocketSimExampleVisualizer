# RocketSimExampleVisualizer

A visualizer for Rocketsim using pyqtgraph

## Intallation

```
git clone https: // github.com / uservar / RocketSimExampleVisualizer
cd RocketSimExampleVisualizer
pip install - r requirements.txt
```

## Usage

- If you just want to use this as a standalone program, simply run:
```
python run_standalone.py
```

- If you intend to use this in a pre-existing project, you can do something like this:

```python
from rocketsimvisualizer import Visualizer
v = Visualizer(arena, car_ids)
v.animation()
```

Optionally you can change keyboard and camera settings by changing `rsvconfig.toml` or poviding your own `config_dict`
