"""运动控制器模块 - 所有执行模块共用的运动控制"""
import time
from typing import Tuple, Optional, Callable
from .servo import ContinuousRotationServo, get_continuous_servo
from .motor import DCMotor, get_dc_motor


class MotionController:
    """运动控制器 - 控制机器人底盘移动

    这是所有执行模块（collect/place/build）共用的运动控制模块，
    负责机器人的导航和移动控制。
    """

    def __init__(self, left_motor_channel: int, right_motor_channel: int):
        """初始化运动控制器

        Args:
            left_motor_channel: 左轮电机PWM通道
            right_motor_channel: 右轮电机PWM通道
        """
        self._left_motor = get_dc_motor(left_motor_channel)
        self._right_motor = get_dc_motor(right_motor_channel)
        self._is_moving = False
        self._current_pose = {'x': 0, 'y': 0, 'yaw': 0}

    def move_forward(self, speed: int = 2048):
        """向前移动

        Args:
            speed: 速度 (0-4095)
        """
        self._left_motor.forward(speed)
        self._right_motor.forward(speed)
        self._is_moving = True

    def move_backward(self, speed: int = 2048):
        """向后移动

        Args:
            speed: 速度 (0-4095)
        """
        self._left_motor.backward(speed)
        self._right_motor.backward(speed)
        self._is_moving = True

    def turn_left(self, speed: int = 2048):
        """原地左转"""
        self._left_motor.backward(speed)
        self._right_motor.forward(speed)
        self._is_moving = True

    def turn_right(self, speed: int = 2048):
        """原地右转"""
        self._left_motor.forward(speed)
        self._right_motor.backward(speed)
        self._is_moving = True

    def stop(self):
        """停止移动"""
        self._left_motor.stop()
        self._right_motor.stop()
        self._is_moving = False

    def move(self, linear_speed: int, angular_speed: int = 0):
        """综合移动控制

        Args:
            linear_speed: 直线速度 (-4095 到 4095)
            angular_speed: 角速度（正值左转，负值右转）
        """
        left_speed = linear_speed - angular_speed
        right_speed = linear_speed + angular_speed

        self._left_motor.set_speed(left_speed)
        self._right_motor.set_speed(right_speed)
        self._is_moving = (linear_speed != 0 or angular_speed != 0)

    def go_to_position(self, target_x: float, target_y: float,
                       threshold: float = 5.0,
                       speed: int = 2048,
                       progress_callback: Optional[Callable] = None):
        """移动到目标位置（直线导航）

        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            threshold: 到达阈值（厘米）
            speed: 移动速度
            progress_callback: 进度回调函数，返回当前进度(0-1)
        """
        start_x = self._current_pose['x']
        start_y = self._current_pose['y']

        dx = target_x - start_x
        dy = target_y - start_y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance < threshold:
            return True

        # 计算方向
        target_yaw = (target_y - start_y, target_x - start_x)

        print(f"[Motion] Going to ({target_x}, {target_y}), distance={distance:.2f}cm")

        # 简单直线移动（实际应使用PID控制）
        self.move_forward(speed)

        # 模拟移动过程
        steps = int(distance / 1)  # 每厘米一步
        for i in range(steps):
            time.sleep(0.1)
            progress = i / steps
            if progress_callback:
                progress_callback(progress)

            # 更新位置（简化模型）
            ratio = (i + 1) / steps
            self._current_pose['x'] = start_x + dx * ratio
            self._current_pose['y'] = start_y + dy * ratio

        self.stop()

        # 更新最终位置
        self._current_pose['x'] = target_x
        self._current_pose['y'] = target_y

        return True

    def rotate_to_angle(self, target_yaw: float, threshold: float = 5.0, speed: int = 1024):
        """旋转到目标角度

        Args:
            target_yaw: 目标偏航角（度）
            threshold: 角度阈值
            speed: 旋转速度
        """
        current_yaw = self._current_pose['yaw']
        diff = target_yaw - current_yaw

        # 归一化到-180到180
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360

        if abs(diff) < threshold:
            return True

        if diff > 0:
            self.turn_left(speed)
        else:
            self.turn_right(speed)

        time.sleep(abs(diff) / 90)  # 简化的旋转估算

        self.stop()
        self._current_pose['yaw'] = target_yaw

        return True

    def get_pose(self) -> dict:
        """获取当前位姿"""
        return self._current_pose.copy()

    def set_pose(self, x: float, y: float, yaw: float):
        """设置当前位姿（用于定位校准）"""
        self._current_pose['x'] = x
        self._current_pose['y'] = y
        self._current_pose['yaw'] = yaw

    def is_moving(self) -> bool:
        """检查是否在移动中"""
        return self._is_moving


class OmniMotionController:
    """全向移动控制器 - 支持麦轮/舵轮底盘"""

    def __init__(self, motor_channels: list):
        """初始化全向移动控制器

        Args:
            motor_channels: 四个电机的PWM通道列表 [FL, FR, RL, RR]
        """
        self._motors = [get_dc_motor(ch) for ch in motor_channels]
        self._is_moving = False

    def move(self, vx: float, vy: float, omega: float):
        """全向移动

        Args:
            vx: X轴速度
            vy: Y轴速度
            omega: 旋转角速度
        """
        # 简化的全向移动模型
        speeds = [
            vx + vy + omega,
            vx - vy - omega,
            vx - vy + omega,
            vx + vy - omega
        ]

        for i, motor in enumerate(self._motors):
            speed = int(speeds[i])
            motor.set_speed(speed)

        self._is_moving = (vx != 0 or vy != 0 or omega != 0)

    def stop(self):
        """停止移动"""
        for motor in self._motors:
            motor.stop()
        self._is_moving = False


class ArmController:
    """机械臂控制器 - 控制机械臂运动"""

    def __init__(self, base_channel: int, shoulder_channel: int,
                 elbow_channel: int, wrist_channel: int):
        """初始化机械臂控制器

        Args:
            base_channel: 底座旋转通道
            shoulder_channel: 肩部通道
            elbow_channel: 肘部通道
            wrist_channel: 腕部通道
        """
        from .servo import ArmServo
        self._base = ArmServo(base_channel, 0, 360)
        self._shoulder = ArmServo(shoulder_channel, 0, 180)
        self._elbow = ArmServo(elbow_channel, 0, 180)
        self._wrist = ArmServo(wrist_channel, 0, 180)

    def set_home(self):
        """设置机械臂到初始位置"""
        self._base.set_angle(90)
        self._shoulder.set_angle(45)
        self._elbow.set_angle(90)
        self._wrist.set_angle(0)

    def reach_forward(self):
        """伸出机械臂（向前）"""
        self._shoulder.set_angle(90)
        self._elbow.set_angle(90)

    def reach_down(self):
        """伸出机械臂（向下抓取）"""
        self._shoulder.set_angle(150)
        self._elbow.set_angle(60)

    def lift_up(self):
        """抬起机械臂"""
        self._shoulder.set_angle(30)
        self._elbow.set_angle(120)

    def move_joint(self, joint: str, angle: float):
        """控制单个关节

        Args:
            joint: 关节名称 ('base', 'shoulder', 'elbow', 'wrist')
            angle: 目标角度
        """
        joints = {'base': self._base, 'shoulder': self._shoulder,
                  'elbow': self._elbow, 'wrist': self._wrist}
        if joint in joints:
            joints[joint].set_angle(angle)

    def release_all(self):
        """释放所有关节（失力）"""
        from .servo import get_servo_controller
        for servo in [self._base, self._shoulder, self._elbow, self._wrist]:
            servo._servo.disable()


def get_motion_controller(left_motor_channel: int, right_motor_channel: int) -> MotionController:
    """获取运动控制器实例"""
    return MotionController(left_motor_channel, right_motor_channel)


def get_omni_motion_controller(motor_channels: list) -> OmniMotionController:
    """获取全向运动控制器实例"""
    return OmniMotionController(motor_channels)


def get_arm_controller(base_channel: int, shoulder_channel: int,
                       elbow_channel: int, wrist_channel: int) -> ArmController:
    """获取机械臂控制器实例"""
    return ArmController(base_channel, shoulder_channel, elbow_channel, wrist_channel)