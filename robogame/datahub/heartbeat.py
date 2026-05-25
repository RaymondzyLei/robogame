"""Heartbeat monitoring for RoboGame modules."""

from __future__ import annotations

from threading import Event, Thread, RLock
from time import sleep, time
from typing import Any

from robogame.communication.bus import EventBus, get_event_bus
from robogame.communication import events


class HeartbeatManager:
    def __init__(self, module_name: str, bus: EventBus | None = None, interval: float = 1.0) -> None:
        self.module_name = module_name
        self.bus = bus or get_event_bus()
        self.interval = interval
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run, name=f"heartbeat:{self.module_name}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.interval * 2)

    def send_heartbeat(self) -> None:
        self.bus.publish(events.MODULE_HEARTBEAT, self.module_name, module=self.module_name, timestamp=time())

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval):
            self.send_heartbeat()


class HeartbeatMonitor:
    def __init__(self, bus: EventBus | None = None, timeout: float = 5.0) -> None:
        self.bus = bus or get_event_bus()
        self.timeout = timeout
        self._lock = RLock()
        self._last_seen: dict[str, float] = {}
        self.bus.subscribe(events.MODULE_HEARTBEAT, self._on_heartbeat)

    def get_module_status(self, module_name: str) -> str:
        with self._lock:
            last_seen = self._last_seen.get(module_name)
        if last_seen is None:
            return "unknown"
        return "online" if time() - last_seen <= self.timeout else "offline"

    def check_timeouts(self) -> dict[str, str]:
        with self._lock:
            modules = list(self._last_seen)
        statuses = {module: self.get_module_status(module) for module in modules}
        for module, status in statuses.items():
            if status == "offline":
                self.bus.publish(events.DATAHUB_SAFETY_SHUTDOWN, "datahub", module=module)
        return statuses

    def _on_heartbeat(self, sender: str, payload: dict[str, Any]) -> None:
        module = str(payload.get("module") or sender)
        timestamp = float(payload.get("timestamp", time()))
        with self._lock:
            self._last_seen[module] = timestamp


def get_heartbeat_manager(module_name: str, bus: EventBus | None = None) -> HeartbeatManager:
    return HeartbeatManager(module_name, bus=bus)
