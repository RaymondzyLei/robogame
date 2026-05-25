"""Communication primitives for RoboGame."""

from robogame.communication.bus import EventBus, get_event_bus, new_request_id

__all__ = ["EventBus", "get_event_bus", "new_request_id"]
