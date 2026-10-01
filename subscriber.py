import csv
import json
import os
import ssl
import time
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv


# -------------------------------------------------
# Configuration
# -------------------------------------------------

load_dotenv()

BROKER = os.getenv("HIVEMQ_HOST")
PORT = int(os.getenv("HIVEMQ_PORT", "8883"))
USERNAME = os.getenv("HIVEMQ_USERNAME")
PASSWORD = os.getenv("HIVEMQ_PASSWORD")
TOPIC = os.getenv("MQTT_TOPIC")


# -------------------------------------------------
# CSV configuration
# -------------------------------------------------

DATA_FOLDER = Path("data")
DATA_FOLDER.mkdir(exist_ok=True)

CSV_FILE = DATA_FOLDER / "machine_data.csv"

FIELDS = [
    "timestamp",
    "machine_id",
    "temperature_c",
    "humidity_percent",
    "vibration_g",
    "rpm",
    "load_percent",
    "condition"
]


# -------------------------------------------------
# MQTT callbacks
# -------------------------------------------------

def on_connect(client, userdata, flags, reason_code, properties):

    if reason_code == 0:

        print("Connected to HiveMQ Cloud")

        client.subscribe(
            TOPIC,
            qos=1
        )

        print("Subscribed to:")
        print(TOPIC)

        print("\nWaiting for machine data...\n")

    else:

        print(
            "Connection failed:",
            reason_code
        )


def on_message(client, userdata, message):

    try:

        payload = message.payload.decode("utf-8")

        data = json.loads(payload)

        write_header = (
            not CSV_FILE.exists()
            or CSV_FILE.stat().st_size == 0
        )

        with CSV_FILE.open(
            mode="a",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS
            )

            if write_header:
                writer.writeheader()

            writer.writerow({
                field: data.get(field, "")
                for field in FIELDS
            })

        print(
            f"Saved | "
            f"{data['condition']:7} | "
            f"Temp: {data['temperature_c']} °C | "
            f"Vib: {data['vibration_g']} g | "
            f"RPM: {data['rpm']}"
        )

    except Exception as error:

        print(
            "Error processing message:",
            error
        )


# -------------------------------------------------
# MQTT client
# -------------------------------------------------

subscriber = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=f"HCL_Subscriber_{uuid.uuid4().hex[:8]}"
)

subscriber.username_pw_set(
    USERNAME,
    PASSWORD
)

subscriber.tls_set(
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

subscriber.on_connect = on_connect
subscriber.on_message = on_message


# -------------------------------------------------
# Start subscriber
# -------------------------------------------------

print("Connecting to HiveMQ...")

subscriber.connect(
    BROKER,
    PORT,
    keepalive=60
)

try:

    subscriber.loop_forever()

except KeyboardInterrupt:

    print("\nSubscriber stopped.")

    subscriber.disconnect()