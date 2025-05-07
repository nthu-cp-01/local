import argparse
from time import time, sleep
import json
from concurrent.futures import Future
import sys
import traceback
from uuid import uuid4
from awscrt import mqtt, http
from awsiot import iotshadow, mqtt_connection_builder

THING_NAME = "named_test"
SENSOR_SHADOW_NAME = "dht_sensor"
CONTROLLER_SHADOW_NAME = "controller"
CONTROLLER_DEFAULT_VALUE = {
    "humidity": 30.0,
    "temperature": 26.0,
    "dehumidifier_is_enable": False,
    "ac_is_enable": False,
}

THRESHOLD_TEMPERATURE = 30.0
ACTIVATED_TEMPERATURE = 26.0
WARNING_INTERVAL_SECONDS = 5 * 60

WARNING_TOPIC = "dht_sensor/warning"

last_warning_sec = 0

class MockSensor:
    def get_humidity_and_temperature(self):
        return 30.1, 27.2

class MockController:
    def set_machine_property(self, property, val):
        print(f"Controller sets {property} to {val}")

    def get_machine_property(self):
        return CONTROLLER_DEFAULT_VALUE

def parse_args():
    parser = argparse.ArgumentParser(description="AWS IoT Device Shadow Client")
    
    parser.add_argument("--ca_file", required=True, help="Root CA file path")
    parser.add_argument("--cert", required=True, help="Device certificate file path")
    parser.add_argument("--key", required=True, help="Device private key file path")
    parser.add_argument("--endpoint", required=True, help="AWS IoT custom endpoint")

    return parser.parse_args()

def exit(msg_or_exception):
    if isinstance(msg_or_exception, Exception):
        print("Exiting sample due to exception.")
        traceback.print_exception(msg_or_exception.__class__, msg_or_exception, sys.exc_info()[2])
    else:
        print("Exiting sample:", msg_or_exception)
    print("Disconnecting...")
    future = mqtt_connection.disconnect()
    future.add_done_callback(on_disconnected)

def on_disconnected(disconnect_future):
    # type: (Future) -> None
    print("Disconnected.")

def on_update_shadow_accepted(response):
    # type: (iotshadow.UpdateShadowResponse) -> None
    print(f"{response.client_token} Finished updating reported shadow value.")

def on_update_shadow_rejected(error):
    # type: (iotshadow.ErrorResponse) -> None
    exit("Update request was rejected. code:{} message:'{}'".format(
        error.code, error.message))

def on_publish_update_shadow(future):
    # type: (Future) -> None
    try:
        future.result()
        print("Update request published.")
    except Exception as e:
        print("Failed to publish update request.")
        exit(e)

def set_machine_and_publish_update(state):
    token = str(uuid4())
    print(f"{token} Set machine properties")
    for k, v in state.items():
        controller.set_machine_property(k, v)

    request = iotshadow.UpdateNamedShadowRequest(
        thing_name=THING_NAME,
        shadow_name=CONTROLLER_SHADOW_NAME,
        state=iotshadow.ShadowState(
            reported=state,
            desired=state,
        ),
        client_token=token,
    )

    future = shadow_client.publish_update_named_shadow(request, mqtt.QoS.AT_LEAST_ONCE)
    future.add_done_callback(on_publish_update_shadow)

def on_shadow_delta_updated(delta):
    # type: (iotshadow.ShadowDeltaUpdatedEvent) -> None
    try:
        print("Received shadow delta event.")
        if delta.state:
            set_machine_and_publish_update(delta.state)
    except Exception as e:
        exit(e)

def run(sensor, controller, shadow_client):
    try:
        # Subscribe to necessary topics.
        # Note that is **is** important to wait for "accepted/rejected" subscriptions
        # to succeed before publishing the corresponding "request".
        print("Subscribing to Update responses...")
        update_accepted_subscribed_future, _ = shadow_client.subscribe_to_update_named_shadow_accepted(
            request=iotshadow.UpdateNamedShadowSubscriptionRequest(
                thing_name=THING_NAME, shadow_name=CONTROLLER_SHADOW_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_update_shadow_accepted)

        update_rejected_subscribed_future, _ = shadow_client.subscribe_to_update_named_shadow_rejected(
            request=iotshadow.UpdateNamedShadowSubscriptionRequest(
                thing_name=THING_NAME, shadow_name=CONTROLLER_SHADOW_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_update_shadow_rejected)

        # Wait for subscriptions to succeed
        update_accepted_subscribed_future.result()
        update_rejected_subscribed_future.result()

        print("Subscribing to Delta events...")
        delta_subscribed_future, _ = shadow_client.subscribe_to_named_shadow_delta_updated_events(
            request=iotshadow.NamedShadowDeltaUpdatedSubscriptionRequest(
                thing_name=THING_NAME, shadow_name=CONTROLLER_SHADOW_NAME),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_shadow_delta_updated)

        # Wait for subscription to succeed
        delta_subscribed_future.result()

        token = str(uuid4())
        print(f"{token} Updating current shadow state...")
        state = controller.get_machine_property()
        request = iotshadow.UpdateNamedShadowRequest(
            thing_name=THING_NAME,
            shadow_name=CONTROLLER_SHADOW_NAME,
            state=iotshadow.ShadowState(
                reported=state,
            ),
            client_token=token,
        )

        future = shadow_client.publish_update_named_shadow(request, mqtt.QoS.AT_LEAST_ONCE)
        future.add_done_callback(on_publish_update_shadow)

        DHT_MIN_PERIOD = 2
        while True:
            hum, temp = sensor.get_humidity_and_temperature()
            state = {
                "humidity": hum,
                "temperature": temp,
            }
            request = iotshadow.UpdateNamedShadowRequest(
                thing_name=THING_NAME,
                shadow_name=SENSOR_SHADOW_NAME,
                state=iotshadow.ShadowState(
                    reported=state,
                ),
                client_token=token,
            )
            future = shadow_client.publish_update_named_shadow(request, mqtt.QoS.AT_LEAST_ONCE)
            future.add_done_callback(on_publish_update_shadow)

            current_time = time()
            global last_warning_sec
            if temp > THRESHOLD_TEMPERATURE and current_time >= last_warning_sec + WARNING_INTERVAL_SECONDS:
                print(f"temperature {temp} exceeding threshold {THRESHOLD_TEMPERATURE}, publish to '{WARNING_TOPIC}'")

                # send SNS warning
                payload = {
                    "reported_temperature": temp,
                    "threshold_temperature": THRESHOLD_TEMPERATURE
                }
                message_json = json.dumps(payload)
                mqtt_connection.publish(
                    topic=WARNING_TOPIC,
                    payload=message_json,
                    qos=mqtt.QoS.AT_LEAST_ONCE)

                # activate machine
                prop = {
                    "temperature": ACTIVATED_TEMPERATURE,
                    "ac_is_enable": True,
                }
                set_machine_and_publish_update(prop)

                last_warning_sec = current_time
            sleep(DHT_MIN_PERIOD)

    except Exception as e:
        exit(e)

if __name__ == '__main__':
    args = parse_args()
    sensor = MockSensor()
    controller = MockController()

    mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=args.endpoint,
    cert_filepath=args.cert,
    pri_key_filepath=args.key,
    #ca_filepath=args.ca_file,
    client_id="test-" + str(uuid4()))

    print("Connecting to endpoint with client ID")
    connected_future = mqtt_connection.connect()
    shadow_client = iotshadow.IotShadowClient(mqtt_connection)
    connected_future.result()
    print("Connected!")

    run(sensor, controller, shadow_client)
