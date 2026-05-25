"""High-level hardware controllers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from robogame.hardware.motor import ContinuousRotationServo, ServoController


class MotionController:
    def __init__(self, left_motor_channel: int, right_motor_channel: int) -> None:
        self.left = ContinuousRotationServo(left_motor_channel)
        self.right = ContinuousRotationServo(right_motor_channel)
        self._pose = {"x": 0.0, "y": 0.0, "yaw": 0.0}

    def move_forward(self, speed: int) -> None:
        self.left.set_speed(speed)
        self.right.set_speed(speed)

    def move_backward(self, speed: int) -> None:
        self.left.set_speed(-speed)
        self.right.set_speed(-speed)

    def turn_left(self, speed: int) -> None:
        self.left.set_speed(-speed)
        self.right.set_speed(speed)

    def turn_right(self, speed: int) -> None:
        self.left.set_speed(speed)
        self.right.set_speed(-speed)

    def stop(self) -> None:
        self.left.stop()
        self.right.stop()

    def go_to_position(
        self,
        x: float,
        y: float,
        threshold: float = 5.0,
        speed: int = 50,
        progress_callback: Callable[[float], None] | None = None,
    ) -> bool:
        self._pose["x"] = x
        self._pose["y"] = y
        if progress_callback:
            progress_callback(1.0)
        return True

    def rotate_to_angle(self, target_yaw: float, threshold: float = 5.0) -> bool:
        self._pose["yaw"] = target_yaw
        return True

    def get_pose(self) -> dict[str, float]:
        return dict(self._pose)

    def set_pose(self, x: float, y: float, yaw: float) -> None:
        self._pose = {"x": x, "y": y, "yaw": yaw}


class GripperController:
    def __init__(self, servo_channel: int) -> None:
        self.servo = ServoController(servo_channel)
        self._open_angle = 0.0
        self._close_angle = 90.0
        self._closed = False

    def open(self) -> None:
        self.servo.set_angle(self._open_angle)
        self._closed = False

    def close(self) -> None:
        self.servo.set_angle(self._close_angle)
        self._closed = True

    def toggle(self) -> None:
        self.open() if self._closed else self.close()

    def is_closed(self) -> bool:
        return self._closed

    def set_open_angle(self, angle: float) -> None:
        self._open_angle = angle

    def set_close_angle(self, angle: float) -> None:
        self._close_angle = angle

    def grab(self) -> None:
        self.close()

    def release(self) -> None:
        self.open()


class ArmController:
    def __init__(self, base_channel: int, shoulder_channel: int, elbow_channel: int, wrist_channel: int) -> None:
        self.joints = {
            "base": ServoController(base_channel),
            "shoulder": ServoController(shoulder_channel),
            "elbow": ServoController(elbow_channel),
            "wrist": ServoController(wrist_channel),
        }
        self.angles: dict[str, float] = {name: 90.0 for name in self.joints}

    def move_joint(self, joint: str, angle: float) -> None:
        self.joints[joint].set_angle(angle)
        self.angles[joint] = angle

    def set_home(self) -> None:
        for joint in self.joints:
            self.move_joint(joint, 90)

    def reach_forward(self) -> None:
        self.move_joint("shoulder", 60)
        self.move_joint("elbow", 120)

    def reach_down(self) -> None:
        self.move_joint("shoulder", 45)
        self.move_joint("elbow", 90)
        self.move_joint("wrist", 0)

    def lift_up(self) -> None:
        self.move_joint("shoulder", 120)
        self.move_joint("elbow", 80)

    def release_all(self) -> None:
        for servo in self.joints.values():
            servo.disable()


def get_motion_controller(left_motor_channel: int, right_motor_channel: int) -> MotionController:
    return MotionController(left_motor_channel, right_motor_channel)


def get_gripper_controller(servo_channel: int) -> GripperController:
    return GripperController(servo_channel)


def get_arm_controller(base_channel: int, shoulder_channel: int, elbow_channel: int, wrist_channel: int) -> ArmController:
    return ArmController(base_channel, shoulder_channel, elbow_channel, wrist_channel)
