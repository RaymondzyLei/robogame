"""Build actuator module."""

from __future__ import annotations

from robogame.communication import events
from robogame.communication.bus import EventBus
from robogame.modules.actuator import ActuatorModule


class BuildModule(ActuatorModule):
    start_event = events.STRATEGY_START_BUILD
    status_event = events.BUILD_STATUS_UPDATED
    status_key = "build:status"
    param_key = "strategy:build_param"

    def __init__(self, bus: EventBus | None = None) -> None:
        super().__init__("build", bus=bus)
