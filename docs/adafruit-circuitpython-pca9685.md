# Adafruit CircuitPython PCA9685 库使用指南

## 1. 简介

`adafruit-circuitpython-pca9685` 是用于驱动 **PCA9685** 芯片的 CircuitPython 库。
- **PCA9685**：16通道、12位分辨率的PWM（脉冲宽度调制）芯片。
- 应用场景：伺服电机控制、LED调光、电机驱动等需要多通道PWM输出的场景。

## 2,3. 依赖与安装（已经完成依赖和安装，故跳过）

## 4. 核心 API 参考

### 4.1 主类：`PCA9685`
#### 初始化
```python
from adafruit_pca9685 import PCA9685
import busio

# 创建I2C对象（根据硬件引脚调整）
i2c = busio.I2C(board.SCL, board.SDA)

# 初始化PCA9685
pca = PCA9685(i2c)
```

#### 关键属性与方法
| 成员 | 说明 |
|------|------|
| `pca.channels` | 16个PWM通道集合（`PCAChannels` 对象） |
| `pca.frequency` | PWM信号频率（单位：Hz），常用50Hz（伺服电机） |
| `pca.reference_clock_speed` | 参考时钟速度（默认25MHz） |
| `pca.reset()` | 重置PCA9685芯片 |
| `pca.deinit()` | 释放硬件资源 |

### 4.2 通道类：`PCAChannels` 与 `PWMChannel`
#### 访问通道
```python
# 获取第0通道（0-15共16个通道）
channel0 = pca.channels[0]
```

#### `PWMChannel` 关键属性
| 属性 | 说明 |
|------|------|
| `channel.duty_cycle` | 占空比（12位，范围0-4095）<br>- 0：完全关闭<br>- 4095：完全打开 |
| `channel.frequency` | 通道频率（继承自 `PCA9685`） |

## 5. 基础使用示例

### 5.1 简单测试（PWM输出）
```python
from adafruit_pca9685 import PCA9685
import busio
import time

# 初始化I2C和PCA9685
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)

# 设置PWM频率为50Hz（伺服电机常用）
pca.frequency = 50

# 控制第0通道：占空比从0渐变到4095
for duty in range(0, 4096, 100):
    pca.channels[0].duty_cycle = duty
    time.sleep(0.01)

# 释放资源
pca.deinit()
```

### 5.2 伺服电机控制示例
```python
from adafruit_pca9685 import PCA9685
import busio
import time

i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50  # 伺服电机标准频率

# 伺服电机角度转占空比（500-2500μs对应0-180°）
def angle_to_duty(angle):
    return int((angle / 180) * (2500 - 500) + 500) * 4095 // 20000

# 控制第0通道伺服电机旋转
for angle in [0, 90, 180, 90, 0]:
    duty = angle_to_duty(angle)
    pca.channels[0].duty_cycle = duty
    time.sleep(1)

pca.deinit()
```

## 6. 注意事项
1. **硬件连接**：PCA9685通过I2C通信，需正确连接SCL/SDA引脚。
2. **电压适配**：芯片供电3.3V-5V，输出通道需匹配负载电压。
3. **占空比范围**：12位分辨率，`duty_cycle` 严格限制在 **0-4095**。
4. **频率选择**：
   - 伺服电机：50Hz
   - LED调光：100Hz-1kHz
   - 电机驱动：1kHz-20kHz

## 7. 官方资源
- 文档主页：https://docs.circuitpython.org/projects/pca9685/en/latest/index.html
- 仓库主页：https://github.com/adafruit/Adafruit_CircuitPython_PCA9685
- 示例代码：项目中`./examples`下的三个示例代码
- PyPI项目页：https://pypi.org/project/adafruit-circuitpython-pca9685/
- 