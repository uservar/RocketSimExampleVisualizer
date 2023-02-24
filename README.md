# RocketSimExampleVisualizer

A pyqtgraph visualizer for [RocketSim](https://github.com/ZealanL/RocketSim) uses a [version](https://github.com/uservar/RocketSim/tree/python) of mtheall's python [bindings](https://github.com/mtheall/RocketSim/tree/python)

## Installation

```
git clone https://github.com/uservar/RocketSimExampleVisualizer
cd RocketSimExampleVisualizer
pip install -r requirements.txt
```

## Usage

If you just want to use this as a standalone program, simply run:
```
python run_standalone.py
```

Although untested, if you intend to use this in a pre-existing project you can try something like this:

```python
from rocketsimvisualizer import Visualizer
v = Visualizer(arena)
v.animation()
```

Optionally you can change keyboard and camera settings by changing `rsvconfig.toml` or poviding your own `config_dict`
