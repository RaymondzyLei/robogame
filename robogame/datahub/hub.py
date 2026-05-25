"""Thread-safe DataHub driven only by EventBus events."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path
from threading import RLock
from time import time
from typing import Any

from robogame.communication.bus import EventBus, get_event_bus
from robogame.communication import events

DataChangedHandler = Callable[[str, Any], None]


class DataHub:
    """Global data center.

    Public methods are for bootstrapping, diagnostics, and tests. Runtime business
    modules should use ``datahub:write`` and ``datahub:read`` events instead.
    """

    def __init__(
        self,
        bus: EventBus | None = None,
        persistence_dir: str | Path | None = None,
        persistent_keys: Iterable[str] | None = None,
    ) -> None:
        self.bus = bus or get_event_bus()
        self._lock = RLock()
        self._data: dict[str, Any] = {}
        self._subscriptions: dict[str, list[DataChangedHandler]] = defaultdict(list)
        self._persistent_keys = set(persistent_keys or ())
        self._persistence_dir = Path(persistence_dir) if persistence_dir else None
        if self._persistence_dir:
            self._persistence_dir.mkdir(parents=True, exist_ok=True)
            self._load_persisted()
        self.bus.subscribe(events.DATAHUB_WRITE, self._handle_write_event)
        self.bus.subscribe(events.DATAHUB_READ, self._handle_read_event)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def subscribe_key(self, key: str, handler: DataChangedHandler) -> Callable[[], None]:
        with self._lock:
            self._subscriptions[key].append(handler)

        def unsubscribe() -> None:
            with self._lock:
                if handler in self._subscriptions[key]:
                    self._subscriptions[key].remove(handler)

        return unsubscribe

    def persist_now(self) -> None:
        if not self._persistence_dir:
            return
        with self._lock:
            for key in self._persistent_keys:
                if key in self._data:
                    self._write_key_file(key, self._data[key])

    def _handle_write_event(self, sender: str, payload: dict[str, Any]) -> None:
        key = str(payload.get("key", ""))
        request_id = payload.get("request_id")
        if not key:
            self._ack(sender, request_id, key, False, "missing key")
            return

        value = payload.get("value")
        timestamp = payload.get("timestamp", time())
        with self._lock:
            self._data[key] = {"value": value, "timestamp": timestamp, "writer": sender}
            handlers = list(self._subscriptions.get(key, ()))
            if key in self._persistent_keys:
                self._write_key_file(key, self._data[key])

        self._ack(sender, request_id, key, True)
        self.bus.publish(events.DATAHUB_DATA_CHANGED, "datahub", key=key, value=value, timestamp=timestamp)
        for handler in handlers:
            handler(key, value)

    def _handle_read_event(self, sender: str, payload: dict[str, Any]) -> None:
        key = str(payload.get("key", ""))
        request_id = payload.get("request_id")
        if not key:
            self._ack(sender, request_id, key, False, "missing key")
            return

        with self._lock:
            entry = self._data.get(key)
        value = entry.get("value") if isinstance(entry, dict) else None
        timestamp = entry.get("timestamp") if isinstance(entry, dict) else None
        self.bus.publish(
            events.DATAHUB_DATA_RETURN,
            "datahub",
            target=sender,
            request_id=request_id,
            key=key,
            value=value,
            timestamp=timestamp,
        )
        self._ack(sender, request_id, key, True)

    def _ack(self, target: str, request_id: Any, key: str, success: bool, error: str | None = None) -> None:
        self.bus.publish(
            events.DATAHUB_ACK,
            "datahub",
            target=target,
            request_id=request_id,
            key=key,
            success=success,
            error=error,
        )

    def _load_persisted(self) -> None:
        assert self._persistence_dir is not None
        for file_path in self._persistence_dir.glob("*.json"):
            key = file_path.stem.replace("__", ":")
            try:
                self._data[key] = json.loads(file_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue

    def _write_key_file(self, key: str, entry: Any) -> None:
        if not self._persistence_dir:
            return
        file_path = self._persistence_dir / f"{key.replace(':', '__')}.json"
        file_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")


_default_datahub: DataHub | None = None


def get_datahub(
    bus: EventBus | None = None,
    persistence_dir: str | Path | None = None,
    persistent_keys: Iterable[str] | None = None,
) -> DataHub:
    global _default_datahub
    if _default_datahub is None:
        _default_datahub = DataHub(bus=bus, persistence_dir=persistence_dir, persistent_keys=persistent_keys)
    return _default_datahub
