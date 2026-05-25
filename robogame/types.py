"""Shared RoboGame typed constants and dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any


class ModuleState(IntEnum):
    INIT = 0
    NAVIGATING = 1
    ACTING = 2
    DONE = 3
    ERROR = -1


class ErrorCode(IntEnum):
    OK = 0
    VISION_FAILED = 1
    NAVIGATION_FAILED = 2
    MECHANICAL_FAILED = 3
    COMMUNICATION_FAILED = 4
    TASK_TIMEOUT = 5


class ModuleName(StrEnum):
    STRATEGY = "strategy"
    VISION = "vision"
    COLLECT = "collect"
    PLACE = "place"
    BUILD = "build"


@dataclass(frozen=True)
class StatusPayload:
    code: ModuleState
    msg: str
    error: ErrorCode = ErrorCode.OK
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": int(self.code),
            "msg": self.msg,
            "error": int(self.error),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ErrorPayload:
    error_code: ErrorCode
    error_type: str
    desc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"error_code": int(self.error_code), "error_type": self.error_type, "desc": self.desc}
