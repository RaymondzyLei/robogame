"""收集方块模块 - 动作执行与状态反馈"""
import time
import uuid
from typing import Callable
from blinker import signal

from ...common.datahub import get_datahub
from ...common.events import (
    DataHubEvent, CollectEvent, VisionEvent, ModuleEvent, StrategyEvent
)
from ...common.types import StatusCode, ErrorCode, ModuleStatus


class CollectModule:
    """收集方块模块，负责控制机械臂执行抓取动作"""

    def __init__(self):
        self._datahub = get_datahub()
        self._running = False

        self._status_updated_signal = signal(CollectEvent.STATUS_UPDATED.value)
        self._init_complete_signal = signal(CollectEvent.INIT_COMPLETE.value)
        self._navigating_signal = signal(CollectEvent.NAVIGATING.value)
        self._grabbing_signal = signal(CollectEvent.GRABBING.value)
        self._task_complete_signal = signal(CollectEvent.TASK_COMPLETE.value)
        self._exception_signal = signal(CollectEvent.EXCEPTION.value)

        self._pending_reads: dict = {}
        self._current_status = None
        self._state = StatusCode.INIT

        self._setup_listeners()

    def _setup_listeners(self):
        """设置事件监听"""
        data_return_signal = signal(DataHubEvent.DATA_RETURN.value)
        data_return_signal.connect(self._handle_data_return)

        start_signal = signal(StrategyEvent.START_COLLECT.value)
        start_signal.connect(self._handle_start_collect)

        vision_grab_check_signal = signal(VisionEvent.GRAB_CHECK_DONE.value)
        vision_grab_check_signal.connect(self._handle_grab_check_done)

        module_retry_signal = signal(StrategyEvent.MODULE_RETRY.value)
        module_retry_signal.connect(self._handle_module_retry)

    def _handle_data_return(self, sender, request_id: str, key: str, value):
        """处理datahub:data_return事件"""
        if request_id in self._pending_reads:
            callback = self._pending_reads.pop(request_id)
            callback(value)

    def _handle_start_collect(self, sender, request_id: str, data_key: str):
        """处理启动收集模块事件"""
        def handle_param(param):
            if param:
                print(f"[Collect] Received collect param: {param}")
                self._execute_init_state(param)
            else:
                self._send_exception(ErrorCode.COMMUNICATION_FAIL, "Failed to get collect param")

        self._read_datahub(data_key, handle_param)

    def _handle_grab_check_done(self, sender, request_id: str, data_key: str):
        """处理抓取校验完成事件"""
        def handle_check_result(result):
            if result:
                print(f"[Collect] Grab check result: {result}")
                check_passed = result.get('result', False)
                if check_passed and self._state == StatusCode.ACTION:
                    self._transition_to_complete()
                elif not check_passed:
                    self._send_exception(ErrorCode.ACTION_FAIL, "Grab check failed")
            else:
                self._send_exception(ErrorCode.COMMUNICATION_FAIL, "Failed to get grab check result")

        self._read_datahub(data_key, handle_check_result)

    def _handle_module_retry(self, sender, request_id: str, data_key: str):
        """处理模块重试事件"""
        def handle_retry_param(param):
            if param:
                module = param.get('module', '')
                if module == 'collect':
                    print(f"[Collect] Retrying, count: {param.get('retry_count', 0)}")
                    self._state = StatusCode.INIT
                    self._execute_init_state(param)
        self._read_datahub(data_key, handle_retry_param)

    def _write_datahub(self, key: str, value):
        """向DataHub写入数据"""
        self._datahub.write(key, value)

    def _read_datahub(self, key: str, callback: Callable):
        """从DataHub读取数据"""
        request_id = str(uuid.uuid4())
        self._pending_reads[request_id] = callback
        self._datahub.read(key, request_id)

    def _update_status(self, code: int, msg: str, error_code: int = ErrorCode.NONE):
        """更新模块状态"""
        self._current_status = ModuleStatus(code=code, msg=msg, error_code=error_code)
        self._write_datahub('collect:status', self._current_status.to_dict())

        request_id = str(uuid.uuid4())
        self._status_updated_signal.send(self, request_id=request_id, data_key='collect:status')

    def _send_exception(self, error_code: int, desc: str):
        """发送异常事件"""
        error_info = {
            'error_code': error_code,
            'error_type': self._get_error_type(error_code),
            'desc': desc,
            'timestamp': time.time()
        }

        self._write_datahub('module:error_info', error_info)

        request_id = str(uuid.uuid4())
        self._exception_signal.send(self, request_id=request_id, data_key='module:error_info')

        self._update_status(StatusCode.ERROR, desc, error_code)

    def _get_error_type(self, error_code: int) -> str:
        """获取错误类型名称"""
        error_types = {
            ErrorCode.VISION_FAIL: 'vision_fail',
            ErrorCode.NAVIGATION_FAIL: 'navigation_fail',
            ErrorCode.ACTION_FAIL: 'action_fail',
            ErrorCode.COMMUNICATION_FAIL: 'communication_fail',
            ErrorCode.TIMEOUT: 'timeout'
        }
        return error_types.get(error_code, 'unknown')

    def _transition_to_complete(self):
        """转换到完成状态"""
        self._state = StatusCode.COMPLETE
        self._update_status(StatusCode.COMPLETE, "Collect task completed", ErrorCode.NONE)

        request_id = str(uuid.uuid4())
        self._task_complete_signal.send(self, request_id=request_id, data_key='collect:status')

    def _execute_init_state(self, param: dict):
        """执行初始化定位状态"""
        self._state = StatusCode.INIT
        self._update_status(StatusCode.INIT, "Initializing", ErrorCode.NONE)

        target_position = param.get('target_position', {})
        print(f"[Collect] Initializing, target: {target_position}")

        request_id = str(uuid.uuid4())
        self._init_complete_signal.send(self, request_id=request_id, data_key='collect:status')

        self._state = StatusCode.NAVIGATE
        self._execute_navigate_state(param)

    def _execute_navigate_state(self, param: dict):
        """执行导航状态"""
        self._update_status(StatusCode.NAVIGATE, "Navigating to target", ErrorCode.NONE)

        request_id = str(uuid.uuid4())
        self._navigating_signal.send(self, request_id=request_id, data_key='collect:status')

        target_position = param.get('target_position', {})
        print(f"[Collect] Navigating to {target_position}")

        self._state = StatusCode.ACTION
        self._execute_action_state(param)

    def _execute_action_state(self, param: dict):
        """执行抓取动作状态"""
        self._update_status(StatusCode.ACTION, "Grabbing cube", ErrorCode.NONE)

        request_id = str(uuid.uuid4())
        self._grabbing_signal.send(self, request_id=request_id, data_key='collect:status')

        print("[Collect] Executing grab action")

    def start(self):
        """启动收集模块"""
        self._running = True
        print("[Collect] Collect module started")

    def stop(self):
        """停止收集模块"""
        self._running = False
        print("[Collect] Collect module stopped")

    def on_status_updated(self, callback: Callable):
        """注册状态更新回调"""
        self._status_updated_signal.connect(callback)

    def on_task_complete(self, callback: Callable):
        """注册任务完成回调"""
        self._task_complete_signal.connect(callback)

    def on_exception(self, callback: Callable):
        """注册异常回调"""
        self._exception_signal.connect(callback)


def get_collect_module() -> CollectModule:
    """获取收集模块单例"""
    return CollectModule()