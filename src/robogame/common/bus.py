import time
from typing import Callable, Any
from collections import defaultdict
from threading import Lock
from .msg import Message, MessageType


class MessageBus:
    """消息总线 - 核心通信枢纽"""

    def __init__(self):
        self._subscribers: dict[MessageType, list[Callable[[Message], None]]] = defaultdict(list)
        self._lock = Lock()
        self._message_history: list[Message] = []
        self._max_history = 1000

    def subscribe(self, msg_type: MessageType, callback: Callable[[Message], None]) -> None:
        """订阅特定类型消息"""
        with self._lock:
            self._subscribers[msg_type].append(callback)

    def unsubscribe(self, msg_type: MessageType, callback: Callable[[Message], None]) -> None:
        """取消订阅"""
        with self._lock:
            if callback in self._subscribers[msg_type]:
                self._subscribers[msg_type].remove(callback)

    def publish(self, message: Message) -> None:
        """发布消息"""
        message.timestamp = time.time()

        with self._lock:
            self._message_history.append(message)
            if len(self._message_history) > self._max_history:
                self._message_history.pop(0)

            callbacks = list(self._subscribers.get(message.type, []))

        for callback in callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Message callback error: {e}")

    def get_history(self, msg_type: MessageType | None = None, limit: int = 100) -> list[Message]:
        """获取消息历史"""
        with self._lock:
            if msg_type is None:
                return self._message_history[-limit:]
            return [m for m in self._message_history if m.type == msg_type][-limit:]


_bus: MessageBus | None = None


def get_bus() -> MessageBus:
    """获取全局消息总线单例"""
    global _bus
    if _bus is None:
        _bus = MessageBus()
    return _bus