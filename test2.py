from picamera2 import Picamera2
import time
import os

class CameraHelper:
    def __init__(self):
        self.cam = Picamera2()
        self.cam.configure(self.cam.create_still_configuration())

    def capture_and_save_image(self, filename="id.jpg"):
        try:
            print(f"📸 拍照並儲存為 {filename}")
            self.cam.start()
            time.sleep(2)
            self.cam.capture_file(filename)
            self.cam.stop()
            time.sleep(1)

            if os.path.exists(filename):
                print(f"✅ 圖片儲存成功：{filename}")
                return True
            else:
                print("❌ 找不到圖片檔案")
                return False

        except Exception as e:
            print(f"❌ 拍照錯誤：{e}")
            return False
