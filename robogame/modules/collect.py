"""Collect actuator module."""

from __future__ import annotations

from robogame.communication import events
from robogame.communication.bus import EventBus
from robogame.modules.actuator import ActuatorModule


class CollectModule(ActuatorModule):
    start_event = events.STRATEGY_START_COLLECT
    status_event = events.COLLECT_STATUS_UPDATED
    status_key = "collect:status"
    param_key = "strategy:collect_param"

    def __init__(self, bus: EventBus | None = None) -> None:
        super().__init__("collect", bus=bus)
