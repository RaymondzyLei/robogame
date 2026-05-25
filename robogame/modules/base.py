"""Base class for event-driven business modules."""

from __future__ import annotations

from threading import Event, RLock
from time import time
from typing import Any

from robogame.communication.bus import EventBus, get_event_bus, new_request_id
from robogame.communication import events
from robogame.datahub.heartbeat import HeartbeatManager


class BaseModule:
    def __init__(self, name: str, bus: EventBus | None = None) -> None:
        self.name = name
        self.bus = bus or get_event_bus()
        self.heartbeat = HeartbeatManager(name, bus=self.bus)
        self._lock = RLock()
        self._acks: dict[str, dict[str, Any]] = {}
        self._ack_events: dict[str, Event] = {}
        self._returns: dict[str, dict[str, Any]] = {}
        self._return_events: dict[str, Event] = {}
        self.bus.subscribe(events.DATAHUB_ACK, self._on_ack)
        self.bus.subscribe(events.DATAHUB_DATA_RETURN, self._on_data_return)

    def start(self) -> None:
        self.heartbeat.start()

    def stop(self) -> None:
        self.heartbeat.stop()

    def write_data(self, key: str, value: Any, wait_ack: bool = True, timeout: float = 1.0) -> bool:
        request_id = new_request_id(self.name)
        ack_event = Event()
        with self._lock:
            self._ack_events[request_id] = ack_event
        self.bus.publish(
            events.DATAHUB_WRITE,
            self.name,
            request_id=request_id,
            key=key,
            value=value,
            timestamp=time(),
        )
        if not wait_ack:
            return True
        if not ack_event.wait(timeout):
            self._publish_communication_exception(key, "write")
            return False
        with self._lock:
            ack = self._acks.pop(request_id, {})
            self._ack_events.pop(request_id, None)
        return bool(ack.get("success"))

    def read_data(self, key: str, timeout: float = 1.0) -> tuple[Any, bool]:
        request_id = new_request_id(self.name)
        return_event = Event()
        with self._lock:
            self._return_events[request_id] = return_event
        self.bus.publish(events.DATAHUB_READ, self.name, request_id=request_id, key=key)
        if not return_event.wait(timeout):
            self._publish_communication_exception(key, "read")
            return None, False
        with self._lock:
            returned = self._returns.pop(request_id, {})
            self._return_events.pop(request_id, None)
        return returned.get("value"), True

    def publish_business_event(self, event_name: str, data_key: str, **payload: Any) -> None:
        self.bus.publish(event_name, self.name, request_id=new_request_id(self.name), data_key=data_key, **payload)

    def _on_ack(self, sender: str, payload: dict[str, Any]) -> None:
        if payload.get("target") != self.name:
            return
        request_id = str(payload.get("request_id"))
        with self._lock:
            self._acks[request_id] = payload
            event = self._ack_events.get(request_id)
        if event:
            event.set()

    def _on_data_return(self, sender: str, payload: dict[str, Any]) -> None:
        if payload.get("target") != self.name:
            return
        request_id = str(payload.get("request_id"))
        with self._lock:
            self._returns[request_id] = payload
            event = self._return_events.get(request_id)
        if event:
            event.set()

    def _publish_communication_exception(self, key: str, operation: str) -> None:
        self.bus.publish(events.DATAHUB_COMMUNICATION_EXCEPTION, self.name, key=key, operation=operation)
