"""Vision module skeleton for perception and visual checks."""

from __future__ import annotations

from typing import Any

from robogame.communication import events
from robogame.communication.bus import EventBus
from robogame.modules.base import BaseModule


class VisionModule(BaseModule):
    def __init__(self, bus: EventBus | None = None) -> None:
        super().__init__("vision", bus=bus)
        self.bus.subscribe(events.ADJUST_RECOGNIZE_PARAM, self._on_adjust_param)
        self.recognize_param: dict[str, Any] = {}

    def update_cube_position(self, pose: dict[str, Any]) -> None:
        key = "vision:cube_position"
        self.write_data(key, pose)
        self.publish_business_event(events.VISION_DATA_UPDATED, key)

    def publish_check_result(self, check_type: str, result: bool, error: int = 0) -> None:
        key = f"vision:{check_type}_check_result"
        self.write_data(key, {"result": result, "error": error})
        event_name = {
            "grab": events.VISION_GRAB_CHECK_DONE,
            "place": events.VISION_PLACE_CHECK_DONE,
            "build": events.VISION_BUILD_CHECK_DONE,
        }.get(check_type, events.VISION_DATA_UPDATED)
        self.publish_business_event(event_name, key)

    def _on_adjust_param(self, sender: str, payload: dict[str, Any]) -> None:
        data_key = str(payload.get("data_key") or "strategy:recognize_param")
        value, success = self.read_data(data_key)
        if success and isinstance(value, dict):
            self.recognize_param = value
