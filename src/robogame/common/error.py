from enum import IntEnum


class ErrorCode(IntEnum):
    OK = 0
    VISION_FAILED = 1
    NAVIGATION_FAILED = 2
    ACTION_FAILED = 3
    COMM_ERROR = 4
    TIMEOUT = 5