from dataclasses import dataclass


@dataclass
class Position:
    """位置信息"""
    x: float
    y: float
    theta: float = 0.0  # 角度，弧度


@dataclass
class Block:
    """方块信息"""
    id: int
    position: Position
    color: str = "unknown"
    size: float = 0.0


@dataclass
class BuildTarget:
    """搭建目标点"""
    id: int
    position: Position
    height: int = 0  # 层级
    required_block_color: str | None = None