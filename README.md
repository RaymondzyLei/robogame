# RoboGame

RoboGame 是一个面向机器人方块收集、放置、搭建任务的 Python 控制系统框架。当前项目重点搭建了模块边界、事件通信和硬件抽象基础，便于后续逐步接入真实视觉算法、路径规划和树莓派硬件控制。

## 项目目标

系统遵循“感知 - 决策 - 执行 - 反馈”的闭环控制思路：

- 视觉模块负责环境感知、方块定位和动作校验。
- 策略模块负责任务调度和状态流转。
- 收集、放置、搭建模块负责执行动作状态机。
- DataHub 负责全局共享数据管理。
- Blinker 事件总线负责模块间解耦通信。
- HAL 硬件抽象层负责屏蔽 PCA9685、电机、舵机、机械爪、机械臂等底层差异。

## 目录结构

```text
robogame/
  communication/   # EventBus 封装与事件常量
  datahub/         # DataHub、心跳、ACK、订阅、持久化骨架
  modules/         # 策略、视觉、执行模块通信骨架
  hardware/        # PCA9685、电机、舵机、运动/机械爪/机械臂控制抽象
  scheduler/       # 动态任务调度器骨架
  runtime.py       # 系统装配入口
  types.py         # 状态码、错误码、载荷类型

tests/             # 通信闭环与集成流程测试
examples/          # PCA9685 官方风格示例
```

## 核心通信规则

业务模块不直接互相调用，也不直接共享状态。所有跨模块联动均通过事件完成：

1. 模块写数据：发布 `datahub:write`。
2. DataHub 写入内部数据并发布 `datahub:ack` / `datahub:data_changed`。
3. 模块读数据：发布 `datahub:read`。
4. DataHub 返回 `datahub:data_return`，并用 `request_id` 关联请求。
5. 业务流程事件只传递 `data_key` 和上下文，完整数据由接收方再向 DataHub 读取。

## 快速使用

```python
from robogame import create_runtime

runtime = create_runtime()
runtime.strategy.start_task({"collect": {"target_id": 1, "threshold": 5}})

# 当前执行模块是骨架状态机，可手动推进用于仿真/测试
runtime.collect.run_once()
runtime.collect.run_once()
runtime.collect.run_once()
```

## 依赖管理

项目使用 uv 管理依赖：

```bash
uv add <package>
uv add --dev <package>
uv remove <package>
```

不要手动编辑 `pyproject.toml` 添加或移除依赖。

## 测试与类型检查

```bash
uv run python -m compileall robogame tests examples
uv run python -m pytest
uv run pyright
```

当前测试覆盖：

- DataHub 写入、读取、ACK、返回数据闭环。
- 视觉数据写入后由策略模块读取。
- 策略调度 `collect -> place -> build` 的基础流程。

## 硬件说明

`robogame.hardware` 默认是安全抽象，不会自动初始化真实硬件。要在树莓派上控制 PCA9685，需要显式初始化：

```python
import busio
from board import SCL, SDA
from robogame.hardware import get_pca9685_driver

i2c = busio.I2C(SCL, SDA)
driver = get_pca9685_driver()
driver.initialize(i2c, address=0x40)
driver.frequency = 50
```
