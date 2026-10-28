import unittest
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from layer5_ai_dashboard import fetch_recent_data, ai, alert_mgr, cond_color

class TestDashboardRefreshLogic(unittest.TestCase):

    def test_fetch_recent_data_returns_advancing_telemetry(self):
        """Verify fetch_recent_data pulls latest records from SQLite."""
        df1 = fetch_recent_data(limit=10)
        self.assertFalse(df1.empty, "Database machine_readings should not be empty")
        latest1_id = df1.iloc[0]["id"]
        latest1_ts = df1.iloc[0]["timestamp"]

        # Check required columns
        for col in ["id", "timestamp", "machine_id", "temperature_c", "vibration_g", "rpm", "load_percent", "condition"]:
            self.assertIn(col, df1.columns)

        print(f"Sample 1: ID={latest1_id}, Time={latest1_ts}, RPM={df1.iloc[0]['rpm']}, Temp={df1.iloc[0]['temperature_c']} C")

    def test_refresh_interval_policy(self):
        """Verify refresh interval is 3s for Overview & Trends, and None for interactive pages."""
        def compute_refresh_interval(auto_refresh, page):
            return 3 if (auto_refresh and page in ["Overview", "Trends"]) else None

        # Live monitoring pages with auto-refresh enabled
        self.assertEqual(compute_refresh_interval(True, "Overview"), 3)
        self.assertEqual(compute_refresh_interval(True, "Trends"), 3)

        # Interactive / static pages must NOT auto-refresh
        self.assertIsNone(compute_refresh_interval(True, "What-If"))
        self.assertIsNone(compute_refresh_interval(True, "Alerts"))
        self.assertIsNone(compute_refresh_interval(True, "AI Model"))
        self.assertIsNone(compute_refresh_interval(True, "Layers"))

        # When auto_refresh is toggled off, no page should auto-refresh
        self.assertIsNone(compute_refresh_interval(False, "Overview"))
        self.assertIsNone(compute_refresh_interval(False, "Trends"))

    def test_prediction_on_fresh_telemetry(self):
        """Verify ai.predict works cleanly on fresh SQLite rows."""
        df = fetch_recent_data(limit=5)
        self.assertFalse(df.empty)
        latest = df.iloc[0].to_dict()
        pred = ai.predict(latest)

        self.assertIn("predicted_condition", pred)
        self.assertIn("failure_risk_percent", pred)
        self.assertIn("estimated_rul_hours", pred)
        self.assertIn("root_cause_analysis", pred)
        self.assertIn("anomaly_score", pred)
        self.assertIn("prescriptive_action", pred)

        cc = cond_color(pred["predicted_condition"])
        self.assertTrue(cc.startswith("#"))
        print(f"Prediction OK: Condition={pred['predicted_condition']}, Risk={pred['failure_risk_percent']}%, RUL={pred['estimated_rul_hours']}h")

if __name__ == "__main__":
    unittest.main()

