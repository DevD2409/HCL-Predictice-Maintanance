import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.predictor import PredictiveMaintenanceAI


class TestPredictorRootCause(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai = PredictiveMaintenanceAI(models_dir=PROJECT_ROOT / "ml" / "models")

    # -------------------------------------------------------------
    # 1. RPM = 0 (Stationary Motor)
    # -------------------------------------------------------------
    def test_rpm_zero_stationary_nominal(self):
        """Verify RPM = 0 with normal readings produces neutral 'Machine stationary / at rest'."""
        root_cause = self.ai.diagnose_root_cause(
            temp=27.4, vib=0.025, rpm=0, load=0.0, condition="Healthy"
        )
        self.assertEqual(root_cause, "Machine stationary / at rest")
        self.assertNotIn("Under-speed Phenomenon", root_cause)
        self.assertNotIn("Nominal Machine Operation", root_cause)

    def test_rpm_zero_float(self):
        """Verify float 0.0 RPM produces 'Machine stationary / at rest'."""
        root_cause = self.ai.diagnose_root_cause(
            temp=25.0, vib=0.02, rpm=0.0, load=0.0, condition="Healthy"
        )
        self.assertEqual(root_cause, "Machine stationary / at rest")
        self.assertNotIn("Under-speed Phenomenon", root_cause)

    def test_rpm_zero_with_temperature_fault(self):
        """Verify RPM = 0 does not mask or claim health if other defects exist (e.g. overheating)."""
        root_cause = self.ai.diagnose_root_cause(
            temp=65.0, vib=0.025, rpm=0, load=0.0, condition="Fault"
        )
        self.assertIn("Excessive Temperature", root_cause)
        self.assertIn("Machine stationary / at rest", root_cause)
        self.assertNotIn("Under-speed Phenomenon", root_cause)

    def test_rpm_zero_with_vibration_defect(self):
        """Verify RPM = 0 with high vibration reports both vibration and stationary status."""
        root_cause = self.ai.diagnose_root_cause(
            temp=30.0, vib=0.22, rpm=0, load=0.0, condition="Fault"
        )
        self.assertIn("High Vibration", root_cause)
        self.assertIn("Machine stationary / at rest", root_cause)
        self.assertNotIn("Under-speed Phenomenon", root_cause)

    # -------------------------------------------------------------
    # 2. RPM Between 1 and 1349 (Running Motor Operating Under-Speed)
    # -------------------------------------------------------------
    def test_rpm_lower_bound_under_speed(self):
        """Verify RPM = 1 triggers under-speed diagnosis."""
        root_cause = self.ai.diagnose_root_cause(
            temp=40.0, vib=0.05, rpm=1, load=40.0, condition="Warning"
        )
        self.assertIn("Under-speed Phenomenon", root_cause)
        self.assertNotIn("Machine stationary / at rest", root_cause)

    def test_rpm_mid_range_under_speed(self):
        """Verify RPM = 800 triggers under-speed diagnosis."""
        root_cause = self.ai.diagnose_root_cause(
            temp=40.0, vib=0.05, rpm=800, load=50.0, condition="Warning"
        )
        self.assertIn("Under-speed Phenomenon", root_cause)
        self.assertNotIn("Machine stationary / at rest", root_cause)

    def test_rpm_upper_bound_under_speed(self):
        """Verify RPM = 1349 triggers under-speed diagnosis."""
        root_cause = self.ai.diagnose_root_cause(
            temp=40.0, vib=0.05, rpm=1349, load=50.0, condition="Warning"
        )
        self.assertIn("Under-speed Phenomenon", root_cause)
        self.assertNotIn("Machine stationary / at rest", root_cause)

    # -------------------------------------------------------------
    # 3. RPM >= 1350 (Normal Operating Speed Range)
    # -------------------------------------------------------------
    def test_rpm_threshold_boundary(self):
        """Verify RPM = 1350 does not trigger under-speed."""
        root_cause = self.ai.diagnose_root_cause(
            temp=40.0, vib=0.05, rpm=1350, load=50.0, condition="Healthy"
        )
        self.assertNotIn("Under-speed Phenomenon", root_cause)
        self.assertNotIn("Machine stationary / at rest", root_cause)
        self.assertEqual(root_cause, "Nominal Machine Operation (All telemetry within ISO standard limits)")

    def test_rpm_nominal_rated_speed(self):
        """Verify nominal operating RPM (1450) produces nominal machine operation."""
        root_cause = self.ai.diagnose_root_cause(
            temp=40.0, vib=0.05, rpm=1450, load=50.0, condition="Healthy"
        )
        self.assertEqual(root_cause, "Nominal Machine Operation (All telemetry within ISO standard limits)")
        self.assertNotIn("Under-speed Phenomenon", root_cause)
        self.assertNotIn("Machine stationary / at rest", root_cause)

    def test_rpm_nominal_with_heavy_load(self):
        """Verify high RPM with heavy load reports heavy load without under-speed."""
        root_cause = self.ai.diagnose_root_cause(
            temp=40.0, vib=0.05, rpm=1450, load=80.0, condition="Warning"
        )
        self.assertIn("Heavy Dynamic Load", root_cause)
        self.assertNotIn("Under-speed Phenomenon", root_cause)

    # -------------------------------------------------------------
    # 4. End-to-End Pipeline Integration Check
    # -------------------------------------------------------------
    def test_predict_pipeline_stationary_telemetry(self):
        """Verify predict() returns valid classifications and updated root-cause for stationary telemetry."""
        sample = {
            "machine_id": "MOTOR_01",
            "timestamp": "2026-10-27 23:00:00",
            "temperature_c": 27.4,
            "humidity_percent": 50.0,
            "vibration_g": 0.025,
            "rpm": 0,
            "load_percent": 0.0,
            "condition": "Healthy"
        }
        res = self.ai.predict(sample)
        self.assertEqual(res["predicted_condition"], "Healthy")
        self.assertFalse(res["is_heuristic"])
        self.assertEqual(res["root_cause_analysis"], "Machine stationary / at rest")
        self.assertIn("failure_risk_percent", res)
        self.assertIn("estimated_rul_hours", res)
        self.assertIn("prescriptive_action", res)


if __name__ == "__main__":
    unittest.main()
