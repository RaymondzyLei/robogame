"""RoboGame机器人控制系统"""

from .common.datahub import DataHub, get_datahub
from .common.events import *
from .common.types import *

from .vision.camera import VisionModule, get_vision_module
from .strategy.scheduler import StrategyModule, get_strategy_module
from .actuator.collect.collect import CollectModule, get_collect_module
from .actuator.place.place import PlaceModule, get_place_module
from .actuator.build.build import BuildModule, get_build_module

__all__ = [
    'DataHub', 'get_datahub',
    'VisionModule', 'get_vision_module',
    'StrategyModule', 'get_strategy_module',
    'CollectModule', 'get_collect_module',
    'PlaceModule', 'get_place_module',
    'BuildModule', 'get_build_module',
]