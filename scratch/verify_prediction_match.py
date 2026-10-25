import json
import sqlite3
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "machine_data.db"
API_URL = "http://localhost:8000/latest-prediction"

# Fetch the live prediction
with urllib.request.urlopen(API_URL, timeout=10) as response:
    prediction = json.loads(response.read().decode("utf-8"))

metrics = prediction["input_metrics"]
timestamp = prediction["timestamp"]
machine_id = prediction["machine_id"]

print("API STATUS: SUCCESS")
print("Timestamp:", timestamp)
print("Machine:", machine_id)
print("Condition:", prediction["predicted_condition"])
print("Confidence:", prediction["confidence_percent"])

# Read the matching SQLite record
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

row = conn.execute(
    """
    SELECT *
    FROM machine_readings
    WHERE timestamp = ? AND machine_id = ?
    ORDER BY id DESC
    LIMIT 1
    """,
    (timestamp, machine_id),
).fetchone()

if row is None:
    print("\nNo exact timestamp match found.")
    print("API timestamp:", timestamp)
else:
    row = dict(row)

    checks = {
        "Temperature": abs(
            float(metrics["temperature_c"]) - row["temperature_c"]
        ) < 0.01,
        "Vibration": abs(
            float(metrics["vibration_g"]) - row["vibration_g"]
        ) < 0.001,
        "RPM": int(metrics["rpm"]) == row["rpm"],
        "Load": abs(
            float(metrics["load_percent"]) - row["load_percent"]
        ) < 0.01,
    }

    print("\n=== Exact Value Match ===")
    for name, result in checks.items():
        print(f"{name} match: {result}")

    print(
        "\nOVERALL:",
        "PASS" if all(checks.values()) else "MISMATCH"
    )

conn.close()