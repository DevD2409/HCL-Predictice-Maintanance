import json
import os
import random
import ssl
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Optional winsound for real audio alert on Windows
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


load_dotenv()

BROKER = os.getenv("HIVEMQ_HOST")
PORT = int(os.getenv("HIVEMQ_PORT", "8883"))
USERNAME = os.getenv("HIVEMQ_USERNAME")
PASSWORD = os.getenv("HIVEMQ_PASSWORD")
COMMAND_TOPIC = "machine/commands"
ALERT_TOPIC = "machine/alerts"


class HardwareActuatorController:
    """
    Virtual Actuator Simulator & Display Controller.
    Simulates ESP32-S3 actuator behaviors and visualizes logic state for:
      - Green LED  (GPIO 18 / Normal)
      - Yellow LED (GPIO 17 / Warning)
      - Red LED    (GPIO 5 / Fault)
      - Active Buzzer (GPIO 15 / Audio Alarm via PC speaker)
    """

    def __init__(self):
        self.green_led = True
        self.yellow_led = False
        self.red_led = False
        self.buzzer = False
        self.current_state = "Healthy"
        self.last_beep_time = 0

    def update_actuators(self, condition: str, severity: str = "NORMAL"):
        self.current_state = condition

        if condition == "Healthy" or severity == "NORMAL":
            self.green_led = True
            self.yellow_led = False
            self.red_led = False
            self.buzzer = False
        elif condition == "Warning" or severity == "WARNING":
            self.green_led = False
            self.yellow_led = True
            self.red_led = False
            self.buzzer = True
            self._trigger_beep(frequency=1200, duration_ms=150)
        elif condition == "Fault" or severity == "CRITICAL":
            self.green_led = False
            self.yellow_led = False
            self.red_led = True
            self.buzzer = True
            self._trigger_beep(frequency=2400, duration_ms=400)

        self.display_pin_status()

    def _trigger_beep(self, frequency=1500, duration_ms=200):
        now = time.time()
        if now - self.last_beep_time > 1.5:
            self.last_beep_time = now
            if HAS_WINSOUND and sys.platform == "win32":
                try:
                    winsound.Beep(frequency, duration_ms)
                except Exception:
                    pass

    def display_pin_status(self):
        g_box = "[ON]" if self.green_led else "[OFF]"
        y_box = "[ON]" if self.yellow_led else "[OFF]"
        r_box = "[ON]" if self.red_led else "[OFF]"
        b_box = "[ALARM]" if self.buzzer else "[SILENT]"

        print(
            f" [VIRTUAL ACTUATORS] State: {self.current_state:7} | "
            f"GPIO 18 (Green): {g_box} | "
            f"GPIO 17 (Yellow): {y_box} | "
            f"GPIO 5 (Red): {r_box} | "
            f"GPIO 15 (Buzzer): {b_box}"
        )


actuators = HardwareActuatorController()


# -------------------------------------------------
# MQTT Client Callback Handling
# -------------------------------------------------
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("\n[Hardware Bridge] Connected to HiveMQ Cloud TLS.")
        client.subscribe(COMMAND_TOPIC, qos=1)
        client.subscribe(ALERT_TOPIC, qos=1)
        print(f"[Hardware Bridge] Subscribed to Actuator Topics: {COMMAND_TOPIC}, {ALERT_TOPIC}\n")
    else:
        print(f"[Hardware Bridge] Connection failed: {reason_code}")


def on_message(client, userdata, message):
    try:
        payload = message.payload.decode("utf-8")
        data = json.loads(payload)

        condition = data.get("condition", "Healthy")
        severity = data.get("severity", "NORMAL")
        cmd = data.get("actuator_command", "")

        print(f"\n>> [INCOMING CLOUD COMMAND] Condition: {condition} | Severity: {severity} | Cmd: {cmd}")
        actuators.update_actuators(condition, severity)

    except Exception as e:
        print(f"[Hardware Bridge] Payload decode error: {e}")


def run_bridge():
    print("=" * 65)
    print(" HCL Layer 6 - Virtual Hardware Actuator Simulator (ESP32-S3)")
    print("=" * 65)
    print("Listening for MQTT Alert Commands from Cloud AI Service...")
    print("Initial Pin States:")
    actuators.display_pin_status()
    print("-" * 65)

    client_id = f"VirtualActuator_{uuid.uuid4().hex[:6]}"
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        protocol=mqtt.MQTTv311,
    )

    if USERNAME and PASSWORD:
        client.username_pw_set(USERNAME, PASSWORD)

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    client.tls_set_context(context)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[Hardware Bridge] Stopped by user.")
        client.disconnect()


if __name__ == "__main__":
    run_bridge()