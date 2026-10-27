import unittest
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from alerts.alert_manager import AlertManager


class TestAlertManager(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary SQLite database for each test
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.test_db_path = Path(self.temp_file.name)
        self.mgr = AlertManager(db_path=self.test_db_path)

    def tearDown(self):
        if self.test_db_path.exists():
            try:
                self.test_db_path.unlink()
            except Exception:
                pass

    # -------------------------------------------------------------
    # 1. Healthy Readings with Risk Below 40% (Suppression)
    # -------------------------------------------------------------
    def test_healthy_low_risk_no_alert(self):
        """Confirm Healthy readings with risk < 40% do not create alerts."""
        pred = {
            "predicted_condition": "Healthy",
            "failure_risk_percent": 10.75,
            "machine_id": "MOTOR_01",
            "timestamp": "2026-10-28 00:00:01",
            "input_metrics": {"temperature_c": 26.5, "vibration_g": 0.025, "rpm": 0},
            "root_cause_analysis": "Machine stationary / at rest",
            "prescriptive_action": {"action": "ROUTINE MONITORING", "timeframe": "Monthly"}
        }
        res = self.mgr.create_alert(pred)
        self.assertIsNone(res)
        self.assertEqual(self.mgr.get_active_count(), 0)
        self.assertEqual(len(self.mgr.get_recent_alerts()), 0)

    def test_healthy_at_boundary_39_no_alert(self):
        """Risk 39.9% with Healthy condition must be suppressed."""
        pred = {
            "predicted_condition": "Healthy",
            "failure_risk_percent": 39.9,
            "machine_id": "MOTOR_01",
            "input_metrics": {"temperature_c": 27.0, "vibration_g": 0.03, "rpm": 0}
        }
        res = self.mgr.create_alert(pred)
        self.assertIsNone(res)
        self.assertEqual(self.mgr.get_active_count(), 0)

    # -------------------------------------------------------------
    # 2. Warning / High-Risk Thresholds & Severity Mapping
    # -------------------------------------------------------------
    def test_healthy_with_elevated_risk_triggers_warning(self):
        """Healthy condition with risk >= 40% triggers WARNING alert."""
        pred = {
            "predicted_condition": "Healthy",
            "failure_risk_percent": 42.0,
            "machine_id": "MOTOR_01",
            "timestamp": "2026-10-28 00:00:05",
            "input_metrics": {"temperature_c": 35.0, "vibration_g": 0.06, "rpm": 1400},
            "root_cause_analysis": "Elevated dynamic stress",
            "prescriptive_action": {"action": "CHECK LUBRICATION", "timeframe": "48h"}
        }
        alert = self.mgr.create_alert(pred)
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "WARNING")
        self.assertEqual(alert["condition"], "Healthy")
        self.assertEqual(alert["failure_risk_percent"], 42.0)
        self.assertEqual(alert["status"], "ACTIVE")

    def test_warning_condition_triggers_warning(self):
        """Condition 'Warning' with risk < 75% maps to severity 'WARNING'."""
        pred = {
            "predicted_condition": "Warning",
            "failure_risk_percent": 55.0,
            "machine_id": "MOTOR_01",
            "timestamp": "2026-10-28 00:00:10",
            "input_metrics": {"temperature_c": 50.0, "vibration_g": 0.12, "rpm": 1380},
            "root_cause_analysis": "Elevated Vibration",
            "prescriptive_action": {"action": "INSPECT BEARINGS", "timeframe": "24h"}
        }
        alert = self.mgr.create_alert(pred)
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "WARNING")

    def test_fault_condition_triggers_critical(self):
        """Condition 'Fault' maps to severity 'CRITICAL'."""
        pred = {
            "predicted_condition": "Fault",
            "failure_risk_percent": 88.0,
            "machine_id": "MOTOR_01",
            "timestamp": "2026-10-28 00:00:15",
            "input_metrics": {"temperature_c": 75.0, "vibration_g": 0.45, "rpm": 1200},
            "root_cause_analysis": "High Vibration | Overheating",
            "prescriptive_action": {"action": "EMERGENCY SHUTDOWN", "timeframe": "Immediate"}
        }
        alert = self.mgr.create_alert(pred)
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "CRITICAL")

    def test_risk_above_75_triggers_critical(self):
        """Failure risk >= 75% maps to severity 'CRITICAL' regardless of condition."""
        pred = {
            "predicted_condition": "Warning",
            "failure_risk_percent": 76.5,
            "machine_id": "MOTOR_01",
            "timestamp": "2026-10-28 00:00:20",
            "input_metrics": {"temperature_c": 55.0, "vibration_g": 0.18, "rpm": 1360},
            "root_cause_analysis": "Elevated Vibration",
            "prescriptive_action": {"action": "URGENT INSPECTION", "timeframe": "12h"}
        }
        alert = self.mgr.create_alert(pred)
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "CRITICAL")

    # -------------------------------------------------------------
    # 3. Cooldown Behavior (Suppression of Rapid Duplicates)
    # -------------------------------------------------------------
    def test_cooldown_suppression(self):
        """Verify identical severity alerts within 15 seconds are suppressed unless force=True."""
        pred = {
            "predicted_condition": "Warning",
            "failure_risk_percent": 50.0,
            "machine_id": "MOTOR_01",
            "timestamp": "2026-10-28 00:00:25",
            "input_metrics": {"temperature_c": 48.0, "vibration_g": 0.10, "rpm": 1400}
        }
        first = self.mgr.create_alert(pred)
        self.assertIsNotNone(first)

        # Immediate second alert of same severity should be suppressed by cooldown
        second = self.mgr.create_alert(pred)
        self.assertIsNone(second)

        # But with force=True, it should bypass cooldown
        forced = self.mgr.create_alert(pred, force=True)
        self.assertIsNotNone(forced)

    # -------------------------------------------------------------
    # 4. Persistence, Acknowledgment and Resolution Lifecycle
    # -------------------------------------------------------------
    def test_alert_lifecycle_persistence_and_acknowledgment(self):
        """Verify full lifecycle: create (ACTIVE) -> acknowledge (ACKNOWLEDGED) -> resolve (RESOLVED)."""
        pred = {
            "predicted_condition": "Fault",
            "failure_risk_percent": 90.0,
            "machine_id": "MOTOR_01",
            "timestamp": "2026-10-28 00:00:30",
            "input_metrics": {"temperature_c": 70.0, "vibration_g": 0.35, "rpm": 1250},
            "root_cause_analysis": "Bearing cage failure",
            "prescriptive_action": {"action": "SHUTDOWN", "timeframe": "Immediate"}
        }
        alert = self.mgr.create_alert(pred)
        self.assertIsNotNone(alert)
        alert_id = alert["id"]

        # Check persistence in SQLite
        recent = self.mgr.get_recent_alerts(limit=5)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["id"], alert_id)
        self.assertEqual(recent[0]["status"], "ACTIVE")
        self.assertEqual(self.mgr.get_active_count(), 1)

        # Acknowledge alert
        ack_res = self.mgr.acknowledge_alert(alert_id, user="Operator_John")
        self.assertTrue(ack_res)

        # Verify status changed to ACKNOWLEDGED
        active_cnt = self.mgr.get_active_count()
        self.assertEqual(active_cnt, 0)  # No longer active
        acked_alerts = self.mgr.get_recent_alerts(limit=5, status="ACKNOWLEDGED")
        self.assertEqual(len(acked_alerts), 1)
        self.assertEqual(acked_alerts[0]["acknowledged_by"], "Operator_John")
        self.assertIsNotNone(acked_alerts[0]["acknowledged_at"])

        # Resolve alert
        res_res = self.mgr.resolve_alert(alert_id, user="Reliability_Engineer_Alice")
        self.assertTrue(res_res)

        # Verify status changed to RESOLVED
        resolved_alerts = self.mgr.get_recent_alerts(limit=5, status="RESOLVED")
        self.assertEqual(len(resolved_alerts), 1)
        self.assertEqual(resolved_alerts[0]["acknowledged_by"], "Reliability_Engineer_Alice")


if __name__ == "__main__":
    unittest.main()
