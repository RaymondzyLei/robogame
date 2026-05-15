from picamera2 import Picamera2
import time
import os

def take_max_res_photo(save_name="max_res_photo.jpg"):
    # 枚举所有摄像头
    cam_list = Picamera2.global_camera_info()
    if not cam_list:
        raise RuntimeError("未识别到摄像头硬件")
    
    # 初始化摄像头
    picam = Picamera2(0)
    # OV5647 原生最高分辨率 2592*1944
    max_config = picam.create_still_configuration(
        main={"size": (2592, 1944)}
    )
    picam.configure(max_config)
    picam.start()
    
    # 曝光防抖预热
    time.sleep(1.5)
    # 拍摄保存
    picam.capture_file(save_name)
    picam.stop()
    print(f"✅ 超清照片拍摄完成")
    print(f"📸 分辨率：2592 × 1944")
    print(f"💾 保存路径：{os.path.abspath(save_name)}")

if __name__ == "__main__":
    try:
        take_max_res_photo()
    except Exception as e:
        print(f"❌ 拍摄失败：{str(e)}")
