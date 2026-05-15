"""RoboGame机器人控制系统"""

from .common.datahub import DataHub, get_datahub
from .common.events import *
from .common.types import *
from .common.scheduler import *

from .vision.camera import VisionModule, get_vision_module
from .strategy.scheduler import StrategyModule, get_strategy_module
from .actuator.collect.collect import CollectModule, get_collect_module
from .actuator.place.place import PlaceModule, get_place_module
from .actuator.build.build import BuildModule, get_build_module

from .hardware import *
from .hardware.pca9685 import PCA9685Driver, get_pca9685_driver
from .hardware.motor import MotorController, DCMotor, StepperMotor
from .hardware.servo import ServoController, GripperServo, ArmServo, ContinuousRotationServo
from .hardware.gripper import GripperController, DualGripperController
from .hardware.motion import MotionController, OmniMotionController, ArmController

__all__ = [
    # Common
    'DataHub', 'get_datahub',
    'DataHubEvent', 'VisionEvent', 'StrategyEvent',
    'CollectEvent', 'PlaceEvent', 'BuildEvent', 'ModuleEvent',
    'StatusCode', 'ErrorCode', 'ModuleStatus', 'Position', 'Pose',
    'CubeInfo', 'TaskParam', 'ErrorInfo', 'HeartbeatInfo',
    'TaskScheduler', 'TaskSchedulerManager', 'HeartbeatManager',
    'TaskPriority', 'TaskState', 'Task',
    'get_task_scheduler', 'get_heartbeat_manager',
    # Vision
    'VisionModule', 'get_vision_module',
    # Strategy
    'StrategyModule', 'get_strategy_module',
    # Actuator
    'CollectModule', 'get_collect_module',
    'PlaceModule', 'get_place_module',
    'BuildModule', 'get_build_module',
    # Hardware
    'PCA9685Driver', 'get_pca9685_driver',
    'MotorController', 'DCMotor', 'StepperMotor',
    'ServoController', 'GripperServo', 'ArmServo', 'ContinuousRotationServo',
    'GripperController', 'DualGripperController',
    'MotionController', 'OmniMotionController', 'ArmController',
]