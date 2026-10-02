import hashlib
import os
import sqlite3
from pathlib import Path


DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "machine_data.db"


class AuthManager:
    """
    Role-Based Authentication and User Management System.
    Supports Admin, Engineer, and Operator roles with salted password hashing.
    """

    DEFAULT_USERS = [
        ("admin", "admin123", "admin", "System Administrator"),
        ("engineer", "engineer123", "engineer", "Reliability Engineer"),
        ("operator", "operator123", "operator", "Plant Floor Operator")
    ]

    ROLE_PERMISSIONS = {
        "admin": {
            "view_telemetry": True,
            "view_predictions": True,
            "view_alerts": True,
            "acknowledge_alerts": True,
            "resolve_alerts": True,
            "manage_users": True,
            "retrain_model": True,
            "hardware_control": True
        },
        "engineer": {
            "view_telemetry": True,
            "view_predictions": True,
            "view_alerts": True,
            "acknowledge_alerts": True,
            "resolve_alerts": True,
            "manage_users": False,
            "retrain_model": True,
            "hardware_control": True
        },
        "operator": {
            "view_telemetry": True,
            "view_predictions": True,
            "view_alerts": True,
            "acknowledge_alerts": True,
            "resolve_alerts": False,
            "manage_users": False,
            "retrain_model": False,
            "hardware_control": False
        }
    }

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.init_db()

    def _hash_password(self, password, salt):
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

    def init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Seed default accounts if empty
        cursor.execute("SELECT COUNT(*) FROM system_users")
        count = cursor.fetchone()[0]
        if count == 0:
            for username, password, role, full_name in self.DEFAULT_USERS:
                salt = os.urandom(16).hex()
                pw_hash = self._hash_password(password, salt)
                cursor.execute("""
                    INSERT INTO system_users (username, password_hash, salt, role, full_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (username, pw_hash, salt, role, full_name))
            conn.commit()

        conn.close()

    def authenticate(self, username, password):
        """Verify user credentials and return user info dictionary or None."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT username, password_hash, salt, role, full_name
            FROM system_users WHERE username = ?
        """, (username.strip().lower(),))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return False, "User not found"

        uname, stored_hash, salt, role, full_name = row
        candidate_hash = self._hash_password(password, salt)

        if candidate_hash == stored_hash:
            return True, {
                "username": uname,
                "role": role,
                "full_name": full_name,
                "permissions": self.ROLE_PERMISSIONS.get(role, self.ROLE_PERMISSIONS["operator"])
            }
        return False, "Invalid password"

    def list_users(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, full_name, created_at FROM system_users")
        users = [
            {"id": r[0], "username": r[1], "role": r[2], "full_name": r[3], "created_at": r[4]}
            for r in cursor.fetchall()
        ]
        conn.close()
        return users
