# RoboGame 通信机制用户指南

## 目录

1. [概述](#1-概述)
2. [核心概念](#2-核心概念)
3. [快速开始](#3-快速开始)
4. [DataHub 使用教程](#4-datahub-使用教程)
5. [Blinker 事件使用教程](#5-blinker-事件使用教程)
6. [模块间通信实战](#6-模块间通信实战)
7. [常见问题](#7-常见问题)
8. [API 参考](#8-api-参考)
9. [高级功能](#9-高级功能)

---

## 1. 概述

### 1.1 这套通信机制是什么？

RoboGame 系统由多个模块组成：
- **视觉模块**：负责"看"——识别方块位置、机器人位姿等
- **策略模块**：负责"想"——决定下一步做什么
- **执行模块**：负责"做"——控制机械臂移动、抓取、放置等

这些模块就像一个团队，需要互相沟通：
- 视觉模块看到方块位置后，要告诉策略模块
- 策略模块做出决策后，要告诉执行模块该动哪里
- 执行模块完成动作后，要反馈给策略模块

**我们的通信机制就是让这些模块能够安全、快速地互相传递信息。**

### 1.2 为什么选择 Blinker？

Blinker 是一个轻量级的事件通信库，它的核心特点是：

1. **不需要直接调用**：模块 A 想告诉模块 B 什么事情，不需要直接写 `B.receive()`，只需要发送一个"事件"
2. **线程安全**：多个模块同时通信不会出问题
3. **简单易用**：几行代码就能实现复杂的通信

### 1.3 通信的整体架构

```
                    ┌─────────────────────────────────────┐
                    │           Blinker 消息总线           │
                    │    (所有模块通过它来传递信息)          │
                    └─────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
    ┌───────────┐            ┌───────────┐            ┌───────────┐
    │  视觉模块  │            │  策略模块  │            │  执行模块  │
    └───────────┘            └───────────┘            └───────────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │        DataHub 数据中心        │
                    │    (存储所有模块共享的数据)      │
                    └───────────────────────────────┘
```

**数据流**：
- 所有模块不直接读写 DataHub，而是发送"写事件"或"读事件"
- DataHub 监听这些事件，完成实际的数据操作
- 数据准备好后，DataHub 发送"返回事件"给请求的模块

---

## 2. 核心概念

在开始编程之前，你需要理解三个核心概念：

### 2.1 事件（Event）

**什么是事件？**

事件就像生活中的"通知"。比如：
- 上课铃响 → 学生知道该去教室了
- 手机震动 → 你知道收到消息了

在我们的系统里，事件就是模块之间互相发送的"通知"。

**事件的组成**：
- **名称**：比如 `start_collect`（开始收集）
- **数据**：通知里包含的信息，比如目标位置、状态等

### 2.2 信号（Signal）

**什么是信号？**

信号是用来发送事件的工具。你可以把它想象成：
- 广播站 → 发送事件（广播）
- 收音机 → 监听事件（接收）

**如何使用**：

```python
from blinker import signal

# 创建一个信号（相当于建立一个广播频道）
my_signal = signal('my_event')

# 发送事件（广播）
my_signal.send(None, message="Hello!")

# 监听事件（接收）
def handle_message(sender, message):
    print(f"收到消息: {message}")

my_signal.connect(handle_message)
```

### 2.3 DataHub

**什么是 DataHub？**

DataHub 是一个数据仓库，存储所有模块共享的数据。

**为什么要通过事件来访问它？**

直接访问的问题：如果模块 A 正在读数据，同时模块 B 在写数据，可能会出错。

通过事件访问的好处：DataHub 自己管理锁，保证同一时间只有一个模块在操作数据。

**DataHub 支持的操作**：
- **写入数据**：`datahub:write` 事件
- **读取数据**：`datahub:read` 事件
- **接收返回**：`datahub:data_return` 事件

---

## 3. 快速开始

### 3.1 环境准备

确保你已经安装了依赖：

```bash
uv add blinker
```

### 3.2 最简单的例子

让我们从一个最简单的例子开始：**发送一个事件并接收它**。

```python
from blinker import signal

# 1. 创建一个信号
start_signal = signal('robot:start')

# 2. 定义处理函数（当事件发生时会调用这个函数）
def on_robot_start(sender, task_id):
    print(f"机器人开始执行任务 {task_id}")

# 3. 订阅这个信号（让系统知道这个函数要响应这个事件）
start_signal.connect(on_robot_start)

# 4. 发送事件（触发所有订阅了这个信号的函数）
start_signal.send(None, task_id=123)
# 输出: 机器人开始执行任务 123
```

### 3.3 两个模块之间通信

假设我们有两个模块：**传感器模块** 和 **控制模块**。

传感器检测到障碍物后，要通知控制模块。

```python
from blinker import signal

# ===== 传感器模块 =====

# 创建一个信号，用于发送障碍物信息
obstacle_signal = signal('sensor:obstacle')

def send_obstacle_info(x, y):
    """发送障碍物信息"""
    obstacle_signal.send(
        None,
        position={'x': x, 'y': y},
        distance=50
    )

# ===== 控制模块 =====

# 订阅障碍物信号
def handle_obstacle(sender, position, distance):
    print(f"检测到障碍物! 位置: {position}, 距离: {distance}cm")
    # 控制机器人停止或绕行
    print("机器人停止!")

obstacle_signal.connect(handle_obstacle)

# ===== 测试 =====
# 传感器检测到障碍物
send_obstacle_info(100, 200)
# 输出:
# 检测到障碍物! 位置: {'x': 100, 'y': 200}, 距离: 50cm
# 机器人停止!
```

### 3.4 完整的数据读写流程

现在让我们看看如何通过 DataHub 读写数据：

```python
import time
from blinker import signal

import sys
sys.path.insert(0, 'src')

from robogame.common.datahub import get_datahub
from robogame.common.events import DataHubEvent

# 获取 DataHub（数据仓库）
datahub = get_datahub()

# ===== 写入数据 =====

# 发送写入事件，通知 DataHub 保存数据
datahub.write('robot:position', {'x': 100, 'y': 200, 'z': 0})

# ===== 读取数据 =====

# 订阅数据返回事件
def on_data_return(sender, request_id, key, value):
    print(f"收到数据! key={key}, value={value}")

signal(DataHubEvent.DATA_RETURN.value).connect(on_data_return)

# 发送读取事件，通知 DataHub 返回数据
request_id = datahub.read('robot:position')

# 等待数据返回（约 0.01ms）
time.sleep(0.1)

# 输出: 收到数据! key=robot:position, value={'x': 100, 'y': 200, 'z': 0}
```

---

## 4. DataHub 使用教程

### 4.1 什么是 DataHub？

DataHub 是一个全局数据存储中心。所有模块需要保存或读取数据时，都要通过 DataHub。

**关键原则**：
- 不要直接读写 DataHub
- 通过发送事件来操作 DataHub
- DataHub 会线程安全地管理所有数据

### 4.2 写入数据

当你需要保存数据时，使用 `write` 方法：

```python
datahub = get_datahub()

# 写入方块位置
datahub.write('vision:cube_position', {
    'cube_id': 1,
    'x': 100,
    'y': 200,
    'z': 50
})

# 写入机器人位姿
datahub.write('robot:pose', {
    'x': 50,
    'y': 60,
    'yaw': 45
})

# 写入模块状态
datahub.write('collect:status', {
    'code': 1,
    'msg': 'navigating'
})
```

### 4.3 读取数据

当你需要获取数据时，使用 `read` 方法：

```python
datahub = get_datahub()

# 先订阅数据返回事件
def handle_data_return(sender, request_id, key, value):
    print(f"收到数据: {value}")

signal(DataHubEvent.DATA_RETURN.value).connect(handle_data_return)

# 发送读取请求
request_id = datahub.read('vision:cube_position')

# 等待数据返回
import time
time.sleep(0.1)  # 实际上很短，这里只是演示需要等待
```

### 4.4 实际使用场景

#### 场景 1：视觉模块报告方块位置

```python
from blinker import signal
from robogame.common.datahub import get_datahub
from robogame.common.events import VisionEvent

datahub = get_datahub()

def report_cube_position(cube_id, x, y, z):
    """报告方块位置给策略模块"""

    # 1. 写入数据到 DataHub
    cube_data = {
        'cube_id': cube_id,
        'position': {'x': x, 'y': y, 'z': z},
        'timestamp': time.time()
    }
    datahub.write('vision:cube_position', cube_data)

    # 2. 发送数据更新事件，通知策略模块
    data_updated_signal = signal(VisionEvent.DATA_UPDATED.value)
    data_updated_signal.send(
        None,
        request_id='req_001',
        data_key='vision:cube_position'
    )
```

#### 场景 2：策略模块获取视觉数据

```python
from blinker import signal
from robogame.common.datahub import get_datahub
from robogame.common.events import DataHubEvent

datahub = get_datahub()
pending_reads = {}  # 存储待处理的读取请求

def on_data_return(sender, request_id, key, value):
    """处理返回的数据"""
    if request_id in pending_reads:
        callback = pending_reads.pop(request_id)
        callback(value)

# 订阅数据返回事件
signal(DataHubEvent.DATA_RETURN.value).connect(on_data_return)

def get_cube_position(callback):
    """获取方块位置的辅助函数"""
    request_id = datahub.read('vision:cube_position')
    pending_reads[request_id] = callback

# 使用
def handle_cube_position(data):
    print(f"方块位置: {data}")

get_cube_position(handle_cube_position)
```

### 4.5 数据键命名规范

为了避免不同模块之间的命名冲突，我们使用统一的命名规范：

```
{模块}:{数据类型}
```

| 数据键 | 说明 |
|--------|------|
| `vision:cube_position` | 视觉模块报告的方块位置 |
| `vision:check_result` | 视觉模块的校验结果 |
| `strategy:collect_param` | 策略模块发给收集模块的参数 |
| `collect:status` | 收集模块的状态 |
| `place:status` | 放置模块的状态 |
| `build:status` | 搭建模块的状态 |
| `module:error_info` | 模块的错误信息 |

---

## 5. Blinker 事件使用教程

### 5.1 事件类型总览

我们的系统定义了以下几类事件：

**DataHub 交互事件**：
| 事件名 | 说明 |
|--------|------|
| `datahub:write` | 写入数据到 DataHub |
| `datahub:read` | 从 DataHub 读取数据 |
| `datahub:data_return` | DataHub 返回数据 |

**业务事件**：
| 事件名 | 说明 |
|--------|------|
| `vision:data_updated` | 视觉数据已更新 |
| `strategy:start_collect` | 启动收集模块 |
| `collect:status_updated` | 收集模块状态更新 |
| `place:status_updated` | 放置模块状态更新 |
| `build:status_updated` | 搭建模块状态更新 |
| `module:exception` | 模块发生异常 |

### 5.2 发送业务事件

业务事件用于模块之间的逻辑联动。

**例 1：策略模块启动收集模块**

```python
from blinker import signal
from robogame.common.events import StrategyEvent

# 获取信号
start_collect_signal = signal(StrategyEvent.START_COLLECT.value)

# 发送事件
start_collect_signal.send(
    None,
    request_id='req_123',
    data_key='strategy:collect_param'
)
```

**例 2：收集模块报告状态**

```python
from blinker import signal
from robogame.common.events import CollectEvent

# 获取信号
status_signal = signal(CollectEvent.STATUS_UPDATED.value)

# 发送状态更新
status_signal.send(
    None,
    request_id='req_456',
    data_key='collect:status'
)
```

### 5.3 订阅业务事件

**例：收集模块监听启动事件**

```python
from blinker import signal
from robogame.common.events import StrategyEvent, DataHubEvent

# 1. 定义处理函数
def on_start_collect(sender, request_id, data_key):
    print(f"收到启动收集模块的指令!")
    # 获取参数
    datahub = get_datahub()
    datahub.read(data_key, request_id)

# 2. 订阅事件
start_collect_signal = signal(StrategyEvent.START_COLLECT.value)
start_collect_signal.connect(on_start_collect)

# 3. 发送测试事件
start_collect_signal.send(None, request_id='test', data_key='strategy:collect_param')
```

### 5.4 订阅数据返回事件

当你发送 `datahub:read` 请求后，需要监听 `datahub:data_return` 事件来获取数据：

```python
from blinker import signal
from robogame.common.events import DataHubEvent

# 存储待处理的读取请求
pending_callbacks = {}

def on_data_return(sender, request_id, key, value):
    """处理所有数据返回"""
    if request_id in pending_callbacks:
        callback = pending_callbacks.pop(request_id)
        callback(value)

# 订阅数据返回事件
signal(DataHubEvent.DATA_RETURN.value).connect(on_data_return)

def read_data(key, callback):
    """读取数据的辅助函数"""
    datahub = get_datahub()
    request_id = datahub.read(key)
    pending_callbacks[request_id] = callback

# 使用
def handle_cube_data(data):
    print(f"收到方块数据: {data}")

read_data('vision:cube_position', handle_cube_data)
```

---

## 6. 模块间通信实战

### 6.1 视觉模块 → 策略模块

**流程**：视觉模块发现方块 → 通知策略模块 → 策略模块读取数据

```python
# ===== 视觉模块 =====
import time
from blinker import signal
from robogame.common.datahub import get_datahub
from robogame.common.events import VisionEvent

datahub = get_datahub()

def report_cube_detected(cube_id, x, y):
    """报告检测到的方块"""

    # 1. 写入方块数据
    cube_data = {
        'cube_id': cube_id,
        'x': x,
        'y': y,
        'detected': True,
        'timestamp': time.time()
    }
    datahub.write('vision:cube_position', cube_data)

    # 2. 发送数据更新事件
    signal(VisionEvent.DATA_UPDATED.value).send(
        None,
        request_id=f'req_{cube_id}',
        data_key='vision:cube_position'
    )

# ===== 策略模块 =====
from robogame.common.events import VisionEvent

def on_vision_data_updated(sender, request_id, data_key):
    """处理视觉数据更新"""
    print(f"视觉数据已更新: {data_key}")

    # 读取数据
    def handle_data(data):
        print(f"方块位置: x={data['x']}, y={data['y']}")

    read_data(data_key, handle_data)

signal(VisionEvent.DATA_UPDATED.value).connect(on_vision_data_updated)
```

### 6.2 策略模块 → 执行模块

**流程**：策略模块决定要收集 → 写入参数 → 发送启动事件 → 执行模块读取参数

```python
# ===== 策略模块 =====
import time
from blinker import signal
from robogame.common.datahub import get_datahub
from robogame.common.events import StrategyEvent

datahub = get_datahub()

def start_collect_module(target_x, target_y):
    """启动收集模块"""

    # 1. 写入收集参数
    collect_param = {
        'target_position': {'x': target_x, 'y': target_y},
        'threshold': 5,
        'timestamp': time.time()
    }
    datahub.write('strategy:collect_param', collect_param)

    # 2. 发送启动事件
    signal(StrategyEvent.START_COLLECT.value).send(
        None,
        request_id='req_start_collect',
        data_key='strategy:collect_param'
    )

# ===== 收集模块 =====
def on_start_collect(sender, request_id, data_key):
    """收到启动收集模块的指令"""

    pending_reads = {}

    def on_data_return(sender, req_id, key, value):
        if req_id in pending_reads:
            callback = pending_reads.pop(req_id)
            callback(value)

    signal('datahub:data_return').connect(on_data_return)

    def handle_param(param):
        print(f"收到收集参数: target={param['target_position']}")
        # 开始执行收集动作...

    req_id = datahub.read(data_key, request_id)
    pending_reads[req_id] = handle_param

signal(StrategyEvent.START_COLLECT.value).connect(on_start_collect)
```

### 6.3 执行模块 → 策略模块（状态反馈）

**流程**：执行模块完成动作 → 更新状态 → 发送状态更新事件 → 策略模块读取状态

```python
# ===== 执行模块（收集模块）=====

def update_status(code, msg, error_code=0):
    """更新模块状态"""

    # 1. 写入状态到 DataHub
    status = {
        'code': code,
        'msg': msg,
        'error_code': error_code
    }
    datahub.write('collect:status', status)

    # 2. 发送状态更新事件
    signal(CollectEvent.STATUS_UPDATED.value).send(
        None,
        request_id='req_status_update',
        data_key='collect:status'
    )

# 完成收集
update_status(code=3, msg="Task completed")

# 发生异常
update_status(code=-1, msg="Navigation failed", error_code=2)

# ===== 策略模块 =====
def on_collect_status_updated(sender, request_id, data_key):
    """处理收集模块状态更新"""

    pending_reads = {}

    def on_data_return(sender, req_id, key, value):
        if req_id in pending_reads:
            callback = pending_reads.pop(req_id)
            callback(value)

    signal('datahub:data_return').connect(on_data_return)

    def handle_status(status):
        print(f"收集状态: code={status['code']}, msg={status['msg']}")

        # 根据状态码决定下一步
        if status['code'] == 3:
            print("收集完成，启动放置模块")
            # start_place_module()
        elif status['code'] == -1:
            print(f"异常: error_code={status['error_code']}")
            # handle_error()

    req_id = datahub.read(data_key, request_id)
    pending_reads[req_id] = handle_status

signal(CollectEvent.STATUS_UPDATED.value).connect(on_collect_status_updated)
```

### 6.4 异常处理流程

```python
# ===== 执行模块检测到异常 =====

def report_exception(error_code, error_type, desc):
    """报告异常"""

    # 1. 写入错误信息
    error_info = {
        'error_code': error_code,
        'error_type': error_type,
        'desc': desc,
        'timestamp': time.time()
    }
    datahub.write('module:error_info', error_info)

    # 2. 发送异常事件
    signal(CollectEvent.EXCEPTION.value).send(
        None,
        request_id='req_exception',
        data_key='module:error_info'
    )

# 检测到导航失败
report_exception(
    error_code=2,
    error_type='navigation_fail',
    desc='Path blocked'
)

# ===== 策略模块处理异常 =====

def on_module_exception(sender, request_id, data_key):
    """处理模块异常"""

    pending_reads = {}

    def on_data_return(sender, req_id, key, value):
        if req_id in pending_reads:
            callback = pending_reads.pop(req_id)
            callback(value)

    signal('datahub:data_return').connect(on_data_return)

    def handle_error(error_info):
        print(f"模块异常: {error_info['error_type']} - {error_info['desc']}")

        # 根据错误类型决定重试还是终止
        if error_info['error_code'] in [1, 2]:  # 可重试的错误
            retry_param = {
                'module': 'collect',
                'retry_count': 0,
                'max_retry': 3
            }
            datahub.write('strategy:retry_param', retry_param)
            signal(StrategyEvent.MODULE_RETRY.value).send(
                None,
                request_id='req_retry',
                data_key='strategy:retry_param'
            )
        else:
            print("错误无法恢复，终止任务")

    req_id = datahub.read(data_key, request_id)
    pending_reads[req_id] = handle_error

signal(CollectEvent.EXCEPTION.value).connect(on_module_exception)
```

---

## 7. 常见问题

### Q1: 为什么我发送的事件没有收到？

检查以下几点：
1. 是否正确订阅了事件？
2. 发送事件和接收事件的时机是否正确？
3. 数据返回是异步的，是否等待了足够的时间？

```python
import time
time.sleep(0.1)  # 等待事件处理
```

### Q2: 如何调试通信问题？

可以使用打印语句来调试：

```python
# 在发送事件前打印
print(f"发送事件: start_collect, request_id={request_id}")

# 在接收事件时打印
def on_start_collect(sender, request_id, data_key):
    print(f"收到事件: start_collect, request_id={request_id}")
```

### Q3: 如何处理多个并发的读取请求？

使用 `request_id` 来区分不同的请求：

```python
pending_reads = {}

def on_data_return(sender, request_id, key, value):
    if request_id in pending_reads:
        callback = pending_reads.pop(request_id)
        callback(value)

def read_data(key, callback):
    request_id = str(uuid.uuid4())  # 生成唯一ID
    pending_reads[request_id] = callback
    datahub.read(key, request_id)
```

### Q4: 什么是状态码？

状态码表示执行模块当前所处的阶段：

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 0 | 初始化 | 刚收到任务，准备中 |
| 1 | 导航中 | 正在移动到目标位置 |
| 2 | 执行中 | 正在执行动作（抓取/放置/搭建） |
| 3 | 完成 | 任务成功完成 |
| -1 | 异常 | 发生了错误 |

### Q5: 什么是错误码？

错误码表示发生了哪种类型的错误：

| 错误码 | 含义 |
|--------|------|
| 0 | 无错误 |
| 1 | 视觉识别失败 |
| 2 | 导航失败 |
| 3 | 机械动作失败 |
| 4 | 通信异常 |
| 5 | 任务超时 |

---

## 8. API 参考

### 8.1 DataHub

```python
from robogame.common.datahub import get_datahub

datahub = get_datahub()

# 写入数据
datahub.write(key, value)

# 读取数据（返回 request_id）
request_id = datahub.read(key)
```

### 8.2 信号操作

```python
from blinker import signal

# 创建或获取信号
my_signal = signal('my_event')

# 发送事件
my_signal.send(None, data1=value1, data2=value2)

# 订阅事件
def handler(sender, **kwargs):
    pass
my_signal.connect(handler)

# 取消订阅
my_signal.disconnect(handler)
```

### 8.3 预定义事件

所有预定义事件都在 `robogame.common.events` 中：

```python
from robogame.common.events import (
    # DataHub 事件
    DataHubEvent,
    # 视觉事件
    VisionEvent,
    # 策略事件
    StrategyEvent,
    # 收集模块事件
    CollectEvent,
    # 放置模块事件
    PlaceEvent,
    # 搭建模块事件
    BuildEvent,
    # 通用模块事件
    ModuleEvent
)

# 使用
signal(DataHubEvent.WRITE.value)
signal(VisionEvent.DATA_UPDATED.value)
signal(StrategyEvent.START_COLLECT.value)
```

### 8.4 数据类型

```python
from robogame.common.types import (
    Position,    # 位置 (x, y, z)
    Pose,        # 位姿 (x, y, z, yaw, pitch, roll)
    CubeInfo,    # 方块信息
    ModuleStatus, # 模块状态
    HeartbeatInfo # 心跳信息
)

# 创建位置
pos = Position(x=100, y=200, z=50)

# 创建模块状态
status = ModuleStatus(code=1, msg="navigating", error_code=0)

# 创建心跳信息
heartbeat = HeartbeatInfo(module_name='vision_module')
```

### 8.5 任务调度类型

```python
from robogame.common.scheduler import (
    TaskScheduler,   # 任务调度器
    HeartbeatManager, # 心跳管理器
    TaskPriority,   # 任务优先级枚举
    TaskState,      # 任务状态枚举
    Task            # 任务对象
)

# 任务优先级
TaskPriority.LOW      # 低优先级 (0)
TaskPriority.NORMAL   # 普通优先级 (1)
TaskPriority.HIGH     # 高优先级 (2)
TaskPriority.CRITICAL # 紧急优先级 (3)

# 任务状态
TaskState.PENDING     # 待执行
TaskState.RUNNING     # 运行中
TaskState.SUSPENDED   # 已挂起
TaskState.COMPLETED   # 已完成
TaskState.CANCELLED   # 已取消
```

---

## 9. 高级功能

### 9.1 订阅推送模式

订阅指定的 DataHub key，数据变化时自动推送通知，无需反复发送 `read` 请求。

```python
from robogame.common.datahub import get_datahub

datahub = get_datahub()

# 定义回调函数
def on_cube_position_changed(key, value):
    print(f"Cube position updated: {value}")

# 订阅vision:cube_position的数据变化
datahub.subscribe('vision:cube_position', on_cube_position_changed)

# 当vision模块写入数据时，回调会自动被调用
datahub.write('vision:cube_position', {'x': 100, 'y': 200})

# 取消订阅
datahub.unsubscribe('vision:cube_position', on_cube_position_changed)
```

### 9.2 同步读写（ACK模式）

支持同步写入/读取，需要等待 ACK 或数据返回。

```python
# 同步写入，等待ACK，超时返回False（默认超时1秒）
result = datahub.write_with_ack('vision:cube_position', {'x': 100})
print(f"写入成功: {result}")

# 同步读取，等待数据返回，超时返回(None, False)
data, success = datahub.read_with_ack('vision:cube_position')
if success:
    print(f"读取成功: {data}")
```

### 9.3 心跳保活

所有模块可以启动心跳管理器，每秒自动发送心跳到 DataHub。

```python
from robogame.common.scheduler import get_heartbeat_manager

# 创建心跳管理器（每个模块有自己的名称）
heartbeat_mgr = get_heartbeat_manager('vision_module')

# 启动心跳（自动每秒发送一次）
heartbeat_mgr.start()

# 停止心跳
heartbeat_mgr.stop()

# 手动发送心跳
heartbeat_mgr.send_heartbeat()

# 检查模块状态
status = datahub.get_module_status('vision_module')
# 'online' / 'offline' / 'unknown'
```

**注意**：当模块失联超过 5 秒（可配置），DataHub 会触发安全机制，发送 `datahub:safety_shutdown` 事件。

### 9.4 数据持久化

关键数据会自动持久化到 JSON 文件，重启后可恢复。

```python
# DataHub启动时自动加载持久化数据
datahub = get_datahub(persistence_dir='data')

# 手动触发持久化
datahub.persist_now()

# 持久化的数据包括：任务参数、状态、异常记录等
```

### 9.5 动态任务调度器

任务调度器支持优先级、抢占、中断恢复、可随时切换目标方块。

```python
from robogame.common.scheduler import get_task_scheduler, TaskPriority

scheduler = get_task_scheduler()

# 创建任务（优先级：LOW=0, NORMAL=1, HIGH=2, CRITICAL=3）
task_id = scheduler.create_task(
    task_type='collect',      # 'collect' / 'place' / 'build'
    target={'x': 100, 'y': 200},
    priority=TaskPriority.HIGH,
    cube_id=1
)

# 抢占式调度（中断当前任务，优先执行新任务）
scheduler.preempt_task('collect', {'x': 300, 'y': 400}, TaskPriority.CRITICAL, cube_id=2)

# 切换任务目标（如中途切换目标方块）
scheduler.switch_target(task_id, {'x': 500, 'y': 500})

# 挂起当前任务
scheduler.suspend_current_task('manual')

# 恢复被挂起的任务
scheduler.resume_task(task_id)

# 模拟任务完成
scheduler.on_task_complete(task_id, {'success': True})

# 获取任务状态
status = scheduler.get_task_status(task_id)
print(f"任务状态: {status}")

# 获取待执行任务列表
pending = scheduler.get_pending_tasks()
print(f"待执行任务: {len(pending)}个")

# 获取当前运行中的任务
running = scheduler.get_running_task()
print(f"运行中任务: {running}")
```

**任务优先级**：
| 优先级 | 值 | 说明 |
|--------|-----|------|
| `LOW` | 0 | 低优先级 |
| `NORMAL` | 1 | 普通优先级（默认） |
| `HIGH` | 2 | 高优先级 |
| `CRITICAL` | 3 | 紧急优先级，可抢占当前任务 |

**任务状态**：`PENDING` → `RUNNING` → `COMPLETED` / `SUSPENDED` → `CANCELLED`

---

## 附录：完整示例

### 完整流程：收集 → 放置 → 搭建

```python
"""
RoboGame 完整工作流程示例
"""
import time
from blinker import signal

import sys
sys.path.insert(0, 'src')

from robogame.common.datahub import get_datahub
from robogame.common.events import (
    DataHubEvent, VisionEvent, StrategyEvent,
    CollectEvent, PlaceEvent, BuildEvent
)
from robogame.vision.camera import get_vision_module
from robogame.strategy.scheduler import get_strategy_module
from robogame.actuator.collect.collect import get_collect_module
from robogame.actuator.place.place import get_place_module
from robogame.actuator.build.build import get_build_module

# 初始化所有模块
vision = get_vision_module()
strategy = get_strategy_module()
collect = get_collect_module()
place = get_place_module()
build = get_build_module()

# 订阅数据返回事件
pending_reads = {}

def on_data_return(sender, request_id, key, value):
    if request_id in pending_reads:
        callback = pending_reads.pop(request_id)
        callback(value)

signal(DataHubEvent.DATA_RETURN.value).connect(on_data_return)

def read_data(key, callback):
    datahub = get_datahub()
    request_id = datahub.read(key)
    pending_reads[request_id] = callback

# 启动策略模块
strategy.start()
collect.start()
place.start()
build.start()

print("=== 开始任务 ===")

# 1. 模拟视觉模块检测到方块
print("1. 视觉模块检测到方块")
datahub = get_datahub()
datahub.write('vision:cube_position', {'x': 100, 'y': 200, 'z': 50})
signal(VisionEvent.DATA_UPDATED.value).send(None, request_id='1', data_key='vision:cube_position')

time.sleep(0.1)

# 2. 策略模块启动收集
print("2. 策略模块启动收集")
collect_param = {'target_position': {'x': 100, 'y': 200}, 'threshold': 5}
datahub.write('strategy:collect_param', collect_param)
signal(StrategyEvent.START_COLLECT.value).send(None, request_id='2', data_key='strategy:collect_param')

time.sleep(0.1)

# 3. 模拟收集完成
print("3. 收集完成")
datahub.write('collect:status', {'code': 3, 'msg': 'completed'})
signal(CollectEvent.STATUS_UPDATED.value).send(None, request_id='3', data_key='collect:status')

time.sleep(0.1)

# 4. 策略模块启动放置
print("4. 策略模块启动放置")
place_param = {'target_position': {'x': 50, 'y': 50}}
datahub.write('strategy:place_param', place_param)
signal(StrategyEvent.START_PLACE.value).send(None, request_id='4', data_key='strategy:place_param')

time.sleep(0.1)

# 5. 模拟放置完成
print("5. 放置完成")
datahub.write('place:status', {'code': 3, 'msg': 'completed'})
signal(PlaceEvent.STATUS_UPDATED.value).send(None, request_id='5', data_key='place:status')

time.sleep(0.1)

# 6. 策略模块启动搭建
print("6. 策略模块启动搭建")
build_param = {'target_position': {'x': 50, 'y': 50, 'z': 0}}
datahub.write('strategy:build_param', build_param)
signal(StrategyEvent.START_BUILD.value).send(None, request_id='6', data_key='strategy:build_param')

time.sleep(0.1)

# 7. 模拟搭建完成
print("7. 搭建完成")
datahub.write('build:status', {'code': 3, 'msg': 'completed'})
signal(BuildEvent.STATUS_UPDATED.value).send(None, request_id='7', data_key='build:status')

print("=== 任务完成 ===")
```

运行这个示例，你将看到所有模块之间通过事件进行通信的完整过程。