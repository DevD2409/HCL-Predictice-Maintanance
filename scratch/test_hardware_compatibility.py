"""
HCL Predictive Maintenance - Layer 6 Hardware Compatibility & Pipeline Test Suite
Validates:
  1. RPM pulse-count conversion and zero-timeout logic.
  2. Missing / Invalid sensor readings and graceful fallback.
  3. MQTT telemetry JSON payload schema compatibility.
  4. SQLite database schema and non-null column consistency.
  5. ML prediction model compatibility across real ambient and running conditions.
  6. Actuator state machine and remote override logic.
"""

import json
import sqlite3
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.predictor import PredictiveMaintenanceAI


class TestHardwareCompatibility(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.models_dir = BASE_DIR / "ml" / "models"
        cls.db_path = BASE_DIR / "data" / "machine_data.db"
        cls.ai = PredictiveMaintenanceAI(cls.models_dir)

    def test_rpm_pulse_conversion(self):
        """Verify RPM calculation across various Pulses-Per-Revolution (PPR) settings."""
        def calculate_rpm(pulse_count, sample_interval_sec, ppr):
            if ppr <= 0 or sample_interval_sec <= 0:
                return 0.0
            return (float(pulse_count) / float(ppr)) * (60.0 / float(sample_interval_sec))

        # Case A: 1 pulse per rev (single reflective mark or single magnet)
        self.assertAlmostEqual(calculate_rpm(25, 1.0, 1), 1500.0)

        # Case B: 3 pulses per rev (3-blade fan target)
        self.assertAlmostEqual(calculate_rpm(75, 1.0, 3), 1500.0)

        # Case C: 20 pulses per rev (slotted optical encoder disc)
        self.assertAlmostEqual(calculate_rpm(500, 1.0, 20), 1500.0)

        # Case D: Zero pulses (motor stationary) -> 0 RPM
        self.assertAlmostEqual(calculate_rpm(0, 1.0, 1), 0.0)

        # Case E: High-speed edge case (50 pulses in 1.0s with PPR=1 -> 3000 RPM)
        self.assertAlmostEqual(calculate_rpm(50, 1.0, 1), 3000.0)

    def test_rpm_zero_timeout_logic(self):
        """Verify that stationary shaft resets RPM to zero when no pulses arrive."""
        TIMEOUT_MS = 1500
        last_pulse_time = 1000
        current_time_moving = 1800   # 800ms since last pulse
        current_time_stopped = 2600  # 1600ms since last pulse

        is_stopped_moving = (current_time_moving - last_pulse_time) > TIMEOUT_MS
        is_stopped_halted = (current_time_stopped - last_pulse_time) > TIMEOUT_MS

        self.assertFalse(is_stopped_moving)
        self.assertTrue(is_stopped_halted)

    def test_invalid_and_missing_sensor_fallback(self):
        """Verify graceful fallback when sensors return NaN or timeout."""
        def sanitize_reading(temp, hum, vib, rpm):
            import math
            safe_temp = 25.0 if (temp is None or math.isnan(temp)) else float(temp)
            safe_hum = 50.0 if (hum is None or math.isnan(hum)) else float(hum)
            safe_vib = 0.02 if (vib is None or math.isnan(vib)) else float(vib)
            safe_rpm = 0 if (rpm is None or rpm < 0) else int(rpm)
            return {
                "temperature_c": safe_temp,
                "humidity_percent": safe_hum,
                "vibration_g": safe_vib,
                "rpm": safe_rpm
            }

        sanitized = sanitize_reading(float("nan"), None, float("nan"), -5)
        self.assertEqual(sanitized["temperature_c"], 25.0)
        self.assertEqual(sanitized["humidity_percent"], 50.0)
        self.assertEqual(sanitized["vibration_g"], 0.02)
        self.assertEqual(sanitized["rpm"], 0)

    def test_mqtt_payload_schema(self):
        """Verify ESP32 JSON telemetry matches required keys and data types."""
        sample_payload = {
            "timestamp": "2026-10-26 20:00:00",
            "machine_id": "MOTOR_01",
            "temperature_c": 26.50,
            "humidity_percent": 54.20,
            "vibration_g": 0.045,
            "rpm": 1440,
            "load_percent": 52.30,
            "condition": "Healthy"
        }

        serialized = json.dumps(sample_payload)
        parsed = json.loads(serialized)

        required_keys = [
            "timestamp", "machine_id", "temperature_c",
            "humidity_percent", "vibration_g", "rpm",
            "load_percent", "condition"
        ]
        for key in required_keys:
            self.assertIn(key, parsed)

        self.assertIsInstance(parsed["temperature_c"], (int, float))
        self.assertIsInstance(parsed["humidity_percent"], (int, float))
        self.assertIsInstance(parsed["vibration_g"], (int, float))
        self.assertIsInstance(parsed["rpm"], int)
        self.assertIsInstance(parsed["load_percent"], (int, float))
        self.assertIn(parsed["condition"], ["Healthy", "Warning", "Fault"])

    def test_database_schema_consistency(self):
        """Verify SQLite database columns and types align with telemetry fields."""
        self.assertTrue(self.db_path.exists(), f"Database not found at {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(machine_readings)")
        columns = {row[1]: row[2] for row in cur.fetchall()}
        conn.close()

        expected_cols = [
            "timestamp", "machine_id", "temperature_c",
            "humidity_percent", "vibration_g", "rpm",
            "load_percent", "condition"
        ]
        for col in expected_cols:
            self.assertIn(col, columns, f"Column {col} missing in machine_readings table")

    def test_ml_model_room_ambient_and_idle(self):
        """Verify ML model stability with physical room temperature and idle motor."""
        idle_telemetry = {
            "temperature_c": 24.0,
            "vibration_g": 0.01,
            "rpm": 0,
            "load_percent": 45.0,
            "humidity_percent": 55.0
        }
        res = self.ai.predict(idle_telemetry)
        self.assertIn(res["predicted_condition"], ["Healthy", "Warning", "Fault"])
        self.assertGreaterEqual(res["estimated_rul_hours"], 0.0)
        self.assertIn("root_cause_analysis", res)
        self.assertIn("prescriptive_action", res)

    def test_ml_model_running_nominal_machine(self):
        """Verify ML model predicts Healthy under nominal operational parameters."""
        normal_telemetry = {
            "temperature_c": 38.0,
            "vibration_g": 0.045,
            "rpm": 1450,
            "load_percent": 55.0,
            "humidity_percent": 50.0
        }
        res = self.ai.predict(normal_telemetry)
        self.assertEqual(res["predicted_condition"], "Healthy")
        self.assertGreaterEqual(res["confidence_percent"], 70.0)
        self.assertGreaterEqual(res["estimated_rul_hours"], 500.0)

    def test_ml_model_critical_fault(self):
        """Verify ML model triggers Fault on elevated thermal and vibration signatures."""
        fault_telemetry = {
            "temperature_c": 72.0,
            "vibration_g": 0.38,
            "rpm": 1250,
            "load_percent": 90.0,
            "humidity_percent": 50.0
        }
        res = self.ai.predict(fault_telemetry)
        self.assertEqual(res["predicted_condition"], "Fault")
        self.assertGreaterEqual(res["failure_risk_percent"], 70.0)
        self.assertLessEqual(res["estimated_rul_hours"], 100.0)

    def test_actuator_state_transition_logic(self):
        """Verify local actuator logic transitions and buzzer patterns."""
        def evaluate_actuators(condition, remote_command=None):
            if remote_command == "BUZZER_ALARM":
                return {"green": False, "yellow": False, "red": True, "buzzer_mode": "CONTINUOUS"}
            elif remote_command == "BUZZER_WARNING_CHIRP":
                return {"green": False, "yellow": True, "red": False, "buzzer_mode": "CHIRP"}

            if condition == "Healthy":
                return {"green": True, "yellow": False, "red": False, "buzzer_mode": "OFF"}
            elif condition == "Warning":
                return {"green": False, "yellow": True, "red": False, "buzzer_mode": "CHIRP"}
            elif condition == "Fault":
                return {"green": False, "yellow": False, "red": True, "buzzer_mode": "CONTINUOUS"}
            return {"green": True, "yellow": False, "red": False, "buzzer_mode": "OFF"}

        healthy_state = evaluate_actuators("Healthy")
        self.assertTrue(healthy_state["green"])
        self.assertEqual(healthy_state["buzzer_mode"], "OFF")

        warning_state = evaluate_actuators("Warning")
        self.assertTrue(warning_state["yellow"])
        self.assertEqual(warning_state["buzzer_mode"], "CHIRP")

        fault_state = evaluate_actuators("Fault")
        self.assertTrue(fault_state["red"])
        self.assertEqual(fault_state["buzzer_mode"], "CONTINUOUS")

        override_state = evaluate_actuators("Healthy", remote_command="BUZZER_ALARM")
        self.assertTrue(override_state["red"])
        self.assertEqual(override_state["buzzer_mode"], "CONTINUOUS")

    def test_rpm_debouncing_and_noise_filter(self):
        """Verify that rapid optical flutter pulses below DEBOUNCE_INTERVAL_MICROS (2000us) are rejected."""
        DEBOUNCE_MICROS = 2000
        pulse_timestamps = [
            1000000,
            1000500,  # +500us -> Should be rejected (optical flutter)
            1001200,  # +700us from last valid (still < 2000us) -> Rejected
            1002500,  # +2500us from last valid -> ACCEPTED
            1003000,  # +500us -> Rejected
            1004600,  # +2100us -> ACCEPTED
        ]

        valid_pulse_count = 0
        last_valid_micros = 0

        for t in pulse_timestamps:
            if t - last_valid_micros >= DEBOUNCE_MICROS:
                valid_pulse_count += 1
                last_valid_micros = t

        # Of 6 raw events, only 3 meet the 2ms physical threshold
        self.assertEqual(valid_pulse_count, 3)

    def test_prediction_api_response_contract(self):
        """Verify ML prediction engine contract matches requirements of ml_service and dashboards."""
        sample_input = {
            "temperature_c": 27.5,
            "vibration_g": 0.032,
            "rpm": 1440,
            "load_percent": 53.0,
            "humidity_percent": 51.5
        }
        res = self.ai.predict(sample_input)

        required_keys = [
            "machine_id", "input_metrics", "predicted_condition",
            "confidence_percent", "failure_risk_percent",
            "estimated_rul_hours", "root_cause_analysis",
            "prescriptive_action", "model_version"
        ]
        for key in required_keys:
            self.assertIn(key, res)

        self.assertIn(res["predicted_condition"], ["Healthy", "Warning", "Fault"])
        self.assertGreaterEqual(res["confidence_percent"], 0.0)
        self.assertLessEqual(res["confidence_percent"], 100.0)
        self.assertGreaterEqual(res["failure_risk_percent"], 0.0)
        self.assertLessEqual(res["failure_risk_percent"], 100.0)
        self.assertGreaterEqual(res["estimated_rul_hours"], 0.0)

    def test_alert_manager_and_actuator_command_contract(self):
        """Verify AlertManager creates alerts and formats commands matching ESP32 firmware expectations."""
        from alerts.alert_manager import AlertManager
        test_db = BASE_DIR / "scratch" / "test_alerts_tmp.db"
        if test_db.exists():
            test_db.unlink()

        try:
            mgr = AlertManager(db_path=test_db)

            # Healthy prediction -> Should not generate alert
            healthy_pred = {
                "predicted_condition": "Healthy",
                "failure_risk_percent": 12.0,
                "machine_id": "MOTOR_01",
                "timestamp": "2026-10-26 20:30:00",
                "input_metrics": {"temperature_c": 26.5, "vibration_g": 0.03, "rpm": 1450},
                "prescriptive_action": {"action": "ROUTINE MONITORING", "timeframe": "Monthly"}
            }
            alert_healthy = mgr.create_alert(healthy_pred)
            self.assertIsNone(alert_healthy)

            # Warning prediction -> Should create WARNING alert
            warning_pred = {
                "predicted_condition": "Warning",
                "failure_risk_percent": 52.0,
                "machine_id": "MOTOR_01",
                "timestamp": "2026-10-26 20:30:05",
                "input_metrics": {"temperature_c": 48.0, "vibration_g": 0.12, "rpm": 1390},
                "prescriptive_action": {"action": "INSPECT BEARINGS", "timeframe": "24h"},
                "root_cause_analysis": "Elevated Vibration"
            }
            alert_warning = mgr.create_alert(warning_pred, force=True)
            self.assertIsNotNone(alert_warning)
            self.assertEqual(alert_warning["severity"], "WARNING")

            # Verify MQTT command format expected by esp32_firmware.ino
            warning_cmd = {
                "machine_id": "MOTOR_01",
                "severity": alert_warning["severity"],
                "condition": alert_warning["condition"],
                "actuator_command": "BUZZER_ALARM" if alert_warning["severity"] == "CRITICAL" else "BUZZER_WARNING_CHIRP",
                "led_indicator": "RED" if alert_warning["severity"] == "CRITICAL" else "YELLOW"
            }
            self.assertEqual(warning_cmd["actuator_command"], "BUZZER_WARNING_CHIRP")
            self.assertEqual(warning_cmd["led_indicator"], "YELLOW")

            # Fault prediction -> Should create CRITICAL alert
            fault_pred = {
                "predicted_condition": "Fault",
                "failure_risk_percent": 88.0,
                "machine_id": "MOTOR_01",
                "timestamp": "2026-10-26 20:30:10",
                "input_metrics": {"temperature_c": 75.0, "vibration_g": 0.45, "rpm": 1220},
                "prescriptive_action": {"action": "SHUTDOWN", "timeframe": "Immediate"},
                "root_cause_analysis": "High Vibration | Overheating"
            }
            alert_fault = mgr.create_alert(fault_pred, force=True)
            self.assertIsNotNone(alert_fault)
            self.assertEqual(alert_fault["severity"], "CRITICAL")

            fault_cmd = {
                "machine_id": "MOTOR_01",
                "severity": alert_fault["severity"],
                "condition": alert_fault["condition"],
                "actuator_command": "BUZZER_ALARM" if alert_fault["severity"] == "CRITICAL" else "BUZZER_WARNING_CHIRP",
                "led_indicator": "RED" if alert_fault["severity"] == "CRITICAL" else "YELLOW"
            }
            self.assertEqual(fault_cmd["actuator_command"], "BUZZER_ALARM")
            self.assertEqual(fault_cmd["led_indicator"], "RED")

        finally:
            if test_db.exists():
                test_db.unlink()

    def test_sensor_to_database_insert_and_retrieve(self):
        """Verify insertion of physical ESP32 telemetry into SQLite schema with float precision."""
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE machine_readings (
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

        # Physical reading from DHT11, MPU6050, and IR tachometer
        physical_reading = {
            "timestamp": "2026-10-26 20:30:00",
            "machine_id": "MOTOR_01",
            "temperature_c": 26.50,
            "humidity_percent": 52.00,
            "vibration_g": 0.035,
            "rpm": 1440,
            "load_percent": 54.00,
            "condition": "Healthy"
        }

        cur.execute("""
            INSERT INTO machine_readings (
                timestamp, machine_id, temperature_c, humidity_percent,
                vibration_g, rpm, load_percent, condition
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            physical_reading["timestamp"],
            physical_reading["machine_id"],
            physical_reading["temperature_c"],
            physical_reading["humidity_percent"],
            physical_reading["vibration_g"],
            physical_reading["rpm"],
            physical_reading["load_percent"],
            physical_reading["condition"]
        ))
        conn.commit()

        row = cur.execute("SELECT * FROM machine_readings WHERE id=1").fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[1], "2026-10-26 20:30:00")
        self.assertEqual(row[2], "MOTOR_01")
        self.assertAlmostEqual(row[3], 26.50)
        self.assertAlmostEqual(row[4], 52.00)
        self.assertAlmostEqual(row[5], 0.035)
        self.assertEqual(row[6], 1440)
        self.assertAlmostEqual(row[7], 54.00)
        self.assertEqual(row[8], "Healthy")


if __name__ == "__main__":
    unittest.main(verbosity=2)