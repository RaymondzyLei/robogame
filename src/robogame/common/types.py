"""通用数据类型定义"""
from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class Position:
    """位置坐标"""
    x: float
    y: float
    z: float = 0.0


@dataclass
class Pose:
    """机器人位姿"""
    x: float
    y: float
    z: float
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0


@dataclass
class CubeInfo:
    """方块信息"""
    cube_id: int
    position: Position
    pose: Optional[Pose] = None
    detected: bool = False


@dataclass
class StatusCode:
    """状态码定义"""
    INIT = 0
    NAVIGATE = 1
    ACTION = 2
    COMPLETE = 3
    ERROR = -1


@dataclass
class ErrorCode:
    """错误码定义"""
    NONE = 0
    VISION_FAIL = 1
    NAVIGATION_FAIL = 2
    ACTION_FAIL = 3
    COMMUNICATION_FAIL = 4
    TIMEOUT = 5


@dataclass
class ModuleStatus:
    """模块状态"""
    code: int
    msg: str
    error_code: int = ErrorCode.NONE

    def to_dict(self):
        return {
            'code': self.code,
            'msg': self.msg,
            'error_code': self.error_code
        }


@dataclass
class TaskParam:
    """任务参数"""
    target_position: Position
    threshold: float = 5.0
    cube_id: Optional[int] = None

    def to_dict(self):
        return {
            'target_position': {
                'x': self.target_position.x,
                'y': self.target_position.y,
                'z': self.target_position.z
            },
            'threshold': self.threshold,
            'cube_id': self.cube_id
        }


@dataclass
class ErrorInfo:
    """错误信息"""
    error_code: int
    error_type: str
    desc: str
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self):
        return {
            'error_code': self.error_code,
            'error_type': self.error_type,
            'desc': self.desc,
            'timestamp': self.timestamp
        }


@dataclass
class HeartbeatInfo:
    """心跳信息"""
    module_name: str
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self):
        return {
            'module_name': self.module_name,
            'timestamp': self.timestamp
        }