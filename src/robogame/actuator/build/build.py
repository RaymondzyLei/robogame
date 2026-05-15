"""搭建方块模块 - 动作执行与状态反馈"""
import time
import uuid
from typing import Callable, Optional
from blinker import signal

from ...common.datahub import get_datahub
from ...common.events import (
    DataHubEvent, BuildEvent, VisionEvent, ModuleEvent, StrategyEvent
)
from ...common.types import StatusCode, ErrorCode, ModuleStatus
from ...hardware.motion import MotionController, get_motion_controller, ArmController, get_arm_controller
from ...hardware.gripper import GripperController, get_gripper_controller


class BuildModule:
    """搭建方块模块，负责控制机器人执行多层搭建动作"""

    def __init__(self,
                 left_motor_channel: int = 0,
                 right_motor_channel: int = 1,
                 gripper_channel: int = 2,
                 arm_channels: tuple = (3, 4, 5, 6)):
        """初始化搭建模块

        Args:
            left_motor_channel: 左轮电机PWM通道
            right_motor_channel: 右轮电机PWM通道
            gripper_channel: 机械爪伺服PWM通道
            arm_channels: 机械臂控制通道元组 (base, shoulder, elbow, wrist)
        """
        self._datahub = get_datahub()
        self._running = False

        # 硬件控制器（从模块化运动控制获取）
        self._motion = get_motion_controller(left_motor_channel, right_motor_channel)
        self._gripper = get_gripper_controller(gripper_channel)
        self._arm = get_arm_controller(*arm_channels)

        # 事件信号
        self._status_updated_signal = signal(BuildEvent.STATUS_UPDATED.value)
        self._init_complete_signal = signal(BuildEvent.INIT_COMPLETE.value)
        self._navigating_signal = signal(BuildEvent.NAVIGATING.value)
        self._building_signal = signal(BuildEvent.BUILDING.value)
        self._task_complete_signal = signal(BuildEvent.TASK_COMPLETE.value)
        self._exception_signal = signal(BuildEvent.EXCEPTION.value)

        self._pending_reads: dict = {}
        self._current_status: Optional[ModuleStatus] = None
        self._state = StatusCode.INIT
        self._target_position: Optional[dict] = None
        self._current_layer: int = 0

        self._setup_listeners()

    def _setup_listeners(self):
        """设置事件监听"""
        signal(DataHubEvent.DATA_RETURN.value).connect(self._handle_data_return)
        signal(StrategyEvent.START_BUILD.value).connect(self._handle_start_build)
        signal(VisionEvent.BUILD_CHECK_DONE.value).connect(self._handle_build_check_done)
        signal(StrategyEvent.MODULE_RETRY.value).connect(self._handle_module_retry)

    def _handle_data_return(self, sender, request_id: str, key: str, value):
        """处理datahub:data_return事件"""
        if request_id in self._pending_reads:
            callback = self._pending_reads.pop(request_id)
            callback(value)

    def _handle_start_build(self, sender, request_id: str, data_key: str):
        """处理启动搭建模块事件"""
        def handle_param(param):
            if param:
                print(f"[Build] Received build param: {param}")
                self._execute_init_state(param)
            else:
                self._send_exception(ErrorCode.COMMUNICATION_FAIL, "Failed to get build param")
        self._read_datahub(data_key, handle_param)

    def _handle_build_check_done(self, sender, request_id: str, data_key: str):
        """处理搭建校验完成事件"""
        def handle_check_result(result):
            if result:
                print(f"[Build] Build check result: {result}")
                check_passed = result.get('result', False)
                if check_passed and self._state == StatusCode.ACTION:
                    self._transition_to_complete()
                elif not check_passed:
                    self._send_exception(ErrorCode.ACTION_FAIL, "Build check failed")
            else:
                self._send_exception(ErrorCode.COMMUNICATION_FAIL, "Failed to get build check result")
        self._read_datahub(data_key, handle_check_result)

    def _handle_module_retry(self, sender, request_id: str, data_key: str):
        """处理模块重试事件"""
        def handle_retry_param(param):
            if param:
                module = param.get('module', '')
                if module == 'build':
                    print(f"[Build] Retrying, count: {param.get('retry_count', 0)}")
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
        self._write_datahub('build:status', self._current_status.to_dict())
        request_id = str(uuid.uuid4())
        self._status_updated_signal.send(self, request_id=request_id, data_key='build:status')

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
        self._update_status(StatusCode.COMPLETE, "Build task completed", ErrorCode.NONE)
        request_id = str(uuid.uuid4())
        self._task_complete_signal.send(self, request_id=request_id, data_key='build:status')

    def _execute_init_state(self, param: dict):
        """执行初始化定位状态"""
        self._state = StatusCode.INIT
        self._update_status(StatusCode.INIT, "Initializing", ErrorCode.NONE)

        self._target_position = param.get('target_position', {})
        self._current_layer = param.get('layer', 0)

        print(f"[Build] Initializing, target: {self._target_position}, layer: {self._current_layer}")

        # 设置机械臂到初始位置
        self._arm.set_home()

        # 发送初始化完成事件
        request_id = str(uuid.uuid4())
        self._init_complete_signal.send(self, request_id=request_id, data_key='build:status')

        # 进入导航状态
        self._state = StatusCode.NAVIGATE
        self._execute_navigate_state(param)

    def _execute_navigate_state(self, param: dict):
        """执行导航状态"""
        self._update_status(StatusCode.NAVIGATE, "Navigating to target", ErrorCode.NONE)
        request_id = str(uuid.uuid4())
        self._navigating_signal.send(self, request_id=request_id, data_key='build:status')

        target = param.get('target_position', {})
        target_x = target.get('x', 0)
        target_y = target.get('y', 0)

        print(f"[Build] Navigating to ({target_x}, {target_y})")

        # 使用运动控制器移动到目标位置
        def progress_callback(progress):
            self._write_datahub('build:progress', {'progress': progress, 'layer': self._current_layer})

        success = self._motion.go_to_position(target_x, target_y, threshold=5.0,
                                               speed=2048, progress_callback=progress_callback)

        if success:
            print(f"[Build] Arrived at target")
            self._state = StatusCode.ACTION
            self._execute_action_state(param)
        else:
            self._send_exception(ErrorCode.NAVIGATION_FAIL, "Failed to reach target")

    def _execute_action_state(self, param: dict):
        """执行搭建动作状态"""
        self._update_status(StatusCode.ACTION, "Building structure", ErrorCode.NONE)
        request_id = str(uuid.uuid4())
        self._building_signal.send(self, request_id=request_id, data_key='build:status')

        print(f"[Build] Executing build action, layer={self._current_layer}")

        # 根据目标高度调整机械臂
        if self._current_layer > 0:
            # 多层搭建，需要更精准的放置
            self._arm.reach_forward()
            time.sleep(0.5)

        # 使用机械爪执行搭建（张开放置）
        self._gripper.open()
        print(f"[Build] Gripper opened for layer {self._current_layer}")

        # 通知视觉模块进行搭建校验
        check_key = 'vision:build_check_result'
        vision_check = self._datahub.get(check_key)

        if vision_check and vision_check.get('result'):
            self._current_layer += 1
            self._transition_to_complete()
        else:
            # 需要等待视觉校验结果，由视觉模块触发BUILD_CHECK_DONE事件
            pass

    def start(self):
        """启动搭建模块"""
        self._running = True
        self._arm.set_home()
        print("[Build] Build module started")

    def stop(self):
        """停止搭建模块"""
        self._running = False
        self._motion.stop()
        self._arm.release_all()
        print("[Build] Build module stopped")

    def set_layer(self, layer: int):
        """设置当前搭建层数"""
        self._current_layer = layer

    def get_layer(self) -> int:
        """获取当前层数"""
        return self._current_layer

    def on_status_updated(self, callback: Callable):
        """注册状态更新回调"""
        self._status_updated_signal.connect(callback)

    def on_task_complete(self, callback: Callable):
        """注册任务完成回调"""
        self._task_complete_signal.connect(callback)

    def on_exception(self, callback: Callable):
        """注册异常回调"""
        self._exception_signal.connect(callback)

    def get_motion_controller(self) -> MotionController:
        """获取运动控制器（用于外部控制导航）"""
        return self._motion

    def get_gripper_controller(self) -> GripperController:
        """获取机械爪控制器（用于外部控制抓取）"""
        return self._gripper

    def get_arm_controller(self) -> ArmController:
        """获取机械臂控制器（用于外部控制机械臂）"""
        return self._arm


def get_build_module(left_motor_channel: int = 0,
                     right_motor_channel: int = 1,
                     gripper_channel: int = 2,
                     arm_channels: tuple = (3, 4, 5, 6)) -> BuildModule:
    """获取搭建模块单例"""
    return BuildModule(left_motor_channel, right_motor_channel, gripper_channel, arm_channels)