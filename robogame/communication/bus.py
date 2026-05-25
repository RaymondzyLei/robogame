"""Blinker-backed event bus used by all RoboGame modules."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from blinker import Namespace

EventHandler = Callable[[str, dict[str, Any]], None]


def new_request_id(prefix: str = "req") -> str:
    return f"{prefix}_{uuid4().hex}"


class EventBus:
    """Small wrapper around Blinker signals.

    Business modules only communicate by publishing and subscribing events here.
    The wrapper keeps handler signatures consistent and hides Blinker details.
    """

    def __init__(self, namespace: Namespace | None = None) -> None:
        self._namespace = namespace or Namespace()

    def publish(self, event_name: str, sender: str, **payload: Any) -> None:
        self._namespace.signal(event_name).send(sender, payload=payload)

    def subscribe(self, event_name: str, handler: EventHandler) -> Callable[[], None]:
        signal = self._namespace.signal(event_name)

        def receiver(sender: str, **kwargs: Any) -> None:
            raw_payload = kwargs.get("payload", {})
            payload = raw_payload if isinstance(raw_payload, dict) else {}
            handler(sender, payload)

        signal.connect(receiver, weak=False)

        def unsubscribe() -> None:
            signal.disconnect(receiver)

        return unsubscribe


_default_bus = EventBus()


def get_event_bus() -> EventBus:
    return _default_bus
