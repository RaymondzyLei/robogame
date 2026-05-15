"""伺服电机控制器模块"""
from .pca9685 import get_pca9685_driver


class ServoController:
    """伺服电机控制器 - 用于控制角度伺服电机"""

    # 伺服电机标准参数
    MIN_PULSE = 500   # 最小脉冲宽度（微秒）对应0度
    MAX_PULSE = 2500  # 最大脉冲宽度（微秒）对应180度

    def __init__(self, channel: int, min_pulse: int = None, max_pulse: int = None):
        """初始化伺服控制器

        Args:
            channel: PWM通道号 (0-15)
            min_pulse: 最小脉冲宽度（微秒）
            max_pulse: 最大脉冲宽度（微秒）
        """
        self._channel = channel
        self._pca = get_pca9685_driver()
        self._min_pulse = min_pulse or self.MIN_PULSE
        self._max_pulse = max_pulse or self.MAX_PULSE
        self._current_angle = 0

    def set_angle(self, angle: float):
        """设置伺服电机角度

        Args:
            angle: 目标角度 (0-180度)
        """
        angle = max(0, min(180, angle))
        self._current_angle = angle

        # 将角度转换为脉冲宽度
        pulse_width = int(self._min_pulse + (angle / 180) * (self._max_pulse - self._min_pulse))
        self._pca.set_pulse_width(self._channel, pulse_width)

    def get_angle(self) -> float:
        """获取当前角度"""
        return self._current_angle

    def center(self):
        """将伺服转到中心位置（90度）"""
        self.set_angle(90)

    def disable(self):
        """禁用伺服电机（停止PWM输出）"""
        self._pca.set_duty_cycle(self._channel, 0)

    def enable(self):
        """启用伺服电机（恢复到最后设置的角度）"""
        self.set_angle(self._current_angle)


class GripperServo:
    """机械爪伺服电机专用封装"""

    def __init__(self, channel: int):
        self._servo = ServoController(channel)
        self._open_angle = 0    # 张开角度
        self._close_angle = 90  # 闭合角度

    def open(self):
        """张开机械爪"""
        self._servo.set_angle(self._open_angle)

    def close(self):
        """闭合机械爪"""
        self._servo.set_angle(self._close_angle)

    def set_open_angle(self, angle: float):
        """设置张开角度"""
        self._open_angle = angle

    def set_close_angle(self, angle: float):
        """设置闭合角度"""
        self._close_angle = angle

    def is_open(self) -> bool:
        """检查机械爪是否张开"""
        return abs(self._servo.get_angle() - self._open_angle) < 5


class ArmServo:
    """机械臂伺服电机封装"""

    def __init__(self, channel: int, min_angle: float = 0, max_angle: float = 180):
        self._servo = ServoController(channel)
        self._min_angle = min_angle
        self._max_angle = max_angle

    def set_angle(self, angle: float):
        """设置机械臂角度（带边界限制）"""
        angle = max(self._min_angle, min(self._max_angle, angle))
        self._servo.set_angle(angle)

    def get_angle(self) -> float:
        """获取当前角度"""
        return self._servo.get_angle()

    def tilt_forward(self, delta: float = 10):
        """向前倾斜（增加角度）"""
        self.set_angle(self.get_angle() + delta)

    def tilt_backward(self, delta: float = 10):
        """向后倾斜（减少角度）"""
        self.set_angle(self.get_angle() - delta)


class ContinuousRotationServo:
    """连续旋转伺服电机（用于轮子）"""

    def __init__(self, channel: int):
        self._channel = channel
        self._pca = get_pca9685_driver()
        self._speed = 0  # -100 到 100

    def set_speed(self, speed: float):
        """设置旋转速度

        Args:
            speed: 速度值 (-100 到 100，正值一个方向，负值反方向)
        """
        self._speed = max(-100, min(100, speed))

        # 将-100~100映射到500~2500脉冲宽度
        # 1500为停止，1500-2500为一个方向，500-1500为另一个方向
        pulse = 1500 + int((speed / 100) * 1000)
        pulse = max(500, min(2500, pulse))

        self._pca.set_pulse_width(self._channel, pulse)

    def stop(self):
        """停止旋转"""
        self._speed = 0
        self._pca.set_pulse_width(self._channel, 1500)  # 1500为停止位置

    def get_speed(self) -> float:
        """获取当前速度"""
        return self._speed


def get_servo_controller(channel: int) -> ServoController:
    """获取伺服控制器实例"""
    return ServoController(channel)


def get_gripper_servo(channel: int) -> GripperServo:
    """获取机械爪伺服实例"""
    return GripperServo(channel)


def get_arm_servo(channel: int, min_angle: float = 0, max_angle: float = 180) -> ArmServo:
    """获取机械臂伺服实例"""
    return ArmServo(channel, min_angle, max_angle)


def get_continuous_servo(channel: int) -> ContinuousRotationServo:
    """获取连续旋转伺服实例（用于轮子）"""
    return ContinuousRotationServo(channel)