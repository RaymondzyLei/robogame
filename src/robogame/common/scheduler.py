"""动态任务调度器 - 支持任务优先级、抢占、中断恢复"""
import threading
import time
import uuid
from typing import Optional, List, Dict, Any
from enum import Enum
from blinker import signal

from ..common.datahub import get_datahub
from ..common.events import DataHubEvent, StrategyEvent, ModuleEvent


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskState(Enum):
    """任务状态"""
    PENDING = 'pending'
    RUNNING = 'running'
    SUSPENDED = 'suspended'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class Task:
    """任务单元"""

    def __init__(self, task_id: str, task_type: str, target: Dict[str, Any],
                 priority: TaskPriority = TaskPriority.NORMAL, cube_id: Optional[int] = None):
        self.task_id = task_id
        self.task_type = task_type  # 'collect', 'place', 'build'
        self.target = target
        self.priority = priority
        self.cube_id = cube_id
        self.state = TaskState.PENDING
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.result: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'target': self.target,
            'priority': self.priority.value,
            'cube_id': self.cube_id,
            'state': self.state.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at
        }


class TaskScheduler:
    """动态任务调度器，支持优先级、抢占、中断恢复"""

    def __init__(self):
        self._datahub = get_datahub()
        self._tasks: Dict[str, Task] = {}
        self._task_queue: List[Task] = []
        self._running_task: Optional[Task] = None
        self._task_lock = threading.Lock()

        # 任务事件信号
        self._task_created_signal = signal('scheduler:task_created')
        self._task_started_signal = signal('scheduler:task_started')
        self._task_completed_signal = signal('scheduler:task_completed')
        self._task_cancelled_signal = signal('scheduler:task_cancelled')
        self._task_interrupted_signal = signal('scheduler:task_interrupted')

        self._setup_listeners()

    def _setup_listeners(self):
        """设置事件监听"""
        ack_signal = signal('datahub:ack')
        ack_signal.connect(self._handle_ack)

        safety_signal = signal('datahub:safety_shutdown')
        safety_signal.connect(self._handle_safety_shutdown)

    def _handle_ack(self, sender, request_id: str, key: str, success: bool):
        """处理ACK事件"""
        pass

    def _handle_safety_shutdown(self, sender, module: str):
        """处理安全停机事件"""
        self.suspend_current_task('safety_shutdown')
        print(f"[TaskScheduler] Safety shutdown, current task suspended")

    def create_task(self, task_type: str, target: Dict[str, Any],
                    priority: TaskPriority = TaskPriority.NORMAL,
                    cube_id: Optional[int] = None) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        task = Task(task_id, task_type, target, priority, cube_id)

        with self._task_lock:
            self._tasks[task_id] = task
            self._insert_task_queue(task)

        self._task_created_signal.send(self, task_id=task_id, task_type=task_type)
        print(f"[TaskScheduler] Created task: {task_id}, type={task_type}, priority={priority.name}")

        # 自动尝试执行
        self.try_execute_next()
        return task_id

    def _insert_task_queue(self, task: Task):
        """按优先级插入任务队列"""
        inserted = False
        for i, existing_task in enumerate(self._task_queue):
            if task.priority.value > existing_task.priority.value:
                self._task_queue.insert(i, task)
                inserted = True
                break
        if not inserted:
            self._task_queue.append(task)

    def try_execute_next(self):
        """尝试执行下一个任务"""
        with self._task_lock:
            if self._running_task:
                return False

            if not self._task_queue:
                return False

            task = self._task_queue.pop(0)
            self._running_task = task
            task.state = TaskState.RUNNING
            task.started_at = time.time()

        self._execute_task(task)
        return True

    def _execute_task(self, task: Task):
        """执行任务"""
        print(f"[TaskScheduler] Executing task: {task.task_id}, type={task.task_type}")

        # 写入任务参数到DataHub
        param_key = f'strategy:{task.task_type}_param'
        param_value = {
            'target_position': task.target,
            'priority': task.priority.value,
            'cube_id': task.cube_id,
            'task_id': task.task_id
        }
        self._datahub.write(param_key, param_value)

        # 发送启动事件
        event_map = {
            'collect': StrategyEvent.START_COLLECT,
            'place': StrategyEvent.START_PLACE,
            'build': StrategyEvent.START_BUILD
        }

        if task.task_type in event_map:
            start_signal = signal(event_map[task.task_type].value)
            start_signal.send(self, request_id=task.task_id, data_key=param_key)

        self._task_started_signal.send(self, task_id=task.task_id)

    def on_task_complete(self, task_id: str, result: Dict[str, Any]):
        """任务完成回调"""
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task:
                task.state = TaskState.COMPLETED
                task.completed_at = time.time()
                task.result = result
                if self._running_task and self._running_task.task_id == task_id:
                    self._running_task = None

        self._task_completed_signal.send(self, task_id=task_id, result=result)
        print(f"[TaskScheduler] Task completed: {task_id}")

        # 尝试执行下一个任务
        self.try_execute_next()

    def preempt_task(self, new_task_type: str, new_target: Dict[str, Any],
                     new_priority: TaskPriority, cube_id: Optional[int] = None) -> bool:
        """抢占式调度，新任务中断当前任务"""
        with self._task_lock:
            if self._running_task:
                current_task = self._running_task
                current_task.state = TaskState.SUSPENDED

                # 保存中断点
                self._datahub.write('scheduler:suspend_point', {
                    'task_id': current_task.task_id,
                    'task_type': current_task.task_type,
                    'state': current_task.state.value,
                    'timestamp': time.time()
                })

                print(f"[TaskScheduler] Preempting task: {current_task.task_id}")

                # 创建新任务
                new_task_id = self.create_task(new_task_type, new_target, new_priority, cube_id)

                self._task_interrupted_signal.send(self,
                                                   interrupted_task_id=current_task.task_id,
                                                   new_task_id=new_task_id)
                return True

            # 没有运行中的任务，直接创建
            self.create_task(new_task_type, new_target, new_priority, cube_id)
            return True

    def suspend_current_task(self, reason: str = 'manual'):
        """挂起当前任务"""
        with self._task_lock:
            if self._running_task:
                task = self._running_task
                task.state = TaskState.SUSPENDED

                self._datahub.write('scheduler:suspend_point', {
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'reason': reason,
                    'timestamp': time.time()
                })

                self._running_task = None
                print(f"[TaskScheduler] Task suspended: {task.task_id}, reason={reason}")
                return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """恢复被挂起的任务"""
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task and task.state == TaskState.SUSPENDED:
                self._task_queue.insert(0, task)
                task.state = TaskState.PENDING
                print(f"[TaskScheduler] Task resumed: {task_id}")
                self.try_execute_next()
                return True
        return False

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._task_lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.state == TaskState.RUNNING:
                self._running_task = None

            if task in self._task_queue:
                self._task_queue.remove(task)

            task.state = TaskState.CANCELLED
            self._task_cancelled_signal.send(self, task_id=task_id)
            print(f"[TaskScheduler] Task cancelled: {task_id}")
            return True

    def switch_target(self, task_id: str, new_target: Dict[str, Any]):
        """切换任务目标（如切换目标方块）"""
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task and task.state in [TaskState.PENDING, TaskState.RUNNING]:
                old_target = task.target
                task.target = new_target

                # 如果任务正在运行，发送目标更新事件
                if task.state == TaskState.RUNNING:
                    self._datahub.write(f'strategy:{task.task_type}_param', {
                        'target_position': new_target,
                        'priority': task.priority.value,
                        'cube_id': task.cube_id,
                        'task_id': task.task_id,
                        'target_switched': True,
                        'old_target': old_target
                    })
                    print(f"[TaskScheduler] Target switched for task: {task_id}")
                return True
        return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self._task_lock:
            task = self._tasks.get(task_id)
            return task.to_dict() if task else None

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """获取待执行任务列表"""
        with self._task_lock:
            return [t.to_dict() for t in self._task_queue]

    def get_running_task(self) -> Optional[Dict[str, Any]]:
        """获取当前运行中的任务"""
        with self._task_lock:
            return self._running_task.to_dict() if self._running_task else None

    def recover_interrupted(self):
        """恢复中断的任务"""
        suspend_point = self._datahub.get('scheduler:suspend_point')
        if suspend_point:
            task_id = suspend_point.get('task_id')
            if task_id:
                print(f"[TaskScheduler] Recovering interrupted task: {task_id}")
                self.resume_task(task_id)


class HeartbeatManager:
    """心跳管理器 - 负责发送和监控模块心跳"""

    def __init__(self, module_name: str):
        self._module_name = module_name
        self._datahub = get_datahub()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._heartbeat_signal = signal(ModuleEvent.HEARTBEAT.value)

    def start(self):
        """启动心跳"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        print(f"[HeartbeatManager] {self._module_name} started")

    def stop(self):
        """停止心跳"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _heartbeat_loop(self):
        """心跳循环"""
        interval = 1.0  # 每秒发送
        while self._running:
            try:
                self._datahub.update_heartbeat(self._module_name)

                self._heartbeat_signal.send(self, module=self._module_name, timestamp=time.time())

                time.sleep(interval)
            except Exception as e:
                print(f"[HeartbeatManager] Error: {e}")

    def send_heartbeat(self):
        """手动发送心跳"""
        self._datahub.update_heartbeat(self._module_name)
        self._heartbeat_signal.send(self, module=self._module_name, timestamp=time.time())


class TaskSchedulerManager:
    """任务调度器管理器（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._scheduler = TaskScheduler()

    def get_scheduler(self) -> TaskScheduler:
        """获取任务调度器"""
        return self._scheduler


def get_task_scheduler() -> TaskScheduler:
    """获取任务调度器单例"""
    manager = TaskSchedulerManager()
    return manager.get_scheduler()


def get_heartbeat_manager(module_name: str) -> HeartbeatManager:
    """获取心跳管理器"""
    return HeartbeatManager(module_name)