"""Dynamic task scheduler skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from queue import PriorityQueue
from time import time
from typing import Any

from robogame.communication.bus import new_request_id


class TaskPriority(IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


@dataclass(order=True)
class ScheduledTask:
    sort_index: tuple[int, float] = field(init=False, repr=False)
    priority: TaskPriority
    created_at: float
    task_id: str
    task_type: str
    target: dict[str, Any]
    cube_id: int | None = None
    state: TaskState = TaskState.PENDING
    result: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.sort_index = (-int(self.priority), self.created_at)


class TaskScheduler:
    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self._queue: PriorityQueue[ScheduledTask] = PriorityQueue()
        self.current_task: ScheduledTask | None = None

    def create_task(
        self,
        task_type: str,
        target: dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        cube_id: int | None = None,
    ) -> str:
        task = ScheduledTask(priority, time(), new_request_id("task"), task_type, target, cube_id)
        self._tasks[task.task_id] = task
        self._queue.put(task)
        return task.task_id

    def next_task(self) -> ScheduledTask | None:
        if self.current_task and self.current_task.state == TaskState.RUNNING:
            return self.current_task
        while not self._queue.empty():
            task = self._queue.get()
            if task.state == TaskState.PENDING:
                task.state = TaskState.RUNNING
                self.current_task = task
                return task
        return None

    def preempt_task(self, task_type: str, target: dict[str, Any], priority: TaskPriority, cube_id: int | None = None) -> str:
        if self.current_task and self.current_task.state == TaskState.RUNNING:
            self.suspend_current_task("preempted")
        return self.create_task(task_type, target, priority, cube_id)

    def switch_target(self, task_id: str, target: dict[str, Any]) -> None:
        self._tasks[task_id].target = target

    def suspend_current_task(self, reason: str) -> None:
        if not self.current_task:
            return
        self.current_task.state = TaskState.SUSPENDED
        self.current_task.result = {"reason": reason}
        self.current_task = None

    def resume_task(self, task_id: str) -> None:
        task = self._tasks[task_id]
        task.state = TaskState.PENDING
        self._queue.put(task)

    def on_task_complete(self, task_id: str, result: dict[str, Any]) -> None:
        task = self._tasks[task_id]
        task.state = TaskState.COMPLETED
        task.result = result
        if self.current_task and self.current_task.task_id == task_id:
            self.current_task = None


_default_scheduler = TaskScheduler()


def get_task_scheduler() -> TaskScheduler:
    return _default_scheduler
