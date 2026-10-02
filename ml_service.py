import json
import os
import sqlite3
import ssl
import threading
import time
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from ml.predictor import PredictiveMaintenanceAI
from alerts.alert_manager import AlertManager
from auth.auth_manager import AuthManager


# -------------------------------------------------
# Load HiveMQ & Service Configuration
# -------------------------------------------------
load_dotenv()

BROKER = os.getenv("HIVEMQ_HOST")
PORT = int(os.getenv("HIVEMQ_PORT", "8883"))
USERNAME = os.getenv("HIVEMQ_USERNAME")
PASSWORD = os.getenv("HIVEMQ_PASSWORD")
TELEMETRY_TOPIC = os.getenv("MQTT_TOPIC", "machine/telemetry")
ALERT_TOPIC = "machine/alerts"
COMMAND_TOPIC = "machine/commands"

SERVER_PORT = int(os.getenv("AI_SERVICE_PORT", "8000"))
DB_PATH = Path("data") / "machine_data.db"


ai_engine = PredictiveMaintenanceAI()
alert_mgr = AlertManager()
auth_mgr = AuthManager()

mqtt_client = None
last_analyzed_id = 0


# -------------------------------------------------
# MQTT Integration for Publishing Alerts & Commands
# -------------------------------------------------
def init_mqtt():
    global mqtt_client
    if not (BROKER and USERNAME and PASSWORD):
        print("[AI Service] HiveMQ credentials not configured in .env. MQTT alert publishing disabled.")
        return

    try:
        mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"AI_Service_{uuid.uuid4().hex[:8]}"
        )
        mqtt_client.username_pw_set(USERNAME, PASSWORD)
        mqtt_client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                print(f"[AI Service] Connected to HiveMQ. Alert publishing active on: {ALERT_TOPIC}")
            else:
                print(f"[AI Service] HiveMQ connection failed: {reason_code}")

        mqtt_client.on_connect = on_connect
        mqtt_client.connect(BROKER, PORT, keepalive=60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"[AI Service] MQTT init error: {e}")


def publish_alert_mqtt(alert_data, command_payload):
    if mqtt_client and mqtt_client.is_connected():
        try:
            mqtt_client.publish(ALERT_TOPIC, json.dumps(alert_data), qos=1)
            mqtt_client.publish(COMMAND_TOPIC, json.dumps(command_payload), qos=1)
        except Exception as e:
            print(f"[AI Service] MQTT publish error: {e}")


# -------------------------------------------------
# Continuous Database Monitor & Prediction Loop
# -------------------------------------------------
def monitor_telemetry_loop():
    """Continuously evaluates new readings in SQLite, triggers AI inference, and generates alerts."""
    global last_analyzed_id
    print("[AI Service] Background telemetry inference engine started.")

    while True:
        try:
            if DB_PATH.exists():
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, timestamp, machine_id, temperature_c, humidity_percent,
                           vibration_g, rpm, load_percent, condition
                    FROM machine_readings
                    WHERE id > ?
                    ORDER BY id ASC
                    LIMIT 10
                """, (last_analyzed_id,))
                rows = cursor.fetchall()
                conn.close()

                for row in rows:
                    row_id, ts, mid, temp, hum, vib, rpm, load, cond = row
                    last_analyzed_id = row_id

                    telemetry = {
                        "id": row_id,
                        "timestamp": ts,
                        "machine_id": mid,
                        "temperature_c": temp,
                        "humidity_percent": hum,
                        "vibration_g": vib,
                        "rpm": rpm,
                        "load_percent": load,
                        "condition": cond
                    }

                    # Run AI prediction
                    prediction = ai_engine.predict(telemetry)

                    # Trigger alert if Warning or Fault
                    alert = alert_mgr.create_alert(prediction)
                    if alert:
                        print(f"[ALERT GENERATED] ID: {alert['id']} | {alert['severity']} | Risk: {alert['failure_risk_percent']}% | {alert['condition']}")

                        command = {
                            "machine_id": mid,
                            "timestamp": ts,
                            "severity": alert["severity"],
                            "condition": alert["condition"],
                            "failure_risk_percent": alert["failure_risk_percent"],
                            "actuator_command": "BUZZER_ALARM" if alert["severity"] == "CRITICAL" else "BUZZER_WARNING_CHIRP",
                            "led_indicator": "RED" if alert["severity"] == "CRITICAL" else "YELLOW",
                            "root_cause": alert["root_cause"]
                        }
                        publish_alert_mqtt(alert, command)

        except Exception as e:
            print(f"[AI Service] Monitor loop error: {e}")

        time.sleep(2)


# -------------------------------------------------
# HTTP REST API Handler
# -------------------------------------------------
class RequestHandler(BaseHTTPRequestHandler):

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "status": "online",
                "service": "HCL Predictive Maintenance AI Engine",
                "version": "1.0",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }).encode("utf-8"))

        elif path == "/latest-prediction":
            # Fetch latest SQLite row and run inference
            if DB_PATH.exists():
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, timestamp, machine_id, temperature_c, humidity_percent,
                           vibration_g, rpm, load_percent, condition
                    FROM machine_readings
                    ORDER BY id DESC LIMIT 1
                """)
                row = cursor.fetchone()
                conn.close()

                if row:
                    telemetry = {
                        "id": row[0],
                        "timestamp": row[1],
                        "machine_id": row[2],
                        "temperature_c": row[3],
                        "humidity_percent": row[4],
                        "vibration_g": row[5],
                        "rpm": row[6],
                        "load_percent": row[7],
                        "condition": row[8]
                    }
                    pred = ai_engine.predict(telemetry)
                    self._set_headers(200)
                    self.wfile.write(json.dumps(pred).encode("utf-8"))
                    return

            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "No telemetry data available"}).encode("utf-8"))

        elif path == "/alerts":
            alerts = alert_mgr.get_recent_alerts(limit=50)
            self._set_headers(200)
            self.wfile.write(json.dumps({"alerts": alerts, "count": len(alerts)}).encode("utf-8"))

        elif path == "/metrics":
            self._set_headers(200)
            self.wfile.write(json.dumps(ai_engine.metrics).encode("utf-8"))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": f"Endpoint {path} not found"}).encode("utf-8"))

    def do_POST(self):
        path = self.path.split("?")[0]
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Invalid JSON payload"}).encode("utf-8"))
            return

        if path == "/predict":
            pred = ai_engine.predict(data)
            # Create alert if necessary
            alert_mgr.create_alert(pred)
            self._set_headers(200)
            self.wfile.write(json.dumps(pred).encode("utf-8"))

        elif path == "/login":
            username = data.get("username", "")
            password = data.get("password", "")
            success, result = auth_mgr.authenticate(username, password)
            if success:
                self._set_headers(200)
                self.wfile.write(json.dumps({"authenticated": True, "user": result}).encode("utf-8"))
            else:
                self._set_headers(401)
                self.wfile.write(json.dumps({"authenticated": False, "error": result}).encode("utf-8"))

        elif path == "/acknowledge-alert":
            alert_id = data.get("alert_id")
            user = data.get("user", "Operator")
            if alert_id:
                alert_mgr.acknowledge_alert(alert_id, user)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "alert_id": alert_id}).encode("utf-8"))
            else:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Missing alert_id"}).encode("utf-8"))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": f"Endpoint {path} not found"}).encode("utf-8"))

    def log_message(self, format, *args):
        # Silence default request logging to avoid terminal clutter
        pass


def run_server():
    init_mqtt()

    # Start background monitor thread
    monitor_thread = threading.Thread(target=monitor_telemetry_loop, daemon=True)
    monitor_thread.start()

    server_address = ("", SERVER_PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    print("=" * 60)
    print(f" HCL Predictive Maintenance AI Service Running on Port {SERVER_PORT}")
    print(f" Endpoints:")
    print(f"   - GET  http://localhost:{SERVER_PORT}/health")
    print(f"   - POST http://localhost:{SERVER_PORT}/predict")
    print(f"   - GET  http://localhost:{SERVER_PORT}/latest-prediction")
    print(f"   - GET  http://localhost:{SERVER_PORT}/alerts")
    print(f"   - POST http://localhost:{SERVER_PORT}/login")
    print(f"   - GET  http://localhost:{SERVER_PORT}/metrics")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping AI Service...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
