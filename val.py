from test2 import CameraHelper
import time
from pyzbar.pyzbar import decode
from PIL import Image
import requests
import json
from gpiozero import InputDevice

camera = CameraHelper()

def scan_qr_loop(filename, label="QR Code", delay=5):
    while True:
        print(f"📸 嘗試拍攝 {label} ...")
        if not camera.capture_and_save_image(filename):
            print("🔴 拍照失敗，重試中...")
            time.sleep(delay)
            continue

        result = read_qr_from_image(filename)
        if result:
            print(f"✅ 成功讀取 {label}: {result}")
            return result
        else:
            print(f"📭 沒有偵測到 QR code，{delay} 秒後重試...")
            time.sleep(delay)


API_BASE = "http://192.168.251.11"


def read_qr_from_image(image_path):
    try:
        image = Image.open(image_path)
        width, height = image.size

        # 裁切中央區域（縮小解碼範圍）
        crop_size = int(min(width, height) * 0.6)
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        cropped_image = image.crop((left, top, right, bottom))

        decoded_objects = decode(cropped_image)
        for obj in decoded_objects:
            return obj.data.decode("utf-8")

        # 嘗試用整張圖片再次 decode（以防中央掃不到）
        decoded_objects = decode(image)
        for obj in decoded_objects:
            return obj.data.decode("utf-8")

        return None
    except Exception as e:
        print(f"❌ 解碼失敗: {e}")
        return None


def verify_user_token(token):
    url = f"{API_BASE}/api/user"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, verify=False, allow_redirects=False)
    print(f"使用者驗證狀態碼: {response.status_code}")
    print("回應內容:", response.text)
    return response.status_code == 200

def send_item_id(token, item_id):
    url = f"{API_BASE}/api/scan"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        payload = json.loads(item_id)
    except json.JSONDecodeError:
        print("❌ 物品 QR 不是合法 JSON 格式")
        return False

    response = requests.post(url, headers=headers, json=payload, verify=False, allow_redirects=False)
    print(f"物品掃描狀態碼: {response.status_code}")
    print("回應內容:", response.text)
    return response.status_code == 200

def verify():
    # 使用者 QR Code 掃描 + 驗證
    print("🔔 請將使用者 QR Code 放在鏡頭前，按 Enter 開始掃描")
    input("👉 請按 Enter 開始...")

    while True:
        user_token = scan_qr_loop("id.jpg", label="使用者 QR Code", delay=5)
        if verify_user_token(user_token):
            print("✅ 使用者驗證成功")
            break
        else:
            print("❌ 使用者驗證失敗，請重新掃描")

    y = input("👉 若要借出物品，按 y 繼續掃描物品 QR Code: ")
    if y != 'y':
        return
    # 物品 QR Code 掃描（只需要掃到即可）
    print("🔔 請將物品 QR Code 放在鏡頭前")

    item_id = scan_qr_loop("qr.jpg", label="物品 QR Code", delay=5)

    # 傳送 item id
    if send_item_id(user_token, item_id):
        print("🎉 ✅ 借/還成功！")
    else:
        print("❌ 借出失敗，請重試整個流程")

# ========================
# ✅ 主流程
# ========================
if __name__ == "__main__":
    # IR sensor 初始化，設定輸入為 GPIO 23(Pin 16)
    ir_sensor = InputDevice(23)

    while True:
        # 偵測人員通過門禁
        while not ir_sensor.is_active:
            time.sleep(0.5)

        # 人員和物品驗證
        verify()

        # 避免人員偵測重複觸發
        time.sleep(1)
