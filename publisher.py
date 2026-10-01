import json
import random
import ssl
import time
import uuid
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os


# -------------------------------------------------
# Load HiveMQ configuration
# -------------------------------------------------

load_dotenv()

BROKER = os.getenv("HIVEMQ_HOST")
PORT = int(os.getenv("HIVEMQ_PORT", "8883"))
USERNAME = os.getenv("HIVEMQ_USERNAME")
PASSWORD = os.getenv("HIVEMQ_PASSWORD")
TOPIC = os.getenv("MQTT_TOPIC")


# -------------------------------------------------
# Generate synthetic rotating-machine data
# -------------------------------------------------

def generate_machine_data(condition):

    if condition == "Healthy":

        temperature = random.uniform(35, 45)
        humidity = random.uniform(40, 60)
        vibration = random.uniform(0.02, 0.08)
        rpm = random.randint(1420, 1480)
        load = random.uniform(40, 70)

    elif condition == "Warning":

        temperature = random.uniform(45, 60)
        humidity = random.uniform(40, 65)
        vibration = random.uniform(0.08, 0.20)
        rpm = random.randint(1350, 1450)
        load = random.uniform(60, 85)

    else:  # Fault

        temperature = random.uniform(60, 80)
        humidity = random.uniform(40, 70)
        vibration = random.uniform(0.20, 0.50)
        rpm = random.randint(1200, 1400)
        load = random.uniform(75, 100)

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "machine_id": "MOTOR_01",
        "temperature_c": round(temperature, 2),
        "humidity_percent": round(humidity, 2),
        "vibration_g": round(vibration, 3),
        "rpm": rpm,
        "load_percent": round(load, 2),
        "condition": condition
    }


# -------------------------------------------------
# MQTT callbacks
# -------------------------------------------------

def on_connect(client, userdata, flags, reason_code, properties):

    if reason_code == 0:
        print("Connected to HiveMQ Cloud")
    else:
        print("Connection failed:", reason_code)


# -------------------------------------------------
# Create MQTT client
# -------------------------------------------------

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=f"HCL_Publisher_{uuid.uuid4().hex[:8]}"
)

client.username_pw_set(
    USERNAME,
    PASSWORD
)

client.tls_set(
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

client.on_connect = on_connect


# -------------------------------------------------
# Connect
# -------------------------------------------------

print("Connecting to HiveMQ...")

client.connect(
    BROKER,
    PORT,
    keepalive=60
)

client.loop_start()

time.sleep(2)


# -------------------------------------------------
# Continuously simulate the machine
# -------------------------------------------------

reading_number = 0

try:

    while True:

        cycle_position = reading_number % 60

        if cycle_position < 30:
            condition = "Healthy"

        elif cycle_position < 50:
            condition = "Warning"

        else:
            condition = "Fault"

        data = generate_machine_data(condition)

        payload = json.dumps(data)

        result = client.publish(
            TOPIC,
            payload,
            qos=1
        )

        result.wait_for_publish()

        print(
            f"{reading_number + 1:03d} | "
            f"{data['condition']:7} | "
            f"Temp: {data['temperature_c']:5.2f} °C | "
            f"Vib: {data['vibration_g']:.3f} g | "
            f"RPM: {data['rpm']} | "
            f"Load: {data['load_percent']:5.2f}%"
        )

        reading_number += 1

        time.sleep(1)


except KeyboardInterrupt:

    print("\nPublisher stopped.")


finally:

    client.loop_stop()
    client.disconnect()