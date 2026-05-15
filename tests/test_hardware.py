"""硬件模块测试"""
import sys
sys.path.insert(0, 'src')

print("=== 测试硬件模块导入 ===")

# 测试硬件模块导入
try:
    from robogame.hardware import (
        PCA9685Driver,
        MotorController,
        ServoController,
        GripperController,
        MotionController,
    )
    print("[Pass] 硬件模块导入成功")
except Exception as e:
    print(f"[Fail] 硬件模块导入失败: {e}")

# 测试PCA9685Driver
try:
    from robogame.hardware.pca9685 import PCA9685Driver, get_pca9685_driver
    driver = get_pca9685_driver()
    print(f"[Pass] PCA9685Driver单例: {driver}")
    print(f"  - is_initialized: {driver.is_initialized}")
except Exception as e:
    print(f"[Fail] PCA9685Driver: {e}")

# 测试MotorController
try:
    from robogame.hardware.motor import MotorController, get_motor_controller
    motor = get_motor_controller(pwm_channel=0, dir_channel=1)
    print(f"[Pass] MotorController: {motor}")
except Exception as e:
    print(f"[Fail] MotorController: {e}")

# 测试ServoController
try:
    from robogame.hardware.servo import ServoController, get_servo_controller
    servo = get_servo_controller(channel=2)
    print(f"[Pass] ServoController: {servo}")
    print(f"  - MIN_PULSE: {servo.MIN_PULSE}, MAX_PULSE: {servo.MAX_PULSE}")
except Exception as e:
    print(f"[Fail] ServoController: {e}")

# 测试GripperController
try:
    from robogame.hardware.gripper import GripperController, get_gripper_controller
    gripper = get_gripper_controller(servo_channel=3)
    print(f"[Pass] GripperController: {gripper}")
except Exception as e:
    print(f"[Fail] GripperController: {e}")

# 测试MotionController
try:
    from robogame.hardware.motion import MotionController, get_motion_controller
    motion = get_motion_controller(left_motor_channel=0, right_motor_channel=1)
    print(f"[Pass] MotionController: {motion}")
    print(f"  - pose: {motion.get_pose()}")
except Exception as e:
    print(f"[Fail] MotionController: {e}")

# 测试Actuator模块导入硬件
try:
    from robogame.actuator.collect.collect import get_collect_module
    collect = get_collect_module(left_motor_channel=0, right_motor_channel=1, gripper_channel=2)
    print(f"[Pass] CollectModule with hardware: {collect}")
    print(f"  - MotionController: {collect.get_motion_controller()}")
    print(f"  - GripperController: {collect.get_gripper_controller()}")
except Exception as e:
    print(f"[Fail] CollectModule with hardware: {e}")

# 测试PlaceModule
try:
    from robogame.actuator.place.place import get_place_module
    place = get_place_module(left_motor_channel=0, right_motor_channel=1, gripper_channel=2)
    print(f"[Pass] PlaceModule with hardware: {place}")
except Exception as e:
    print(f"[Fail] PlaceModule with hardware: {e}")

# 测试BuildModule
try:
    from robogame.actuator.build.build import get_build_module
    build = get_build_module(
        left_motor_channel=0, right_motor_channel=1,
        gripper_channel=2, arm_channels=(3, 4, 5, 6)
    )
    print(f"[Pass] BuildModule with hardware: {build}")
    print(f"  - ArmController: {build.get_arm_controller()}")
except Exception as e:
    print(f"[Fail] BuildModule with hardware: {e}")

print("\n=== 所有硬件模块测试完成 ===")