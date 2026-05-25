# 2026-05-25 框架搭建开发记录

## 背景

根据项目 Markdown 文档中的技术设计，本次开发目标是搭建 RoboGame 的基础项目框架，优先保证模块边界清晰、通信链路可测试，并为后续接入视觉算法、路径规划和真实硬件控制预留接口。

## 已完成内容

### 1. 通信层

新增 `robogame.communication`：

- `EventBus`：基于 Blinker 封装统一的 `publish/subscribe` 接口。
- `events.py`：集中定义 DataHub 事件与业务事件名称。
- `new_request_id`：生成请求 ID，用于 ACK 和数据返回关联。

### 2. DataHub 数据中心

新增 `robogame.datahub`：

- `DataHub` 监听 `datahub:write` / `datahub:read`。
- 内部使用 `RLock` 做线程安全保护。
- 写入后发布 `datahub:ack` 和 `datahub:data_changed`。
- 读取后发布 `datahub:data_return` 和 ACK。
- 提供 key 订阅和 JSON 持久化骨架。
- `HeartbeatManager` / `HeartbeatMonitor` 提供模块心跳和失联检测基础。

### 3. 业务模块骨架

新增 `robogame.modules`：

- `BaseModule`：封装通过事件读写 DataHub、等待 ACK、等待数据返回、心跳发送。
- `StrategyModule`：实现 `collect -> place -> build` 的基础调度骨架。
- `VisionModule`：实现视觉数据更新与抓取/放置/搭建校验事件发布骨架。
- `ActuatorModule`：实现执行模块通用状态机骨架。
- `CollectModule`、`PlaceModule`、`BuildModule`：分别监听策略启动事件，写入状态并发布状态更新事件。

### 4. 类型与状态定义

新增 `robogame.types`：

- `ModuleState`：`INIT / NAVIGATING / ACTING / DONE / ERROR`。
- `ErrorCode`：视觉、导航、机械、通信、超时等错误码。
- `StatusPayload` 和 `ErrorPayload`：统一状态与错误载荷结构。

### 5. 硬件抽象层

新增 `robogame.hardware`：

- `PCA9685Driver`：默认安全占位，显式初始化后才连接真实 PCA9685。
- `DCMotor`、`StepperMotor`、`ServoController`、`ContinuousRotationServo`。
- `MotionController`、`GripperController`、`ArmController`。

当前 HAL 以接口和安全仿真为主，方便在非树莓派开发环境运行测试。

### 6. 任务调度器骨架

新增 `robogame.scheduler`：

- `TaskPriority`、`TaskState`、`ScheduledTask`。
- `TaskScheduler` 支持创建任务、取下一个任务、抢占、切换目标、挂起、恢复和完成回调。

### 7. 运行时装配

新增 `robogame.runtime`：

- `create_runtime()` 创建独立 `EventBus`、`DataHub`、心跳监控器和五个业务模块。
- `RoboGameRuntime.start()` / `stop()` 统一管理模块心跳。

### 8. 测试与检查

新增测试：

- `tests/test_datahub.py`：验证 DataHub 写入/读取闭环。
- `tests/test_integration_flow.py`：验证视觉数据读取和策略调度执行链路。

新增开发依赖：

- `pytest`
- `pyright`

新增运行依赖：

- `adafruit-circuitpython-motor`

同时修复了 PCA9685 示例中的类型检查问题。

## 验证结果

以下命令已通过：

```bash
uv run python -m compileall robogame tests examples
uv run python -m pytest
uv run pyright
```

结果：

- `pytest`：3 个测试全部通过。
- `pyright`：0 errors, 0 warnings。
- `compileall`：源码、测试、示例均可编译。

## 后续建议

1. 将执行模块状态机从 `run_once()` 骨架扩展为真实导航、抓取、放置、搭建动作。
2. 将视觉模块接入 OpenCV 识别流程，并用 DataHub 发布方块位姿和校验结果。
3. 将 HAL 的安全占位接口逐步替换为目标硬件上的真实控制逻辑。
4. 为通信超时、模块异常、心跳失联、安全停机补充集成测试。
5. 根据真实比赛任务补全 `TaskScheduler` 与 `StrategyModule` 的任务优先级和重试策略。
