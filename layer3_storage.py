import json
import os
import ssl
import sqlite3
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
# SQLite database
# -------------------------------------------------

DATA_FOLDER = Path("data")
DATA_FOLDER.mkdir(exist_ok=True)

DATABASE = DATA_FOLDER / "machine_data.db"


def create_database():

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS machine_readings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT NOT NULL,

            machine_id TEXT NOT NULL,

            temperature_c REAL,

            humidity_percent REAL,

            vibration_g REAL,

            rpm INTEGER,

            load_percent REAL,

            condition TEXT
        )
    """)

    connection.commit()

    connection.close()

    print("SQLite database ready:")
    print(DATABASE)


# -------------------------------------------------
# Save one MQTT reading
# -------------------------------------------------

def save_to_database(data):

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO machine_readings (

            timestamp,
            machine_id,
            temperature_c,
            humidity_percent,
            vibration_g,
            rpm,
            load_percent,
            condition

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)

    """, (

        data.get("timestamp"),
        data.get("machine_id"),
        data.get("temperature_c"),
        data.get("humidity_percent"),
        data.get("vibration_g"),
        data.get("rpm"),
        data.get("load_percent"),
        data.get("condition")

    ))

    connection.commit()

    connection.close()


# -------------------------------------------------
# MQTT callbacks
# -------------------------------------------------

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

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


def on_message(
    client,
    userdata,
    message
):

    try:

        payload = message.payload.decode(
            "utf-8"
        )

        data = json.loads(payload)

        save_to_database(data)

        print(
            f"DB Saved | "
            f"{data['condition']:7} | "
            f"Temp: {data['temperature_c']} °C | "
            f"Vibration: {data['vibration_g']} g | "
            f"RPM: {data['rpm']}"
        )

    except Exception as error:

        print(
            "Database error:",
            error
        )


# -------------------------------------------------
# Create DB
# -------------------------------------------------

create_database()


# -------------------------------------------------
# MQTT client
# -------------------------------------------------

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=f"Layer3_SQLite_{uuid.uuid4().hex[:8]}"
)


client.username_pw_set(
    USERNAME,
    PASSWORD
)


client.tls_set(
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)


client.on_connect = on_connect
client.on_message = on_message


# -------------------------------------------------
# Connect
# -------------------------------------------------

print("\nLayer 3 - SQLite Storage")
print("------------------------")

client.connect(
    BROKER,
    PORT,
    keepalive=60
)


try:

    client.loop_forever()

except KeyboardInterrupt:

    print("\nLayer 3 storage stopped.")

    client.disconnect()