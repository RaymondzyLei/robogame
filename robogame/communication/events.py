"""Shared event names used by the RoboGame event bus."""

DATAHUB_WRITE = "datahub:write"
DATAHUB_READ = "datahub:read"
DATAHUB_DATA_RETURN = "datahub:data_return"
DATAHUB_ACK = "datahub:ack"
DATAHUB_DATA_CHANGED = "datahub:data_changed"
DATAHUB_SAFETY_SHUTDOWN = "datahub:safety_shutdown"
DATAHUB_COMMUNICATION_EXCEPTION = "datahub:communication_exception"

MODULE_HEARTBEAT = "module:heartbeat"
MODULE_EXCEPTION = "module:exception"

VISION_DATA_UPDATED = "vision:data_updated"
VISION_GRAB_CHECK_DONE = "vision:grab_check_done"
VISION_PLACE_CHECK_DONE = "vision:place_check_done"
VISION_BUILD_CHECK_DONE = "vision:build_check_done"
ADJUST_RECOGNIZE_PARAM = "strategy:adjust_recognize_param"

STRATEGY_START_COLLECT = "strategy:start_collect"
STRATEGY_START_PLACE = "strategy:start_place"
STRATEGY_START_BUILD = "strategy:start_build"
STRATEGY_MODULE_RETRY = "strategy:module_retry"
GLOBAL_TASK_DONE = "strategy:global_task_done"

COLLECT_STATUS_UPDATED = "collect:status_updated"
PLACE_STATUS_UPDATED = "place:status_updated"
BUILD_STATUS_UPDATED = "build:status_updated"
