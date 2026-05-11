from ..common.bus import get_bus, MessageType
from ..common.msg import BlocksDetectedMsg, RobotPoseMsg
from ..common.types import Position


class VisionModule:
    """视觉模块 - 消息发布者"""

    def __init__(self, bus=None):
        self.bus = bus or get_bus()
        self._running = False

    def start(self):
        """启动视觉检测"""
        self._running = True

    def stop(self):
        """停止视觉检测"""
        self._running = False

    def detect_and_publish(self, frame) -> None:
        """检测并发布消息"""
        if not self._running:
            return

        blocks = self.detect_blocks(frame)
        if blocks:
            self.bus.publish(BlocksDetectedMsg(blocks))

        pose = self.get_robot_pose(frame)
        if pose:
            self.bus.publish(RobotPoseMsg(pose))

    def detect_blocks(self, frame):
        raise NotImplementedError

    def get_robot_pose(self, frame) -> Position | None:
        raise NotImplementedError