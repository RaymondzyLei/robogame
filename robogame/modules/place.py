"""Place actuator module."""

from __future__ import annotations

from robogame.communication import events
from robogame.communication.bus import EventBus
from robogame.modules.actuator import ActuatorModule


class PlaceModule(ActuatorModule):
    start_event = events.STRATEGY_START_PLACE
    status_event = events.PLACE_STATUS_UPDATED
    status_key = "place:status"
    param_key = "strategy:place_param"

    def __init__(self, bus: EventBus | None = None) -> None:
        super().__init__("place", bus=bus)
