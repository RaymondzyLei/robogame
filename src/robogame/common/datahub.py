"""DataHub数据中心 - 全局数据唯一管理单元，线程安全，支持订阅推送、心跳、持久化"""
import json
import os
import threading
import time
import uuid
from typing import Any, Optional, Dict, Callable, List
from blinker import signal


class DataHub:
    """全局数据唯一管理单元，封装线程锁，支持：
    - 订阅推送模式：模块订阅指定key，数据变更时自动推送
    - 事件ACK+超时重传：write/read操作需要ACK，超时自动重传
    - 心跳监控：监控模块在线状态
    - 轻量持久化：关键数据自动存JSON文件，重启可恢复
    """

    _instance = None
    _lock = threading.Lock()
    _init_kwargs = None  # 存储初始化参数

    # 默认配置
    DEFAULT_ACK_TIMEOUT = 1.0  # ACK超时时间（秒）
    DEFAULT_MAX_RETRIES = 2    # 最大重传次数
    HEARTBEAT_INTERVAL = 1.0   # 心跳间隔（秒）
    HEARTBEAT_TIMEOUT = 5.0    # 心跳超时时间（秒）

    def __new__(cls, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._init_kwargs = kwargs
        return cls._instance

    def __init__(self, persistence_dir: Optional[str] = None):
        if self._initialized:
            return
        self._initialized = True

        # 使用存储的初始化参数
        init_kwargs = DataHub._init_kwargs or {}
        persistence_dir = persistence_dir or init_kwargs.get('persistence_dir')

        self._data: Dict[str, Any] = {}
        self._data_lock = threading.Lock()

        # 持久化配置
        self._persistence_dir = persistence_dir or 'data'
        self._persistence_keys = [
            'strategy:task_param', 'strategy:collect_param', 'strategy:place_param', 'strategy:build_param',
            'module:error_info', 'collect:status', 'place:status', 'build:status'
        ]

        # 订阅推送相关
        self._subscribers: Dict[str, List[Callable]] = {}  # key -> [callback, ...]
        self._subscriber_lock = threading.Lock()

        # ACK+重传相关
        self._pending_acks: Dict[str, Dict] = {}  # request_id -> {key, value, timestamp, retries}
        self._ack_lock = threading.Lock()
        self._ack_timeout = self.DEFAULT_ACK_TIMEOUT
        self._max_retries = self.DEFAULT_MAX_RETRIES

        # 心跳监控相关
        self._module_heartbeat: Dict[str, float] = {}  # module_name -> last_heartbeat_time
        self._heartbeat_lock = threading.Lock()
        self._offline_modules: List[str] = []
        self._safety_triggered = False

        # Blinker信号
        self._write_signal = signal('datahub:write')
        self._read_signal = signal('datahub:read')
        self._ack_signal = signal('datahub:ack')
        self._data_changed_signal = signal('datahub:data_changed')

        # 连接事件处理器
        self._write_signal.connect(self._handle_write)
        self._read_signal.connect(self._handle_read)

        # 启动后台任务
        self._running = False
        self._background_thread: Optional[threading.Thread] = None

        # 加载持久化数据
        self._load_persistence()

    def start(self):
        """启动DataHub后台任务（心跳检测、ACK检测）"""
        if self._running:
            return
        self._running = True
        self._background_thread = threading.Thread(target=self._background_task, daemon=True)
        self._background_thread.start()

    def stop(self):
        """停止DataHub后台任务"""
        self._running = False
        if self._background_thread:
            self._background_thread.join(timeout=2.0)

    def _background_task(self):
        """后台任务：心跳检测、ACK超时检测、持久化"""
        while self._running:
            try:
                now = time.time()

                # 心跳检测
                self._check_heartbeat(now)

                # ACK超时检测
                self._check_pending_acks(now)

                # 定期持久化
                self._auto_persist()

                time.sleep(0.1)  # 100ms周期
            except Exception as e:
                print(f"[DataHub] Background task error: {e}")

    def _check_heartbeat(self, now: float):
        """检测心跳超时"""
        with self._heartbeat_lock:
            offline_modules = []
            for module, last_time in self._module_heartbeat.items():
                if now - last_time > self.HEARTBEAT_TIMEOUT:
                    offline_modules.append(module)

            for module in offline_modules:
                if module not in self._offline_modules:
                    self._offline_modules.append(module)
                    print(f"[DataHub] Module offline: {module}")
                    self._trigger_safety_mechanism(module)

    def _check_pending_acks(self, now: float):
        """检测ACK超时，进行重传"""
        with self._ack_lock:
            expired = []
            for request_id, pending in self._pending_acks.items():
                if now - pending['timestamp'] > self._ack_timeout:
                    expired.append((request_id, pending))

            for request_id, pending in expired:
                if pending['retries'] < self._max_retries:
                    # 重传
                    pending['retries'] += 1
                    pending['timestamp'] = now
                    print(f"[DataHub] Retrying {pending['type']} for key={pending['key']}, attempt {pending['retries']}")

                    if pending['type'] == 'write':
                        self._write_signal.send(self, key=pending['key'], value=pending['value'],
                                               timestamp=now, request_id=request_id, is_retry=True)
                    else:
                        self._read_signal.send(self, key=pending['key'],
                                               request_id=request_id, is_retry=True)
                else:
                    # 超过最大重传次数，上报通信异常
                    print(f"[DataHub] ACK timeout, max retries exceeded for {pending['key']}")
                    self._pending_acks.pop(request_id, None)
                    self._report_communication_exception(pending['key'], pending.get('type', 'unknown'))

    def _report_communication_exception(self, key: str, operation: str):
        """上报通信异常"""
        error_info = {
            'error_code': 4,
            'error_type': 'communication_fail',
            'desc': f'{operation} operation timeout for key={key}',
            'timestamp': time.time()
        }
        self._data['module:error_info'] = {
            'value': error_info,
            'timestamp': time.time()
        }
        signal('datahub:communication_exception').send(self, key=key, operation=operation)

    def _trigger_safety_mechanism(self, offline_module: str):
        """触发安全机制"""
        self._safety_triggered = True
        print(f"[DataHub] Safety mechanism triggered for offline module: {offline_module}")

        # 发送安全停机事件
        signal('datahub:safety_shutdown').send(self, module=offline_module)

    def _handle_write(self, sender, key: str, value: Any, timestamp: Optional[float] = None,
                      request_id: Optional[str] = None, is_retry: bool = False):
        """处理datahub:write事件"""
        if timestamp is None:
            timestamp = time.time()
        if request_id is None:
            request_id = str(uuid.uuid4())

        old_value = self._data.get(key, {}).get('value')

        with self._data_lock:
            self._data[key] = {
                'value': value,
                'timestamp': timestamp
            }

        # 如果不是重传，添加ACK跟踪
        if not is_retry:
            with self._ack_lock:
                self._pending_acks[request_id] = {
                    'type': 'write',
                    'key': key,
                    'value': value,
                    'timestamp': timestamp,
                    'retries': 0
                }

        # 发送ACK
        self._ack_signal.send(self, request_id=request_id, key=key, success=True)

        # 如果数据变化，触发订阅推送
        if old_value != value:
            self._notify_subscribers(key, value)

        # 触发数据变更事件
        self._data_changed_signal.send(self, key=key, value=value)

    def _handle_read(self, sender, key: str, request_id: str, is_retry: bool = False):
        """处理datahub:read事件，返回数据给请求方"""
        with self._data_lock:
            data = self._data.get(key)

        if not is_retry:
            with self._ack_lock:
                self._pending_acks[request_id] = {
                    'type': 'read',
                    'key': key,
                    'timestamp': time.time(),
                    'retries': 0
                }

        data_return_signal = signal('datahub:data_return')

        if data:
            data_return_signal.send(self, request_id=request_id, key=key, value=data['value'])
        else:
            data_return_signal.send(self, request_id=request_id, key=key, value=None)

        # 发送ACK
        self._ack_signal.send(self, request_id=request_id, key=key, success=True)

    def _notify_subscribers(self, key: str, value: Any):
        """通知订阅者数据变化"""
        with self._subscriber_lock:
            callbacks = self._subscribers.get(key, [])

        for callback in callbacks:
            try:
                callback(key, value)
            except Exception as e:
                print(f"[DataHub] Subscriber callback error: {e}")

    def subscribe(self, key: str, callback: Callable):
        """订阅指定key的数据变化"""
        with self._subscriber_lock:
            if key not in self._subscribers:
                self._subscribers[key] = []
            if callback not in self._subscribers[key]:
                self._subscribers[key].append(callback)
        print(f"[DataHub] Subscribed to key: {key}")

    def unsubscribe(self, key: str, callback: Callable):
        """取消订阅"""
        with self._subscriber_lock:
            if key in self._subscribers and callback in self._subscribers[key]:
                self._subscribers[key].remove(callback)

    def write(self, key: str, value: Any, timestamp: Optional[float] = None,
              request_id: Optional[str] = None, wait_ack: bool = True) -> str:
        """发送datahub:write事件，wait_ack表示是否等待ACK"""
        if timestamp is None:
            timestamp = time.time()
        if request_id is None:
            request_id = str(uuid.uuid4())

        self._write_signal.send(self, key=key, value=value, timestamp=timestamp, request_id=request_id)
        return request_id

    def read(self, key: str, request_id: Optional[str] = None, wait_ack: bool = True) -> str:
        """发送datahub:read事件，返回request_id"""
        if request_id is None:
            request_id = str(uuid.uuid4())
        self._read_signal.send(self, key=key, request_id=request_id)
        return request_id

    def write_with_ack(self, key: str, value: Any, timeout: Optional[float] = None) -> bool:
        """同步写入，等待ACK，超时返回False"""
        timeout = timeout or self._ack_timeout
        request_id = str(uuid.uuid4())
        result = {'received': False}

        def on_ack(sender, request_id, key, success):
            if request_id == request_id:
                result['received'] = True

        ack_signal = signal('datahub:ack')
        ack_signal.connect(on_ack)

        self._write_signal.send(self, key=key, value=value, timestamp=time.time(), request_id=request_id)

        start = time.time()
        while time.time() - start < timeout:
            if result['received']:
                return True
            time.sleep(0.01)

        return False

    def read_with_ack(self, key: str, timeout: Optional[float] = None) -> tuple:
        """同步读取，等待数据返回，超时返回(None, False)"""
        timeout = timeout or self._ack_timeout
        request_id = str(uuid.uuid4())
        result = {'value': None, 'received': False}

        def on_data_return(sender, req_id, key, value):
            if req_id == request_id:
                result['value'] = value
                result['received'] = True

        data_return_signal = signal('datahub:data_return')
        data_return_signal.connect(on_data_return)

        self._read_signal.send(self, key=key, request_id=request_id)

        start = time.time()
        while time.time() - start < timeout:
            if result['received']:
                return result['value'], True
            time.sleep(0.01)

        return None, False

    def update_heartbeat(self, module_name: str):
        """更新模块心跳"""
        with self._heartbeat_lock:
            self._module_heartbeat[module_name] = time.time()
            if module_name in self._offline_modules:
                self._offline_modules.remove(module_name)
                print(f"[DataHub] Module online: {module_name}")

    def get_module_status(self, module_name: str) -> str:
        """获取模块在线状态"""
        with self._heartbeat_lock:
            if module_name in self._offline_modules:
                return 'offline'
            if module_name in self._module_heartbeat:
                return 'online'
            return 'unknown'

    def is_safety_triggered(self) -> bool:
        """检查安全机制是否被触发"""
        return self._safety_triggered

    def _load_persistence(self):
        """加载持久化数据"""
        if not os.path.exists(self._persistence_dir):
            return

        state_file = os.path.join(self._persistence_dir, 'datahub_state.json')
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    with self._data_lock:
                        for key, value in state.items():
                            self._data[key] = value
                    print(f"[DataHub] Loaded persistence data: {len(state)} keys")
            except Exception as e:
                print(f"[DataHub] Failed to load persistence: {e}")

    def _auto_persist(self):
        """自动持久化关键数据"""
        with self._data_lock:
            state = {key: self._data[key] for key in self._persistence_keys if key in self._data}

        if state:
            try:
                os.makedirs(self._persistence_dir, exist_ok=True)
                state_file = os.path.join(self._persistence_dir, 'datahub_state.json')
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[DataHub] Failed to persist: {e}")

    def persist_now(self):
        """立即持久化所有关键数据"""
        self._auto_persist()

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
        self._notify_subscribers(key, value)

    def clear(self):
        """清空所有数据（仅用于测试）"""
        with self._data_lock:
            self._data.clear()
        with self._ack_lock:
            self._pending_acks.clear()


def get_datahub(persistence_dir: Optional[str] = None) -> DataHub:
    """获取DataHub单例"""
    if persistence_dir:
        return DataHub(persistence_dir=persistence_dir)
    return DataHub()