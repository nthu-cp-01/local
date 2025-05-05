import time
import json
import random
import argparse
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
from awsiot import iotshadow

# === 解析指令列參數 ===
parser = argparse.ArgumentParser(description="Publish env_condition to AWS IoT shadow repeatedly")
parser.add_argument('--endpoint', required=True, help="Your AWS IoT endpoint")
parser.add_argument('--cert', required=True, help="Path to your certificate.pem")
parser.add_argument('--key', required=True, help="Path to your private key")
parser.add_argument('--thing_name', required=True, help="Thing name to update shadow")
args = parser.parse_args()

ENDPOINT = args.endpoint
CLIENT_ID = args.thing_name
THING_NAME = args.thing_name
ROOT_CA = "./AmazonRootCA1.pem"  # 預設 CA 路徑（可根據需要改）

# === 初始化 MQTT 連線 ===
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=ENDPOINT,
    cert_filepath=args.cert,
    pri_key_filepath=args.key,
    client_bootstrap=client_bootstrap,
    ca_filepath=ROOT_CA,
    client_id=CLIENT_ID,
    clean_session=False,
    keep_alive_secs=30
)

print(f"Connecting to {ENDPOINT} with client ID '{CLIENT_ID}'...")
connect_future = mqtt_connection.connect()
connect_future.result()
print("Connected!")

# === 初始化 shadow client ===
shadow_client = iotshadow.IotShadowClient(mqtt_connection)

# === 主 loop: 每 1 秒更新一次 shadow ===
try:
    while True:
        # 模擬溫溼度
        temperature = round(random.uniform(20, 30), 1)
        humidity = round(random.uniform(40, 80), 1)

        payload = {
            "state": {
                "reported": {
                    "env_condition": {
                        "temperature": temperature,
                        "humidity": humidity
                    }
                }
            }
        }

        print(f"Updating shadow: {payload}")

        # 發送 shadow 更新
        request = iotshadow.UpdateShadowRequest(
            thing_name=THING_NAME,
            state=payload["state"]
        )

        future = shadow_client.publish_update_shadow(request, qos=mqtt.QoS.AT_LEAST_ONCE)
        future.result()  # 等待發送完成

        time.sleep(1)

except KeyboardInterrupt:
    print("Stopping the loop...")

finally:
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected!")

