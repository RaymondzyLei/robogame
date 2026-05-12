"""DataHub数据中心 - 全局数据唯一管理单元，线程安全"""
import threading
import time
import uuid
from typing import Any, Optional, Dict
from blinker import signal


class DataHub:
    """全局数据唯一管理单元，封装线程锁，仅通过Blinker事件触发内部数据读写"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._data: Dict[str, Any] = {}
        self._data_lock = threading.Lock()
        self._pending_reads: Dict[str, Any] = {}

        self._write_signal = signal('datahub:write')
        self._read_signal = signal('datahub:read')

        self._write_signal.connect(self._handle_write)
        self._read_signal.connect(self._handle_read)

    def _handle_write(self, sender, key: str, value: Any, timestamp: Optional[float] = None):
        """处理datahub:write事件"""
        if timestamp is None:
            timestamp = time.time()

        with self._data_lock:
            self._data[key] = {
                'value': value,
                'timestamp': timestamp
            }

    def _handle_read(self, sender, key: str, request_id: str):
        """处理datahub:read事件，返回数据给请求方"""
        with self._data_lock:
            data = self._data.get(key)

        data_return_signal = signal('datahub:data_return')

        if data:
            data_return_signal.send(
                self,
                request_id=request_id,
                key=key,
                value=data['value']
            )
        else:
            data_return_signal.send(
                self,
                request_id=request_id,
                key=key,
                value=None
            )

    def write(self, key: str, value: Any, timestamp: Optional[float] = None):
        """发送datahub:write事件"""
        if timestamp is None:
            timestamp = time.time()
        self._write_signal.send(self, key=key, value=value, timestamp=timestamp)

    def read(self, key: str, request_id: Optional[str] = None) -> str:
        """发送datahub:read事件，返回request_id用于关联返回数据"""
        if request_id is None:
            request_id = str(uuid.uuid4())
        self._read_signal.send(self, key=key, request_id=request_id)
        return request_id

    def get(self, key: str) -> Optional[Any]:
        """直接从DataHub读取数据（仅用于内部测试）"""
        with self._data_lock:
            data = self._data.get(key)
            return data['value'] if data else None

    def set(self, key: str, value: Any):
        """直接设置数据（仅用于内部测试）"""
        with self._data_lock:
            self._data[key] = {
                'value': value,
                'timestamp': time.time()
            }

    def clear(self):
        """清空所有数据（仅用于测试）"""
        with self._data_lock:
            self._data.clear()
            self._pending_reads.clear()


def get_datahub() -> DataHub:
    """获取DataHub单例"""
    return DataHub()