"""Strategy module coordinating collect -> place -> build."""

from __future__ import annotations

from typing import Any

from robogame.communication import events
from robogame.communication.bus import EventBus
from robogame.modules.base import BaseModule
from robogame.types import ModuleState, StatusPayload


class StrategyModule(BaseModule):
    def __init__(self, bus: EventBus | None = None) -> None:
        super().__init__("strategy", bus=bus)
        self.completed = False
        self.bus.subscribe(events.COLLECT_STATUS_UPDATED, self._on_collect_status)
        self.bus.subscribe(events.PLACE_STATUS_UPDATED, self._on_place_status)
        self.bus.subscribe(events.BUILD_STATUS_UPDATED, self._on_build_status)
        self.bus.subscribe(events.MODULE_EXCEPTION, self._on_exception)

    def start_task(self, task_param: dict[str, Any]) -> None:
        self.write_data("strategy:task_param", task_param)
        collect_param = task_param.get("collect", task_param)
        self.write_data("strategy:collect_param", collect_param)
        self.publish_business_event(events.STRATEGY_START_COLLECT, "strategy:collect_param")

    def _on_collect_status(self, sender: str, payload: dict[str, Any]) -> None:
        status = self._read_status(payload, "collect:status")
        if status.get("code") == int(ModuleState.DONE):
            self.write_data("strategy:place_param", {"source": "collect_done", **status.get("detail", {})})
            self.publish_business_event(events.STRATEGY_START_PLACE, "strategy:place_param")

    def _on_place_status(self, sender: str, payload: dict[str, Any]) -> None:
        status = self._read_status(payload, "place:status")
        if status.get("code") == int(ModuleState.DONE):
            self.write_data("strategy:build_param", {"source": "place_done", **status.get("detail", {})})
            self.publish_business_event(events.STRATEGY_START_BUILD, "strategy:build_param")

    def _on_build_status(self, sender: str, payload: dict[str, Any]) -> None:
        status = self._read_status(payload, "build:status")
        if status.get("code") == int(ModuleState.DONE):
            self.completed = True
            self.write_data("strategy:task_result", StatusPayload(ModuleState.DONE, "global task done").to_dict())
            self.publish_business_event(events.GLOBAL_TASK_DONE, "strategy:task_result")

    def _on_exception(self, sender: str, payload: dict[str, Any]) -> None:
        data_key = str(payload.get("data_key", "module:error_info"))
        error_info, success = self.read_data(data_key)
        if success:
            self.write_data("strategy:last_error", error_info)

    def _read_status(self, payload: dict[str, Any], fallback_key: str) -> dict[str, Any]:
        data_key = str(payload.get("data_key") or fallback_key)
        status, success = self.read_data(data_key)
        return status if success and isinstance(status, dict) else {}
