from dataclasses import dataclass
from typing import Callable, Optional
from enum import IntEnum


class State(IntEnum):
    INIT = 0          # 初始化定位
    NAVIGATE = 1      # 导航到目标
    EXECUTE = 2       # 动作执行
    FINISH = 3        # 结束状态
    ERROR = -1        # 异常处理


@dataclass
class StateTransition:
    from_state: State
    to_state: State
    condition: Callable[[], bool]


class StateMachine:
    def __init__(self, name: str):
        self.name = name
        self.current_state = State.INIT
        self.transitions: list[StateTransition] = []
        self.on_state_change: Optional[Callable[[State, State], None]] = None

    def add_transition(self, from_state: State, to_state: State,
                       condition: Callable[[], bool]) -> None:
        self.transitions.append(StateTransition(from_state, to_state, condition))

    def update(self) -> State:
        for trans in self.transitions:
            if trans.from_state == self.current_state and trans.condition():
                old_state = self.current_state
                self.current_state = trans.to_state
                if self.on_state_change:
                    self.on_state_change(old_state, trans.to_state)
                break
        return self.current_state

    def get_state(self) -> State:
        return self.current_state

    def reset(self) -> None:
        self.current_state = State.INIT