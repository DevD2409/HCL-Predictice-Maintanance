import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path


DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "machine_data.db"


class AlertManager:
    """
    Manages persistent alerts for rotating machinery anomalies and fault conditions.
    Stores alerts in SQLite, avoids spamming consecutive duplicates, and supports acknowledgment.
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.last_alert_time = {}
        self.min_alert_interval = 15  # seconds cooldown between identical alerts
        self.init_db()

    def init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machine_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                machine_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                condition TEXT NOT NULL,
                failure_risk_percent REAL NOT NULL,
                temperature_c REAL,
                vibration_g REAL,
                rpm INTEGER,
                root_cause TEXT,
                prescriptive_action TEXT,
                status TEXT DEFAULT 'ACTIVE',
                acknowledged_by TEXT,
                acknowledged_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def create_alert(self, prediction: dict, force=False):
        """
        Creates an alert if condition is Warning or Fault, or failure risk >= 40%.
        Returns alert dict if created, None if suppressed by cooldown.
        """
        cond = prediction.get("predicted_condition", "Healthy")
        risk = prediction.get("failure_risk_percent", 0.0)
        machine_id = prediction.get("machine_id", "MOTOR_01")

        if cond == "Healthy" and risk < 40.0 and not force:
            return None

        severity = "CRITICAL" if cond == "Fault" or risk >= 75.0 else "WARNING"
        now = time.time()
        last_time = self.last_alert_time.get(f"{machine_id}_{severity}", 0)

        if not force and (now - last_time < self.min_alert_interval):
            return None  # Cooldown active

        self.last_alert_time[f"{machine_id}_{severity}"] = now

        ts = prediction.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metrics = prediction.get("input_metrics", {})
        action_dict = prediction.get("prescriptive_action", {})
        action_text = f"{action_dict.get('action', '')} ({action_dict.get('timeframe', '')})"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO machine_alerts (
                timestamp, machine_id, severity, condition, failure_risk_percent,
                temperature_c, vibration_g, rpm, root_cause, prescriptive_action, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
        """, (
            ts,
            machine_id,
            severity,
            cond,
            risk,
            metrics.get("temperature_c"),
            metrics.get("vibration_g"),
            metrics.get("rpm"),
            prediction.get("root_cause_analysis", ""),
            action_text
        ))
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "id": alert_id,
            "timestamp": ts,
            "machine_id": machine_id,
            "severity": severity,
            "condition": cond,
            "failure_risk_percent": risk,
            "root_cause": prediction.get("root_cause_analysis", ""),
            "prescriptive_action": action_text,
            "status": "ACTIVE"
        }

    def get_recent_alerts(self, limit=20, status=None):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if status:
            cursor.execute("""
                SELECT * FROM machine_alerts
                WHERE status = ?
                ORDER BY id DESC LIMIT ?
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT * FROM machine_alerts
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_active_count(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM machine_alerts WHERE status = 'ACTIVE'")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def acknowledge_alert(self, alert_id, user="Operator"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE machine_alerts
            SET status = 'ACKNOWLEDGED', acknowledged_by = ?, acknowledged_at = ?
            WHERE id = ?
        """, (user, now, alert_id))
        conn.commit()
        conn.close()
        return True

    def resolve_alert(self, alert_id, user="Engineer"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE machine_alerts
            SET status = 'RESOLVED', acknowledged_by = ?, acknowledged_at = ?
            WHERE id = ?
        """, (user, now, alert_id))
        conn.commit()
        conn.close()
        return True
