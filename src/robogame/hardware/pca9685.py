"""PCA9685 PWM驱动板控制模块"""
import time
from typing import Optional, Dict, Any


class PCA9685Driver:
    """PCA9685 16通道PWM驱动板封装类"""

    _instance = None

    def __new__(cls, i2c=None, address: int = 0x40):
        if cls._instance is not None:
            return cls._instance
        cls._instance = super().__new__(cls)
        cls._instance._initialized = False
        return cls._instance

    def __init__(self, i2c=None, address: int = 0x40):
        if self._initialized:
            return
        self._initialized = True

        self._address = address
        self._i2c = i2c
        self._pca = None
        self._channels: Dict[int, 'PWMChannel'] = {}
        self._frequency = 50  # 默认50Hz（伺服电机标准）

    def initialize(self, i2c=None, address: int = 0x40):
        """初始化PCA9685硬件连接

        Args:
            i2c: I2C总线对象（如busio.I2C）
            address: PCA9685的I2C地址，默认0x40
        """
        if i2c is not None:
            self._i2c = i2c

        if self._i2c is None:
            raise ValueError("I2C总线未初始化，请在raspberry-pi环境调用initialize()")

        try:
            from adafruit_pca9685 import PCA9685
            self._pca = PCA9685(self._i2c, address=address)
            self._pca.frequency = self._frequency
            print(f"[PCA9685] Initialized at address 0x{address:02X}, frequency={self._frequency}Hz")
        except ImportError:
            print("[PCA9685] Adafruit PCA9685库未安装，模拟模式")
            self._pca = None

    def deinitialize(self):
        """释放硬件资源"""
        if self._pca:
            self._pca.deinit()
            self._pca = None
        print("[PCA9685] Deinitialized")

    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._pca is not None

    @property
    def frequency(self) -> int:
        """获取PWM频率"""
        return self._frequency

    @frequency.setter
    def frequency(self, freq: int):
        """设置PWM频率"""
        self._frequency = freq
        if self._pca:
            self._pca.frequency = freq

    def get_channel(self, channel: int) -> 'PWMChannel':
        """获取指定通道的PWM控制对象

        Args:
            channel: 通道号 (0-15)

        Returns:
            PWMChannel对象
        """
        if channel not in self._channels:
            self._channels[channel] = PWMChannel(self, channel)
        return self._channels[channel]

    def set_pulse_width(self, channel: int, pulse_us: int):
        """设置通道的脉冲宽度（微秒）

        Args:
            channel: 通道号 (0-15)
            pulse_us: 脉冲宽度（微秒），范围500-2500
        """
        channel_obj = self.get_channel(channel)
        channel_obj.pulse_width = pulse_us

    def set_duty_cycle(self, channel: int, duty: int):
        """设置通道的占空比

        Args:
            channel: 通道号 (0-15)
            duty: 占空比 (0-4095，12位分辨率)
        """
        channel_obj = self.get_channel(channel)
        channel_obj.duty_cycle = duty

    def disable_channel(self, channel: int):
        """禁用指定通道（输出为0）"""
        channel_obj = self.get_channel(channel)
        channel_obj.duty_cycle = 0

    def reset(self):
        """重置PCA9685芯片"""
        if self._pca:
            self._pca.reset()


class PWMChannel:
    """PCA9685单通道PWM控制封装"""

    def __init__(self, driver: PCA9685Driver, channel: int):
        self._driver = driver
        self._channel = channel

    @property
    def duty_cycle(self) -> int:
        """获取当前占空比 (0-4095)"""
        if self._driver._pca:
            return self._driver._pca.channels[self._channel].duty_cycle
        return 0

    @duty_cycle.setter
    def duty_cycle(self, value: int):
        """设置占空比 (0-4095)"""
        if self._driver._pca:
            self._driver._pca.channels[self._channel].duty_cycle = max(0, min(4095, value))

    @property
    def pulse_width(self) -> int:
        """获取当前脉冲宽度（微秒）"""
        duty = self.duty_cycle
        if duty == 0:
            return 0
        freq = self._driver.frequency
        period_us = 1_000_000 // freq
        return int((duty / 4095) * period_us)

    @pulse_width.setter
    def pulse_width(self, pulse_us: int):
        """设置脉冲宽度（微秒），自动转换为占空比

        Args:
            pulse_us: 脉冲宽度（微秒），典型范围500-2500
        """
        freq = self._driver.frequency
        period_us = 1_000_000 // freq
        duty = int((pulse_us / period_us) * 4095)
        self.duty_cycle = max(0, min(4095, duty))


def get_pca9685_driver() -> PCA9685Driver:
    """获取PCA9685驱动单例"""
    return PCA9685Driver()