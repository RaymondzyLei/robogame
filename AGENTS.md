# RoboGame 项目协作说明

## 关于包管理

已经手动用 uv 创建过环境。
使用 `uv` 管理依赖，**禁止直接编辑 pyproject.toml**。正确方式：

```bash
uv add <package>      # 添加运行依赖
uv add --dev <package> # 添加开发/测试依赖
uv remove <package>   # 移除依赖
```

## 当前架构约定

本项目采用 `DataHub + Blinker` 的事件驱动架构：

- `DataHub` 是全局共享数据的唯一管理者，内部负责线程安全、ACK、订阅推送、持久化骨架。
- 业务模块不得直接调用其他业务模块的方法进行联动，应通过 `EventBus` 发布/订阅业务事件。
- 业务模块读写共享数据时，应发布 `datahub:write` / `datahub:read` 事件，由 DataHub 处理后返回 `datahub:ack` / `datahub:data_return`。
- 视觉、策略、收集、放置、搭建模块都应继承或遵循 `robogame.modules.base.BaseModule` 的通信模式。
- 执行模块状态码沿用文档定义：`0` 初始化、`1` 导航、`2` 动作执行、`3` 完成、`-1` 异常。

## 硬件开发约定

- `robogame.hardware` 当前提供安全占位/抽象接口；默认不会初始化真实 PCA9685 硬件。
- 只有在树莓派等目标硬件环境中，才应显式传入 I2C 对象调用 `PCA9685Driver.initialize(...)`。
- 上层业务逻辑应依赖 `MotionController`、`GripperController`、`ArmController` 等抽象接口，避免直接操作底层 PWM 通道。

## 测试与检查

常用验证命令：

```bash
uv run python -m compileall robogame tests examples
uv run python -m pytest
uv run pyright
```

提交前应至少运行以上检查，除非当前环境缺少对应工具或硬件依赖，并在提交说明中记录原因。
