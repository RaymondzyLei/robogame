"""Blinker事件名称定义"""
from enum import Enum


class DataHubEvent(Enum):
    WRITE = 'datahub:write'
    READ = 'datahub:read'
    DATA_RETURN = 'datahub:data_return'


class VisionEvent(Enum):
    DATA_UPDATED = 'vision:data_updated'
    GRAB_CHECK_DONE = 'vision:grab_check_done'
    PLACE_CHECK_DONE = 'vision:place_check_done'
    BUILD_CHECK_DONE = 'vision:build_check_done'
    ADJUST_PARAM = 'vision:adjust_param'


class StrategyEvent(Enum):
    START_COLLECT = 'strategy:start_collect'
    START_PLACE = 'strategy:start_place'
    START_BUILD = 'strategy:start_build'
    ADJUST_RECOGNIZE_PARAM = 'strategy:adjust_recognize_param'
    MODULE_RETRY = 'strategy:module_retry'
    TASK_COMPLETE = 'strategy:task_complete'
    TASK_FAILED = 'strategy:task_failed'


class CollectEvent(Enum):
    STATUS_UPDATED = 'collect:status_updated'
    INIT_COMPLETE = 'collect:init_complete'
    NAVIGATING = 'collect:navigating'
    GRABBING = 'collect:grabbing'
    TASK_COMPLETE = 'collect:task_complete'
    EXCEPTION = 'collect:exception'


class PlaceEvent(Enum):
    STATUS_UPDATED = 'place:status_updated'
    INIT_COMPLETE = 'place:init_complete'
    NAVIGATING = 'place:navigating'
    PLACING = 'place:placing'
    TASK_COMPLETE = 'place:task_complete'
    EXCEPTION = 'place:exception'


class BuildEvent(Enum):
    STATUS_UPDATED = 'build:status_updated'
    INIT_COMPLETE = 'build:init_complete'
    NAVIGATING = 'build:navigating'
    BUILDING = 'build:building'
    TASK_COMPLETE = 'build:task_complete'
    EXCEPTION = 'build:exception'


class DataHubEvent(Enum):
    WRITE = 'datahub:write'
    READ = 'datahub:read'
    DATA_RETURN = 'datahub:data_return'
    ACK = 'datahub:ack'
    DATA_CHANGED = 'datahub:data_changed'
    SAFETY_SHUTDOWN = 'datahub:safety_shutdown'
    COMMUNICATION_EXCEPTION = 'datahub:communication_exception'


class ModuleEvent(Enum):
    HEARTBEAT = 'module:heartbeat'
    EXCEPTION = 'module:exception'
    RETRY = 'module:retry'
    TERMINATE = 'module:terminate'