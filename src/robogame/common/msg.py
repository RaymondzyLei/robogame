from dataclasses import dataclass
from enum import IntEnum
from .types import Position, Block


class MessageType(IntEnum):
    # 视觉模块 -> 策略/执行
    BLOCKS_DETECTED = 1
    TARGET_DETECTED = 2
    ROBOT_POSE_UPDATED = 3

    # 执行模块 -> 策略/视觉
    NAVIGATION_STARTED = 10
    NAVIGATION_COMPLETE = 11
    NAVIGATION_FAILED = 12
    ACTION_STARTED = 13
    ACTION_COMPLETE = 14
    ACTION_FAILED = 15

    # 策略模块 -> 执行
    TASK_START = 20
    TASK_CANCEL = 21
    TASK_PHASE_CHANGE = 22

    # 系统
    HEARTBEAT = 100
    ERROR_REPORT = 101


@dataclass
class Message:
    """通用消息"""
    type: MessageType
    sender: str
    timestamp: float
    data: dict


@dataclass
class BlocksDetectedMsg(Message):
    """方块检测结果"""
    def __init__(self, blocks: list[Block]):
        super().__init__(
            type=MessageType.BLOCKS_DETECTED,
            sender="vision",
            timestamp=0.0,
            data={"blocks": blocks}
        )


@dataclass
class RobotPoseMsg(Message):
    """机器人位姿更新"""
    def __init__(self, pose: Position):
        super().__init__(
            type=MessageType.ROBOT_POSE_UPDATED,
            sender="vision",
            timestamp=0.0,
            data={"pose": pose}
        )


@dataclass
class ActionCompleteMsg(Message):
    """动作执行完成"""
    def __init__(self, module: str, success: bool, error_code: int = 0):
        super().__init__(
            type=MessageType.ACTION_COMPLETE,
            sender=module,
            timestamp=0.0,
            data={"success": success, "error_code": error_code}
        )