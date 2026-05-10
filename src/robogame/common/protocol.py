from ..common.fsm import State
from ..common.types import Position, Block, BuildTarget
from ..common.error import ErrorCode


class Status:
    status_code: State
    result: str
    error_code: ErrorCode
    timestamp: float


class TaskCommand:
    module: str
    cmd: str
    target_pos: Position | None
    params: dict
    timeout: float