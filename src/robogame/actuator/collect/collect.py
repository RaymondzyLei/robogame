from ...common.fsm import StateMachine, State
from ...common.bus import get_bus, MessageType, Message
from ...common.msg import ActionCompleteMsg, ActionStartedMsg


class CollectModule:
    """收集方块模块"""

    def __init__(self, bus=None):
        self.bus = bus or get_bus()
        self.fsm = StateMachine("collect")
        self._target_block = None
        self._setup_subscriptions()
        self._setup_fsm()

    def _setup_subscriptions(self):
        """订阅相关消息"""
        self.bus.subscribe(MessageType.TASK_START, self._on_task_start)
        self.bus.subscribe(MessageType.BLOCKS_DETECTED, self._on_blocks_detected)

    def _on_task_start(self, msg: Message):
        """收到任务开始消息"""
        if msg.data.get("module") == "collect":
            self.reset()
            self.bus.publish(Message(
                type=MessageType.NAVIGATION_STARTED,
                sender="collect",
                timestamp=0.0,
                data={}
            ))

    def _on_blocks_detected(self, msg: Message):
        """收到方块检测结果"""
        blocks = msg.data.get("blocks", [])
        if blocks and self.fsm.get_state() == State.INIT:
            self._target_block = blocks[0]

    def _setup_fsm(self):
        self.fsm.add_transition(State.INIT, State.NAVIGATE, lambda: self._check_target_found())
        self.fsm.add_transition(State.NAVIGATE, State.EXECUTE, lambda: True)
        self.fsm.add_transition(State.EXECUTE, State.FINISH, lambda: True)

    def _check_target_found(self) -> bool:
        return self._target_block is not None

    def update(self) -> State:
        old_state = self.fsm.get_state()
        new_state = self.fsm.update()

        if old_state != new_state:
            self.bus.publish(ActionCompleteMsg(
                module="collect",
                success=True
            ))

        return new_state

    def reset(self) -> None:
        self.fsm.reset()
        self._target_block = None