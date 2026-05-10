from ..common.fsm import StateMachine, State


class PlaceModule:
    """放置方块模块"""

    def __init__(self):
        self.fsm = StateMachine("place")
        self._setup_fsm()

    def _setup_fsm(self):
        self.fsm.add_transition(State.INIT, State.NAVIGATE, lambda: True)
        self.fsm.add_transition(State.NAVIGATE, State.EXECUTE, lambda: True)
        self.fsm.add_transition(State.EXECUTE, State.FINISH, lambda: True)

    def update(self) -> State:
        return self.fsm.update()

    def reset(self) -> None:
        self.fsm.reset()