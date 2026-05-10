from ..common.types import Position, Block


class VisionModule:
    """视觉模块"""

    def detect_blocks(self) -> list[Block]:
        raise NotImplementedError

    def detect_target(self) -> Position | None:
        raise NotImplementedError

    def get_robot_pose(self) -> Position | None:
        raise NotImplementedError