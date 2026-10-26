"""
HCL Predictive Maintenance - Consolidated Software & Hardware Readiness Audit
Audits:
  1. Python Virtual Environment and package versions.
  2. Configuration (.env) and HiveMQ Cloud connectivity parameters.
  3. SQLite database integrity, schema verification, and historical records.
  4. Serialized ML model artifacts and real-time inference latency.
  5. Layer 6 hardware compatibility test suite.
"""

import os
import sys
import json
import sqlite3
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import dotenv_values
from ml.predictor import PredictiveMaintenanceAI


def run_audit():
    print("=" * 68)
    print(" HCL PREDICTIVE MAINTENANCE - CONSOLIDATED READINESS AUDIT")
    print("=" * 68)

    results = {}

    # Check 1: Virtualenv and Python runtime
    print("\n[Check 1/5] Python Runtime & Dependencies")
    print(f"  Python executable: {sys.executable}")
    print(f"  Python version:    {sys.version.split()[0]}")
    required_packages = ["numpy", "pandas", "paho.mqtt", "dotenv", "streamlit", "sklearn", "joblib"]
    pkg_status = {}
    for pkg in required_packages:
        try:
            __import__(pkg)
            pkg_status[pkg] = "INSTALLED"
        except ImportError:
            pkg_status[pkg] = "MISSING"
    all_pkgs = all(v == "INSTALLED" for v in pkg_status.values())
    results["dependencies"] = all_pkgs
    print(f"  Required packages status: {'PASS' if all_pkgs else 'FAIL'}")

    # Check 2: Configuration & MQTT Environment
    print("\n[Check 2/5] Configuration & MQTT Secrets Presence")
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        vals = dotenv_values(env_path)
        keys_present = [k for k in ["HIVEMQ_HOST", "HIVEMQ_PORT", "HIVEMQ_USERNAME", "HIVEMQ_PASSWORD", "MQTT_TOPIC"] if vals.get(k)]
        print(f"  Found .env file at {env_path.name}")
        print(f"  Configured keys count: {len(keys_present)} / 5")
        results["configuration"] = len(keys_present) == 5
    else:
        print("  WARNING: .env file missing!")
        results["configuration"] = False

    # Check 3: SQLite Database & Schema
    print("\n[Check 3/5] SQLite Database Storage Layer")
    db_path = BASE_DIR / "data" / "machine_data.db"
    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024.0
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        readings_cnt = cur.execute("SELECT COUNT(*) FROM machine_readings").fetchone()[0]
        alerts_cnt = cur.execute("SELECT COUNT(*) FROM machine_alerts").fetchone()[0]
        users_cnt = cur.execute("SELECT COUNT(*) FROM system_users").fetchone()[0]
        conn.close()
        print(f"  Database file size:          {size_kb:.1f} KB")
        print(f"  Historical machine readings: {readings_cnt}")
        print(f"  Alert records:               {alerts_cnt}")
        print(f"  System users:                {users_cnt}")
        results["database"] = readings_cnt > 0
    else:
        print("  WARNING: database file missing!")
        results["database"] = False

    # Check 4: Serialized ML Models & Inference
    print("\n[Check 4/5] ML Engine & Predictor Inference")
    models_dir = BASE_DIR / "ml" / "models"
    try:
        t0 = time.perf_counter()
        ai = PredictiveMaintenanceAI(models_dir)
        test_pred = ai.predict({
            "temperature_c": 38.0,
            "vibration_g": 0.045,
            "rpm": 1450,
            "load_percent": 55.0,
            "humidity_percent": 50.0
        })
        latency_ms = (time.perf_counter() - t0) * 1000.0
        print(f"  Loaded model version:     {test_pred.get('model_version')}")
        print(f"  Inference latency:        {latency_ms:.2f} ms")
        print(f"  Sample prediction output: {test_pred.get('predicted_condition')} (Risk: {test_pred.get('failure_risk_percent')}%)")
        results["ml_models"] = test_pred.get("predicted_condition") == "Healthy"
    except Exception as e:
        print(f"  ERROR evaluating ML models: {e}")
        results["ml_models"] = False

    # Check 5: Hardware Compatibility Test Suite
    print("\n[Check 5/5] Layer 6 Hardware Compatibility Unit Tests")
    import unittest
    from scratch.test_hardware_compatibility import TestHardwareCompatibility
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHardwareCompatibility)
    runner = unittest.TextTestRunner(verbosity=0)
    test_run = runner.run(suite)
    print(f"  Tests run: {test_run.testsRun}, Errors: {len(test_run.errors)}, Failures: {len(test_run.failures)}")
    results["hardware_tests"] = test_run.wasSuccessful()

    print("\n" + "=" * 68)
    print(" CONSOLIDATED AUDIT SUMMARY")
    print("=" * 68)
    for k, v in results.items():
        status = "PASS" if v else "FAIL"
        print(f"  - {k:<25}: {status}")

    all_passed = all(results.values())
    overall = "ALL CHECKS PASSED (Ready for Hardware Integration)" if all_passed else "ATTENTION REQUIRED"
    print(f"\nOVERALL AUDIT RESULT: {overall}")
    print("=" * 68)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_audit())