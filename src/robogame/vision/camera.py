"""视觉模块 - 环境感知单元"""
import time
import uuid
from typing import Optional, Callable
from blinker import signal

from ..common.datahub import get_datahub
from ..common.events import DataHubEvent, VisionEvent
from ..common.types import Pose, CubeInfo, Position


class VisionModule:
    """视觉模块，负责图像采集、目标识别与位姿反馈"""

    def __init__(self):
        self._datahub = get_datahub()
        self._running = False

        self._data_updated_signal = signal(VisionEvent.DATA_UPDATED.value)
        self._grab_check_done_signal = signal(VisionEvent.GRAB_CHECK_DONE.value)
        self._place_check_done_signal = signal(VisionEvent.PLACE_CHECK_DONE.value)
        self._build_check_done_signal = signal(VisionEvent.BUILD_CHECK_DONE.value)
        self._adjust_param_signal = signal(VisionEvent.ADJUST_PARAM.value)

        self._pending_reads: dict = {}

        self._setup_datahub_listeners()

    def _setup_datahub_listeners(self):
        """设置DataHub返回数据监听"""
        data_return_signal = signal(DataHubEvent.DATA_RETURN.value)
        data_return_signal.connect(self._handle_data_return)

    def _handle_data_return(self, sender, request_id: str, key: str, value):
        """处理datahub:data_return事件"""
        if request_id in self._pending_reads:
            callback = self._pending_reads.pop(request_id)
            callback(value)

    def _write_datahub(self, key: str, value):
        """向DataHub写入数据"""
        self._datahub.write(key, value)

    def _read_datahub(self, key: str, callback: Callable):
        """从DataHub读取数据"""
        request_id = str(uuid.uuid4())
        self._pending_reads[request_id] = callback
        self._datahub.read(key, request_id)

    def update_cube_position(self, cube_id: int, position: Position, pose: Optional[Pose] = None):
        """更新方块位置数据"""
        cube_info = {
            'cube_id': cube_id,
            'position': {'x': position.x, 'y': position.y, 'z': position.z},
            'pose': {
                'yaw': pose.yaw if pose else 0,
                'pitch': pose.pitch if pose else 0,
                'roll': pose.roll if pose else 0
            } if pose else None,
            'detected': True,
            'timestamp': time.time()
        }

        self._write_datahub('vision:cube_position', cube_info)

        request_id = str(uuid.uuid4())
        self._data_updated_signal.send(self, request_id=request_id, data_key='vision:cube_position')

    def update_check_result(self, check_type: str, result: bool, error: float = 0):
        """更新校验结果"""
        check_result = {
            'type': check_type,
            'result': result,
            'error': error,
            'timestamp': time.time()
        }

        key = f'vision:{check_type}_check_result'
        self._write_datahub(key, check_result)

        request_id = str(uuid.uuid4())

        if check_type == 'grab':
            self._grab_check_done_signal.send(self, request_id=request_id, data_key=key)
        elif check_type == 'place':
            self._place_check_done_signal.send(self, request_id=request_id, data_key=key)
        elif check_type == 'build':
            self._build_check_done_signal.send(self, request_id=request_id, data_key=key)

    def request_adjust_param(self, callback: Callable):
        """请求调整识别参数"""
        self._read_datahub('strategy:recognize_param', callback)

    def start(self):
        """启动视觉模块"""
        self._running = True

    def stop(self):
        """停止视觉模块"""
        self._running = False

    def on_data_updated(self, callback: Callable):
        """注册数据更新回调"""
        self._data_updated_signal.connect(callback)

    def on_grab_check_done(self, callback: Callable):
        """注册抓取校验完成回调"""
        self._grab_check_done_signal.connect(callback)

    def on_place_check_done(self, callback: Callable):
        """注册放置校验完成回调"""
        self._place_check_done_signal.connect(callback)

    def on_build_check_done(self, callback: Callable):
        """注册搭建校验完成回调"""
        self._build_check_done_signal.connect(callback)

    def on_adjust_param(self, callback: Callable):
        """注册参数调整回调"""
        self._adjust_param_signal.connect(callback)


def get_vision_module() -> VisionModule:
    """获取视觉模块单例"""
    return VisionModule()