"""机械爪控制器模块"""
from .servo import GripperServo, get_gripper_servo


class GripperController:
    """机械爪控制器 - 控制机械爪的张合动作"""

    def __init__(self, servo_channel: int):
        """初始化机械爪控制器

        Args:
            servo_channel: 机械爪伺服电机连接的PWM通道
        """
        self._servo = get_gripper_servo(servo_channel)
        self._is_closed = False

    def open(self):
        """张开机械爪"""
        self._servo.open()
        self._is_closed = False

    def close(self):
        """闭合机械爪"""
        self._servo.close()
        self._is_closed = True

    def toggle(self):
        """切换机械爪状态"""
        if self._is_closed:
            self.open()
        else:
            self.close()

    def is_closed(self) -> bool:
        """检查机械爪是否闭合"""
        return self._is_closed

    def set_open_angle(self, angle: float):
        """设置张开角度"""
        self._servo.set_open_angle(angle)

    def set_close_angle(self, angle: float):
        """设置闭合角度"""
        self._servo.set_close_angle(angle)

    def grab(self):
        """执行抓取动作（先闭合，检查是否抓稳）"""
        self.close()
        self._is_closed = True

    def release(self):
        """释放机械爪（张开）"""
        self.open()


class DualGripperController:
    """双机械爪控制器 - 控制两个机械爪"""

    def __init__(self, servo_channel1: int, servo_channel2: int):
        """初始化双机械爪控制器

        Args:
            servo_channel1: 第一个机械爪伺服通道
            servo_channel2: 第二个机械爪伺服通道
        """
        self._gripper1 = GripperController(servo_channel1)
        self._gripper2 = GripperController(servo_channel2)

    def open_both(self):
        """同时张开两个机械爪"""
        self._gripper1.open()
        self._gripper2.open()

    def close_both(self):
        """同时闭合两个机械爪"""
        self._gripper1.close()
        self._gripper2.close()

    def open_left(self):
        """张开左侧机械爪"""
        self._gripper1.open()

    def open_right(self):
        """张开右侧机械爪"""
        self._gripper2.open()

    def close_left(self):
        """闭合左侧机械爪"""
        self._gripper1.close()

    def close_right(self):
        """闭合右侧机械爪"""
        self._gripper2.close()


def get_gripper_controller(servo_channel: int) -> GripperController:
    """获取机械爪控制器实例"""
    return GripperController(servo_channel)


def get_dual_gripper_controller(servo_channel1: int, servo_channel2: int) -> DualGripperController:
    """获取双机械爪控制器实例"""
    return DualGripperController(servo_channel1, servo_channel2)