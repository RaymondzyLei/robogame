# RoboGame 机器人方块任务控制系统

## 1. 系统概述

### 1.1 项目简介

本项目为 RoboGame 竞赛中机器人方块收集-放置-搭建任务控制系统，采用"感知-决策-执行-反馈"分层闭环架构。

### 1.2 系统架构

```
graph LR
    A[视觉模块<br/>感知层] -->|目标位置/位姿反馈| B[策略模块<br/>决策层]
    B -->|控制指令| C[收集模块<br/>执行层]
    B -->|控制指令| D[放置模块<br/>执行层]
    B -->|控制指令| E[搭建模块<br/>执行层]
    C -->|执行状态/异常反馈| B
    D -->|执行状态/异常反馈| B
    E -->|执行状态/异常反馈| B
```

### 1.3 项目结构

```
robogame/
├── src/robogame/
│   ├── common/           # 公共模块
│   │   ├── fsm.py       # 有限状态机
│   │   ├── types.py     # 数据类型定义
│   │   ├── error.py     # 错误码定义
│   │   └── protocol.py  # 通信协议
│   ├── strategy/        # 策略模块（决策层）
│   │   └── scheduler.py # 任务调度器
│   ├── vision/           # 视觉模块（感知层）
│   │   ├── camera.py    # 相机接口
│   │   └── detector.py  # 目标检测
│   ├── actuator/         # 执行模块（执行层）
│   │   ├── collect/      # 收集方块模块
│   │   ├── place/       # 放置方块模块
│   │   └── build/       # 搭建方块模块
│   └── __init__.py
├── tests/               # 测试目录
├── docs/                # 文档目录
└── README.md
```

## 2. 核心模块

### 2.1 公共模块 (common)

| 模块 | 功能 |
|------|------|
| fsm.py | 有限状态机实现，定义 State.INIT/NAVIGATE/EXECUTE/FINISH/ERROR |
| types.py | 数据类型：Position、Block、BuildTarget |
| error.py | 错误码：OK/VISION_FAILED/NAVIGATION_FAILED/ACTION_FAILED/COMM_ERROR/TIMEOUT |
| protocol.py | 通信协议：Status、TaskCommand |

### 2.2 策略模块 (strategy)

任务调度器 TaskScheduler 负责任务阶段流转：
- COLLECT → PLACE → BUILD → IDLE

### 2.3 视觉模块 (vision)

- Camera: 相机接口
- VisionModule: 目标检测（方块、目标点、机器人位姿）

### 2.4 执行模块 (actuator)

三个独立的动作模块，每个模块基于有限状态机模型：

| 模块 | 状态流转 |
|------|----------|
| CollectModule | INIT → NAVIGATE → EXECUTE → FINISH |
| PlaceModule | INIT → NAVIGATE → EXECUTE → FINISH |
| BuildModule | INIT → NAVIGATE → EXECUTE → FINISH |

## 3. 状态码定义

| 状态码 | 含义 |
|--------|------|
| 0 | INIT - 初始化定位 |
| 1 | NAVIGATE - 导航到目标 |
| 2 | EXECUTE - 动作执行（抓取/放置/搭建） |
| 3 | FINISH - 模块任务结束 |
| -1 | ERROR - 异常处理 |

## 4. 错误码定义

| 错误码 | 含义 |
|--------|------|
| 0 | OK - 无错误 |
| 1 | VISION_FAILED - 视觉识别失败 |
| 2 | NAVIGATION_FAILED - 导航失败 |
| 3 | ACTION_FAILED - 机械动作失败 |
| 4 | COMM_ERROR - 通信异常 |
| 5 | TIMEOUT - 任务超时 |

## 5. 使用方式

```python
from robogame.common import StateMachine, State
from robogame.strategy import TaskScheduler, TaskPhase
from robogame.actuator import CollectModule, PlaceModule, BuildModule

# 初始化
scheduler = TaskScheduler()
collect = CollectModule()

# 启动收集任务
scheduler.start_collect()
collect.fsm.reset()

# 运行状态机
while collect.fsm.get_state() != State.FINISH:
    collect.update()
```

## 6. 待实现细节

- [ ] 视觉模块具体实现（目标检测算法）
- [ ] 路径规划算法（A*）
- [ ] 机械臂逆运动学求解
- [ ] 与STM32下位机通信协议实现
- [ ] 传感器数据融合
- [ ] 异常处理机制完善