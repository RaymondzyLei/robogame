"""Generic actuator state machine skeleton."""

from __future__ import annotations

from typing import Any

from robogame.communication.bus import EventBus
from robogame.modules.base import BaseModule
from robogame.types import ErrorCode, ModuleState, StatusPayload


class ActuatorModule(BaseModule):
    start_event: str
    status_event: str
    status_key: str
    param_key: str

    def __init__(self, name: str, bus: EventBus | None = None) -> None:
        super().__init__(name, bus=bus)
        self.state = ModuleState.INIT
        self.params: dict[str, Any] = {}
        self.bus.subscribe(self.start_event, self._on_start)

    def run_once(self) -> None:
        if self.state == ModuleState.INIT:
            self._set_status(ModuleState.NAVIGATING, "navigating")
        elif self.state == ModuleState.NAVIGATING:
            self._set_status(ModuleState.ACTING, "acting")
        elif self.state == ModuleState.ACTING:
            self._set_status(ModuleState.DONE, "done")

    def fail(self, error: ErrorCode, message: str) -> None:
        self._set_status(ModuleState.ERROR, message, error=error)

    def _on_start(self, sender: str, payload: dict[str, Any]) -> None:
        data_key = str(payload.get("data_key") or self.param_key)
        value, success = self.read_data(data_key)
        self.params = value if success and isinstance(value, dict) else {}
        self._set_status(ModuleState.INIT, "initialized", detail={"params": self.params})

    def _set_status(
        self,
        state: ModuleState,
        message: str,
        error: ErrorCode = ErrorCode.OK,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.state = state
        status = StatusPayload(state, message, error=error, detail=detail or {}).to_dict()
        self.write_data(self.status_key, status)
        self.publish_business_event(self.status_event, self.status_key)
