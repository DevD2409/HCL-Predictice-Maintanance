import json
import os
import ssl
import threading
import uuid

from collections import deque

import paho.mqtt.client as mqtt
from dotenv import load_dotenv


# -------------------------------------------------
# Load configuration
# -------------------------------------------------

load_dotenv()

BROKER = os.getenv("HIVEMQ_HOST")
PORT = int(os.getenv("HIVEMQ_PORT", "8883"))
USERNAME = os.getenv("HIVEMQ_USERNAME")
PASSWORD = os.getenv("HIVEMQ_PASSWORD")
TOPIC = os.getenv("MQTT_TOPIC")


# -------------------------------------------------
# MQTT Receiver Class
# -------------------------------------------------

class MQTTReceiver:

    def __init__(self):

        self.latest_data = None

        # Store only latest 60 readings
        self.history = deque(maxlen=60)

        # Prevent dashboard and MQTT thread
        # from accessing data simultaneously
        self.lock = threading.Lock()

        self.connected = False


        # Create MQTT client
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"Layer2_Dashboard_{uuid.uuid4().hex[:8]}"
        )


        # Credentials
        self.client.username_pw_set(
            USERNAME,
            PASSWORD
        )


        # TLS security
        self.client.tls_set(
            tls_version=ssl.PROTOCOL_TLS_CLIENT
        )


        # MQTT callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message


    # -------------------------------------------------
    # Connection callback
    # -------------------------------------------------

    def on_connect(
        self,
        client,
        userdata,
        flags,
        reason_code,
        properties
    ):

        if reason_code == 0:

            self.connected = True

            print("Connected to HiveMQ Cloud")

            client.subscribe(
                TOPIC,
                qos=1
            )

            print("Subscribed to:", TOPIC)

        else:

            self.connected = False

            print(
                "Connection failed:",
                reason_code
            )


    # -------------------------------------------------
    # Message callback
    # -------------------------------------------------

    def on_message(
        self,
        client,
        userdata,
        message
    ):

        try:

            payload = message.payload.decode(
                "utf-8"
            )

            data = json.loads(payload)


            # Store safely in memory
            with self.lock:

                self.latest_data = data

                self.history.append(data)


            print(
                f"Received | "
                f"{data['condition']:7} | "
                f"Temp: {data['temperature_c']} °C | "
                f"Vibration: {data['vibration_g']} g | "
                f"RPM: {data['rpm']}"
            )


        except Exception as error:

            print(
                "MQTT message error:",
                error
            )


    # -------------------------------------------------
    # Start MQTT connection
    # -------------------------------------------------

    def start(self):

        if self.client.is_connected():
            return

        print("Connecting to HiveMQ...")

        self.client.connect(
            BROKER,
            PORT,
            keepalive=60
        )

        # MQTT runs in background thread
        self.client.loop_start()


    # -------------------------------------------------
    # Give dashboard a safe copy
    # -------------------------------------------------

    def get_data(self):

        with self.lock:

            latest = (
                self.latest_data.copy()
                if self.latest_data
                else None
            )

            history = list(
                self.history
            )

        return latest, history