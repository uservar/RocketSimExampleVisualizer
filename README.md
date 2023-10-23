# RocketSimExampleVisualizer

A pyqtgraph visualizer for [RocketSim](https://github.com/ZealanL/RocketSim) using [mtheall's python bindings](https://github.com/mtheall/RocketSim/tree/python-dev)

## Installation

```
git clone https://github.com/uservar/RocketSimExampleVisualizer
cd RocketSimExampleVisualizer
pip install -e .
```

## Usage

If you just want to use this as a standalone program, simply run:
```
python run_standalone.py
```

Or check out `run_standalone_atba.py` for an example of using this with a simple bot.

If you intend to use this in a pre-existing project you can try something like this:

```python
from rocketsimvisualizer import VisualizerThread
v = VisualizerThread(arena)
v.start()
```

Optionally you can change keyboard and camera settings by changing `rsvconfig.toml` or poviding your own `config_dict`
