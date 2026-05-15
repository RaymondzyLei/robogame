"""电机控制器模块"""
from typing import Optional
from .pca9685 import get_pca9685_driver, PCA9685Driver


class MotorController:
    """电机控制器 - 用于控制直流电机/步进电机"""

    def __init__(self, pwm_channel: int, dir_channel: Optional[int] = None):
        """初始化电机控制器

        Args:
            pwm_channel: PWM速度控制通道 (0-15)
            dir_channel: 方向控制通道（如果有）
        """
        self._pwm_channel = pwm_channel
        self._dir_channel = dir_channel
        self._pca = get_pca9685_driver()
        self._speed = 0  # 当前速度 (-4095 到 4095)

    def set_speed(self, speed: int):
        """设置电机速度

        Args:
            speed: 速度值 (-4095 到 4095，负值反转)
        """
        self._speed = max(-4095, min(4095, speed))

        pwm_value = abs(self._speed)
        self._pca.set_duty_cycle(self._pwm_channel, pwm_value)

        if self._dir_channel is not None:
            dir_value = 4095 if self._speed >= 0 else 0
            self._pca.set_duty_cycle(self._dir_channel, dir_value)

    def stop(self):
        """停止电机"""
        self._speed = 0
        self._pca.set_duty_cycle(self._pwm_channel, 0)

    def get_speed(self) -> int:
        """获取当前速度"""
        return self._speed


class DCMotor:
    """直流电机控制封装"""

    def __init__(self, pwm_channel: int, dir_channel: Optional[int] = None):
        self._controller = MotorController(pwm_channel, dir_channel)

    def forward(self, speed: int = 2048):
        """正向转动"""
        self._controller.set_speed(speed)

    def backward(self, speed: int = 2048):
        """反向转动"""
        self._controller.set_speed(-speed)

    def stop(self):
        """停止"""
        self._controller.stop()


class StepperMotor:
    """步进电机控制封装"""

    def __init__(self, phase_channels: list):
        """初始化步进电机

        Args:
            phase_channels: 四相控制通道列表 [A+, A-, B+, B-]
        """
        self._channels = phase_channels
        self._pca = get_pca9685_driver()
        self._step_sequence = [
            [1, 0, 0, 0],
            [1, 1, 0, 0],
            [0, 1, 0, 0],
            [0, 1, 1, 0],
            [0, 0, 1, 0],
            [0, 0, 1, 1],
            [0, 0, 0, 1],
            [1, 0, 0, 1],
        ]
        self._current_step = 0

    def step(self, direction: int = 1):
        """执行一步

        Args:
            direction: 方向 (1=正转, -1=反转)
        """
        self._current_step = (self._current_step + direction) % 8

        for i, channel in enumerate(self._channels):
            duty = 4095 if self._step_sequence[self._current_step][i] else 0
            self._pca.set_duty_cycle(channel, duty)

    def release(self):
        """释放电机（所有相关闭）"""
        for channel in self._channels:
            self._pca.set_duty_cycle(channel, 0)


def get_motor_controller(pwm_channel: int, dir_channel: Optional[int] = None) -> MotorController:
    """获取电机控制器实例"""
    return MotorController(pwm_channel, dir_channel)


def get_dc_motor(pwm_channel: int, dir_channel: Optional[int] = None) -> DCMotor:
    """获取直流电机实例"""
    return DCMotor(pwm_channel, dir_channel)


def get_stepper_motor(phase_channels: list) -> StepperMotor:
    """获取步进电机实例"""
    return StepperMotor(phase_channels)