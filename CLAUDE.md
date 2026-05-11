# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 开发命令

```bash
# 安装依赖（使用uv）
uv sync

# 运行测试
uv run pytest

# 运行单个测试文件
uv run pytest tests/test_fsm.py

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      MessageBus (消息总线)                    │
│   所有模块间通信均通过发布/订阅模式实现解耦                      │
└─────────────────────────────────────────────────────────────┘
         ↑                    ↑                    ↑
    视觉模块             策略模块             执行模块
    (感知层)            (决策层)             (执行层)
```

### 核心设计模式

1. **消息总线模式** - [bus.py](src/robogame/common/bus.py) 是全局通信枢纽
   - `get_bus()` 获取全局单例
   - `MessageType` 定义所有消息类型
   - **视觉↔策略↔执行 三个大模块之间均通过 MessageBus 通信**
   - 发布/订阅机制实现松耦合

2. **有限状态机模式** - [fsm.py](src/robogame/common/fsm.py) 每个执行模块使用
   - `State.INIT → NAVIGATE → EXECUTE → FINISH`
   - `State.ERROR` 为异常处理状态
   - 支持状态转换回调

### 模块说明

| 模块 | 路径 | 职责 |
|------|------|------|
| common | src/robogame/common/ | 公共组件：FSM、消息总线、数据类型、错误码、协议 |
| strategy | src/robogame/strategy/ | 任务调度：COLLECT → PLACE → BUILD → IDLE 阶段流转 |
| vision | src/robogame/vision/ | 感知层：相机接口、目标检测 |
| actuator | src/robogame/actuator/ | 执行层：collect/place/build 三个独立模块 |

### 关键数据类型

- [Position](src/robogame/common/types.py#L5): x, y, theta
- [Block](src/robogame/common/types.py#L13): id, position, color, size
- [BuildTarget](src/robogame/common/types.py#L22): id, position, height, required_block_color

### 消息类型分类

- 视觉→策略/执行: `BLOCKS_DETECTED`, `TARGET_DETECTED`, `ROBOT_POSE_UPDATED`
- 执行→策略/视觉: `NAVIGATION_*`, `ACTION_*`
- 策略→执行: `TASK_START`, `TASK_CANCEL`, `TASK_PHASE_CHANGE`

## 包管理

使用 `uv` 管理依赖，**禁止直接编辑 pyproject.toml**。正确方式：

```bash
uv add <package>      # 添加依赖
uv remove <package>   # 移除依赖
```

## 待实现功能

- 视觉模块具体实现（目标检测算法）
- 路径规划算法（A*）
- 机械臂逆运动学求解
- 与STM32下位机通信协议实现