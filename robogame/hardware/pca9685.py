"""Safe PCA9685 abstraction.

The driver is inert until explicitly initialized with a real I2C object.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PWMChannel:
    index: int
    duty_cycle: int = 0


class PCA9685Driver:
    def __init__(self) -> None:
        self._pca: Any | None = None
        self._channels = [PWMChannel(index=i) for i in range(16)]
        self._frequency = 50

    def initialize(self, i2c: Any, address: int = 0x40) -> None:
        from adafruit_pca9685 import PCA9685

        self._pca = PCA9685(i2c, address=address)
        self._pca.frequency = self._frequency

    @property
    def frequency(self) -> int:
        return self._frequency

    @frequency.setter
    def frequency(self, value: int) -> None:
        self._frequency = value
        if self._pca is not None:
            self._pca.frequency = value

    def get_channel(self, channel: int) -> Any:
        if self._pca is not None:
            return self._pca.channels[channel]
        return self._channels[channel]

    def set_pulse_width(self, channel: int, pulse_us: int) -> None:
        duty = int(pulse_us * 4095 / 20000)
        self.get_channel(channel).duty_cycle = max(0, min(4095, duty))

    def disable_channel(self, channel: int) -> None:
        self.get_channel(channel).duty_cycle = 0


_default_driver = PCA9685Driver()


def get_pca9685_driver() -> PCA9685Driver:
    return _default_driver
