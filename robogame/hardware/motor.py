"""Motor and servo abstractions."""

from __future__ import annotations

from robogame.hardware.pca9685 import PCA9685Driver, get_pca9685_driver


class DCMotor:
    def __init__(self, pwm_channel: int, dir_channel: int, driver: PCA9685Driver | None = None) -> None:
        self.pwm_channel = pwm_channel
        self.dir_channel = dir_channel
        self.driver = driver or get_pca9685_driver()

    def forward(self, speed: int) -> None:
        self.driver.get_channel(self.dir_channel).duty_cycle = 4095
        self.driver.get_channel(self.pwm_channel).duty_cycle = max(0, min(4095, speed))

    def backward(self, speed: int) -> None:
        self.driver.get_channel(self.dir_channel).duty_cycle = 0
        self.driver.get_channel(self.pwm_channel).duty_cycle = max(0, min(4095, speed))

    def stop(self) -> None:
        self.driver.disable_channel(self.pwm_channel)


class StepperMotor:
    def __init__(self, channels: list[int], driver: PCA9685Driver | None = None) -> None:
        self.channels = channels
        self.driver = driver or get_pca9685_driver()
        self._step_index = 0
        self._sequence = [(1, 0, 0, 1), (1, 1, 0, 0), (0, 1, 1, 0), (0, 0, 1, 1)]

    def step(self, direction: int = 1) -> None:
        self._step_index = (self._step_index + (1 if direction >= 0 else -1)) % len(self._sequence)
        for channel, enabled in zip(self.channels, self._sequence[self._step_index], strict=False):
            self.driver.get_channel(channel).duty_cycle = 4095 if enabled else 0

    def release(self) -> None:
        for channel in self.channels:
            self.driver.disable_channel(channel)


class ServoController:
    def __init__(self, channel: int, driver: PCA9685Driver | None = None) -> None:
        self.channel = channel
        self.driver = driver or get_pca9685_driver()

    def set_angle(self, angle: float) -> None:
        clamped = max(0.0, min(180.0, angle))
        pulse = int((clamped / 180.0) * 2000 + 500)
        self.driver.set_pulse_width(self.channel, pulse)

    def center(self) -> None:
        self.set_angle(90)

    def disable(self) -> None:
        self.driver.disable_channel(self.channel)


class ContinuousRotationServo(ServoController):
    def set_speed(self, speed: float) -> None:
        clamped = max(-100.0, min(100.0, speed))
        pulse = int(1500 + clamped * 5)
        self.driver.set_pulse_width(self.channel, pulse)

    def stop(self) -> None:
        self.driver.set_pulse_width(self.channel, 1500)


def get_dc_motor(pwm_channel: int, dir_channel: int) -> DCMotor:
    return DCMotor(pwm_channel, dir_channel)


def get_stepper_motor(channels: list[int]) -> StepperMotor:
    return StepperMotor(channels)


def get_servo_controller(channel: int) -> ServoController:
    return ServoController(channel)


def get_continuous_servo(channel: int) -> ContinuousRotationServo:
    return ContinuousRotationServo(channel)
