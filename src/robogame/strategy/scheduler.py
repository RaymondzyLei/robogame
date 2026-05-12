"""策略模块 - 任务调度与决策控制"""
import time
import uuid
from typing import Callable, Optional
from blinker import signal

from ..common.datahub import get_datahub
from ..common.events import (
    DataHubEvent, StrategyEvent, VisionEvent,
    CollectEvent, PlaceEvent, BuildEvent, ModuleEvent
)
from ..common.types import Position, TaskParam


class StrategyModule:
    """树莓派策略模块，负责任务调度、状态机管理与模块协同控制"""

    def __init__(self):
        self._datahub = get_datahub()
        self._running = False

        self._start_collect_signal = signal(StrategyEvent.START_COLLECT.value)
        self._start_place_signal = signal(StrategyEvent.START_PLACE.value)
        self._start_build_signal = signal(StrategyEvent.START_BUILD.value)
        self._adjust_param_signal = signal(StrategyEvent.ADJUST_RECOGNIZE_PARAM.value)
        self._module_retry_signal = signal(StrategyEvent.MODULE_RETRY.value)
        self._task_complete_signal = signal(StrategyEvent.TASK_COMPLETE.value)
        self._task_failed_signal = signal(StrategyEvent.TASK_FAILED.value)

        self._pending_reads: dict = {}
        self._current_task = 'collect'

        self._setup_listeners()

    def _setup_listeners(self):
        """设置所有事件监听"""
        data_return_signal = signal(DataHubEvent.DATA_RETURN.value)
        data_return_signal.connect(self._handle_data_return)

        vision_updated_signal = signal(VisionEvent.DATA_UPDATED.value)
        vision_updated_signal.connect(self._handle_vision_data_updated)

        collect_status_signal = signal(CollectEvent.STATUS_UPDATED.value)
        collect_status_signal.connect(self._handle_collect_status)

        place_status_signal = signal(PlaceEvent.STATUS_UPDATED.value)
        place_status_signal.connect(self._handle_place_status)

        build_status_signal = signal(BuildEvent.STATUS_UPDATED.value)
        build_status_signal.connect(self._handle_build_status)

        module_exception_signal = signal(ModuleEvent.EXCEPTION.value)
        module_exception_signal.connect(self._handle_module_exception)

    def _handle_data_return(self, sender, request_id: str, key: str, value):
        """处理datahub:data_return事件"""
        if request_id in self._pending_reads:
            callback = self._pending_reads.pop(request_id)
            callback(value)

    def _handle_vision_data_updated(self, sender, request_id: str, data_key: str):
        """处理视觉数据更新事件"""
        def handle_data(data):
            if data:
                print(f"[Strategy] Vision data updated: {data_key}")
        self._read_datahub(data_key, handle_data)

    def _handle_collect_status(self, sender, request_id: str, data_key: str):
        """处理收集模块状态更新"""
        def handle_data(data):
            if data:
                status = data if isinstance(data, dict) else {}
                code = status.get('code', -1)
                print(f"[Strategy] Collect status: code={code}, msg={status.get('msg', '')}")

                if code == 3:
                    self._start_place_module()
                elif code == -1:
                    error_code = status.get('error_code', 0)
                    self._handle_error('collect', error_code)
        self._read_datahub(data_key, handle_data)

    def _handle_place_status(self, sender, request_id: str, data_key: str):
        """处理放置模块状态更新"""
        def handle_data(data):
            if data:
                status = data if isinstance(data, dict) else {}
                code = status.get('code', -1)
                print(f"[Strategy] Place status: code={code}, msg={status.get('msg', '')}")

                if code == 3:
                    self._start_build_module()
                elif code == -1:
                    error_code = status.get('error_code', 0)
                    self._handle_error('place', error_code)
        self._read_datahub(data_key, handle_data)

    def _handle_build_status(self, sender, request_id: str, data_key: str):
        """处理搭建模块状态更新"""
        def handle_data(data):
            if data:
                status = data if isinstance(data, dict) else {}
                code = status.get('code', -1)
                print(f"[Strategy] Build status: code={code}, msg={status.get('msg', '')}")

                if code == 3:
                    self._task_completed()
                elif code == -1:
                    error_code = status.get('error_code', 0)
                    self._handle_error('build', error_code)
        self._read_datahub(data_key, handle_data)

    def _handle_module_exception(self, sender, request_id: str, data_key: str):
        """处理模块异常事件"""
        def handle_data(data):
            if data:
                print(f"[Strategy] Module exception: {data}")
        self._read_datahub(data_key, handle_data)

    def _write_datahub(self, key: str, value):
        """向DataHub写入数据"""
        self._datahub.write(key, value)

    def _read_datahub(self, key: str, callback: Callable):
        """从DataHub读取数据"""
        request_id = str(uuid.uuid4())
        self._pending_reads[request_id] = callback
        self._datahub.read(key, request_id)

    def init_task(self, task_param: dict):
        """初始化任务参数"""
        self._write_datahub('strategy:task_param', task_param)

    def start_collect_module(self, collect_param: dict):
        """启动收集模块"""
        self._current_task = 'collect'

        self._write_datahub('strategy:collect_param', collect_param)

        request_id = str(uuid.uuid4())
        self._start_collect_signal.send(self, request_id=request_id, data_key='strategy:collect_param')

        print("[Strategy] Started collect module")

    def _start_place_module(self):
        """启动放置模块"""
        self._current_task = 'place'

        place_param = self._datahub.get('strategy:place_param') or {}
        self._write_datahub('strategy:place_param', place_param)

        request_id = str(uuid.uuid4())
        self._start_place_signal.send(self, request_id=request_id, data_key='strategy:place_param')

        print("[Strategy] Started place module")

    def _start_build_module(self):
        """启动搭建模块"""
        self._current_task = 'build'

        build_param = self._datahub.get('strategy:build_param') or {}
        self._write_datahub('strategy:build_param', build_param)

        request_id = str(uuid.uuid4())
        self._start_build_signal.send(self, request_id=request_id, data_key='strategy:build_param')

        print("[Strategy] Started build module")

    def _handle_error(self, module: str, error_code: int):
        """处理模块错误"""
        retry_param = {
            'module': module,
            'error_code': error_code,
            'retry_count': 0,
            'max_retry': 3
        }

        self._write_datahub('strategy:error_info', retry_param)

        request_id = str(uuid.uuid4())
        self._module_retry_signal.send(self, request_id=request_id, data_key='strategy:error_info')

    def _task_completed(self):
        """任务完成"""
        result = {
            'status': 'completed',
            'final_module': self._current_task,
            'timestamp': time.time()
        }

        self._write_datahub('strategy:task_result', result)

        request_id = str(uuid.uuid4())
        self._task_complete_signal.send(self, request_id=request_id, data_key='strategy:task_result')

        print("[Strategy] Task completed!")

    def start(self):
        """启动策略模块"""
        self._running = True
        print("[Strategy] Strategy module started")

    def stop(self):
        """停止策略模块"""
        self._running = False
        print("[Strategy] Strategy module stopped")

    def on_vision_data_updated(self, callback: Callable):
        """注册视觉数据更新回调"""
        signal(VisionEvent.DATA_UPDATED.value).connect(callback)

    def on_collect_status(self, callback: Callable):
        """注册收集状态回调"""
        signal(CollectEvent.STATUS_UPDATED.value).connect(callback)

    def on_place_status(self, callback: Callable):
        """注册放置状态回调"""
        signal(PlaceEvent.STATUS_UPDATED.value).connect(callback)

    def on_build_status(self, callback: Callable):
        """注册搭建状态回调"""
        signal(BuildEvent.STATUS_UPDATED.value).connect(callback)

    def on_module_exception(self, callback: Callable):
        """注册模块异常回调"""
        signal(ModuleEvent.EXCEPTION.value).connect(callback)


def get_strategy_module() -> StrategyModule:
    """获取策略模块单例"""
    return StrategyModule()