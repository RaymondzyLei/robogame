from enum import IntEnum


class TaskPhase(IntEnum):
    COLLECT = 0
    PLACE = 1
    BUILD = 2
    IDLE = 3


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self.current_phase = TaskPhase.IDLE
        self.task_queue: list[TaskPhase] = []

    def start_collect(self) -> None:
        self.current_phase = TaskPhase.COLLECT

    def start_place(self) -> None:
        self.current_phase = TaskPhase.PLACE

    def start_build(self) -> None:
        self.current_phase = TaskPhase.BUILD

    def next_phase(self) -> TaskPhase:
        if self.current_phase == TaskPhase.COLLECT:
            self.current_phase = TaskPhase.PLACE
        elif self.current_phase == TaskPhase.PLACE:
            self.current_phase = TaskPhase.BUILD
        elif self.current_phase == TaskPhase.BUILD:
            self.current_phase = TaskPhase.IDLE
        return self.current_phase

    def get_current_phase(self) -> TaskPhase:
        return self.current_phase