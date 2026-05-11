# RoboGame 下一步开发建议

这个文档中的内容有点过时，仅供参考。了解详情请阅读源码。

## 1. 项目当前状态概览

### 1.1 已完成模块

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| 有限状态机 | [fsm.py](file:///c:/Users/raymondzylei/Projects/robogame/src/robogame/common/fsm.py) | ✅ 完成 | State枚举、StateMachine类实现完整 |
| 错误码定义 | [error.py](file:///c:/Users/raymondzylei/Projects/robogame/src/robogame/common/error.py) | ✅ 完成 | ErrorCode枚举 |
| 任务调度器 | [scheduler.py](file:///c:/Users/raymondzylei/Projects/robogame/src/robogame/strategy/scheduler.py) | ⚠️ 基础 | TaskPhase枚举，基本框架 |
| 执行模块 | collect/place/build.py | ⚠️ 基础 | FSM骨架，条件全为占位符 |

### 1.2 待修复/待实现模块

| 模块 | 文件 | 状态 | 优先级 |
|------|------|------|--------|
| 模块间通信 | - | ❌ 未实现 | P1 |
| 串口通信 | - | ❌ 未实现 | P2 |
| 相机驱动 | [camera.py](file:///c:/Users/raymondzylei/Projects/robogame/src/robogame/vision/camera.py) | ❌ 空文件 | P2 |
| 目标检测 | [detector.py](file:///c:/Users/raymondzylei/Projects/robogame/src/robogame/vision/detector.py) | ❌ 存根 | P2 |
| 路径规划 | - | ❌ 未实现 | P2 |
---

## 3. P1 级：核心功能实现（当前重点）

### 3.1 模块间通信 - 消息总线设计

**为什么需要消息总线**：
- 解耦各模块（视觉、执行、策略不再直接依赖）
- 支持异步通信（状态更新不阻塞主循环）
- 便于扩展新模块
- 支持调试（可以监听任意消息）

#### 3.1.1 消息定义

```python
# src/robogame/common/msg.py
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
```

#### 3.1.2 消息总线实现

```python
# src/robogame/common/bus.py
import time
from typing import Callable, Any
from collections import defaultdict
from threading import Lock
from .msg import Message, MessageType


class MessageBus:
    """消息总线 - 核心通信枢纽"""

    def __init__(self):
        self._subscribers: dict[MessageType, list[Callable[[Message], None]]] = defaultdict(list)
        self._lock = Lock()
        self._message_history: list[Message] = []
        self._max_history = 1000

    def subscribe(self, msg_type: MessageType, callback: Callable[[Message], None]) -> None:
        """订阅特定类型消息"""
        with self._lock:
            self._subscribers[msg_type].append(callback)

    def unsubscribe(self, msg_type: MessageType, callback: Callable[[Message], None]) -> None:
        """取消订阅"""
        with self._lock:
            if callback in self._subscribers[msg_type]:
                self._subscribers[msg_type].remove(callback)

    def publish(self, message: Message) -> None:
        """发布消息"""
        message.timestamp = time.time()

        with self._lock:
            self._message_history.append(message)
            if len(self._message_history) > self._max_history:
                self._message_history.pop(0)

            callbacks = list(self._subscribers.get(message.type, []))

        for callback in callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Message callback error: {e}")

    def get_history(self, msg_type: MessageType | None = None, limit: int = 100) -> list[Message]:
        """获取消息历史"""
        with self._lock:
            if msg_type is None:
                return self._message_history[-limit:]
            return [m for m in self._message_history if m.type == msg_type][-limit:]


_bus: MessageBus | None = None


def get_bus() -> MessageBus:
    """获取全局消息总线单例"""
    global _bus
    if _bus is None:
        _bus = MessageBus()
    return _bus
```

#### 3.1.3 模块集成示例

```python
# src/robogame/actuator/collect/collect.py
from ..common.fsm import StateMachine, State
from ..common.bus import get_bus, MessageType, Message
from ..common.msg import ActionCompleteMsg, ActionStartedMsg


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
```

```python
# src/robogame/vision/vision_module.py
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
```

#### 3.1.4 主循环集成

```python
# src/robogame/main.py
import time
from .common.bus import get_bus, MessageType, Message
from .strategy import TaskScheduler
from .actuator import CollectModule, PlaceModule, BuildModule
from .vision import VisionModule


class RoboGame:
    """主程序"""

    def __init__(self):
        self.bus = get_bus()
        self.scheduler = TaskScheduler()
        self.collect = CollectModule(self.bus)
        self.place = PlaceModule(self.bus)
        self.build = BuildModule(self.bus)
        self.vision = VisionModule(self.bus)
        self._running = False
        self._setup_message_handlers()

    def _setup_message_handlers(self):
        self.bus.subscribe(MessageType.ERROR_REPORT, self._handle_error)

    def _handle_error(self, msg: Message):
        print(f"Error received: {msg.data}")

    def start(self):
        """启动系统"""
        self._running = True
        self.vision.start()
        self.bus.publish(Message(
            type=MessageType.TASK_START,
            sender="system",
            timestamp=0.0,
            data={"module": "collect"}
        ))

    def run_once(self):
        """执行一次主循环"""
        self.collect.update()
        self.place.update()
        self.build.update()

    def run(self):
        """主循环"""
        self.start()
        while self._running:
            self.run_once()
            time.sleep(0.01)


if __name__ == "__main__":
    game = RoboGame()
    game.run()
```

---

## 4. P2 级：后续功能

### 4.0 通信层次说明

```
┌─────────────────────────────────────────────────────┐
│                    树莓派 (Python)                   │
│  ┌─────────────┐   ┌─────────────┐   ┌───────────┐ │
│  │  策略模块   │ ← → │  执行模块   │ ← → │  视觉模块 │ │
│  └─────────────┘   └─────────────┘   └───────────┘ │
│         ↑                                        │
│         └────────── 消息总线 (bus.py) ──────────┘   │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │          protocol.py (Status/TaskCommand)   │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                          ↓ 串口 (uart.py)
┌─────────────────────────────────────────────────────┐
│                   STM32 (下位机)                     │
│  ┌─────────────┐   ┌─────────────┐   ┌───────────┐ │
│  │  电机控制   │   │  传感器读取  │   │  舵机控制 │ │
│  └─────────────┘   └─────────────┘   └───────────┘ │
└─────────────────────────────────────────────────────┘
```

- **消息总线**：模块间通信（P1）
- **protocol.py + uart.py**：上下位机通信（P2）

### 4.1 串口通信模块（暂不紧急）

> **说明**：消息总线用于**树莓派内部模块间通信**（软件层面），而 `protocol.py` 用于**树莓派与STM32下位机通信**（硬件层面）。两者层次不同，protocol.py 仍然需要实现。

**目标**：实现与STM32下位机的通信

```python
# src/robogame/common/uart.py
import serial
from typing import Callable
from .protocol import TaskCommand, Status
from .bus import get_bus, MessageType


class UARTComm:
    """串口通信模块"""

    def __init__(self, port: str = "COM3", baudrate: int = 115200):
        self.serial = serial.Serial(port, baudrate, timeout=0.1)
        self.bus = get_bus()
        self._running = False

    def send_command(self, cmd: TaskCommand) -> bool:
        """发送命令"""
        data = self._serialize_command(cmd)
        self.serial.write(data)
        return True

    def receive_status(self) -> Status | None:
        """接收状态"""
        if self.serial.in_waiting >= 10:
            data = self.serial.read(10)
            return self._deserialize_status(data)
        return None

    def close(self) -> None:
        self.serial.close()
```

**通信协议建议**：
- 指令格式：指令码(1字节) + 参数(n字节) + 校验位(1字节)
- 心跳：50Hz控制指令 / 100Hz状态反馈

### 4.2 视觉模块（暂不紧急）

```python
# src/robogame/vision/camera.py
import cv2
import numpy as np


class Camera:
    def __init__(self, device: int = 0):
        self.cap = cv2.VideoCapture(device)

    def read_frame(self) -> np.ndarray | None:
        ret, frame = self.cap.read()
        return frame if ret else None

    def release(self) -> None:
        self.cap.release()
```

### 4.3 路径规划模块

```python
# src/robogame/strategy/pathfinder.py
import numpy as np
from ..common.types import Position


class PathPlanner:
    """A*路径规划器"""

    def __init__(self, grid_size: tuple[int, int], resolution: float = 0.05):
        self.grid = np.zeros(grid_size, dtype=int)
        self.resolution = resolution

    def plan(self, start: Position, goal: Position) -> list[Position]:
        """A*路径规划"""
        ...
```

---

## 5. 测试框架

```python
# tests/test_bus.py
import pytest
import time
from robogame.common.bus import MessageBus, get_bus
from robogame.common.msg import Message, MessageType


def test_publish_subscribe():
    bus = MessageBus()
    received = []

    def handler(msg):
        received.append(msg)

    bus.subscribe(MessageType.HEARTBEAT, handler)

    msg = Message(MessageType.HEARTBEAT, "test", time.time(), {})
    bus.publish(msg)

    assert len(received) == 1
    assert received[0] is msg


def test_message_history():
    bus = MessageBus()
    for i in range(5):
        bus.publish(Message(MessageType.HEARTBEAT, "test", time.time(), {}))

    history = bus.get_history(limit=3)
    assert len(history) == 3
```

---

## 6. 依赖管理

```powershell
# 使用 uv 管理依赖
uv add pyserial

# 开发依赖
uv add --dev pytest
```

---

## 7. 技术债务清单

| 序号 | 问题 | 影响 | 修复建议 |
|------|------|------|----------|
| 1 | types.py循环导入 | 模块无法导入 | 立即修复 |
| 2 | 无模块间通信 | 模块紧耦合 | 实现消息总线 |
| 3 | 状态转换条件为占位符 | 状态机无实际功能 | 实现真实条件 |
| 4 | 无通信模块 | 无法控制硬件 | 实现UART通信（P2） |
| 5 | vision模块未实现 | 无法感知环境 | 实现视觉检测（P2） |
| 6 | 无路径规划 | 无法自主导航 | 实现A*算法（P2） |
| 7 | 测试文件为空 | 质量无保障 | 补充单元测试 |

---

## 8. 推荐开发顺序

```
P0: 修复types.py循环导入
    ↓
P1: 实现消息总线 → 集成消息发布/订阅 → 主循环集成
    ↓
P2: 实现UART通信 → 实现视觉检测 → 路径规划
    ↓
持续: 补充测试 → 性能优化
```

---

## 9. 开发里程碑

| 阶段 | 交付物 | 关键任务 |
|------|--------|----------|
| 0 | 可运行框架 | 修复types.py循环导入 |
| 1 | 消息总线 | msg.py + bus.py + 模块集成 |
| 2 | 完整流程 | 状态机条件 + 任务调度 |
| 3 | 通信链路 | UART驱动 + 协议解析 |
| 4 | 感知能力 | 相机驱动 + 目标检测 |
| 5 | 集成测试 | 完整流程测试 + 调优 |
