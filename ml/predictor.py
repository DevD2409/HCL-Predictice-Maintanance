import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import joblib


ML_DIR = Path("ml")
MODELS_DIR = ML_DIR / "models"


class PredictiveMaintenanceAI:
    """
    Predictive Maintenance AI Engine for rotating machinery.
    Performs condition classification, failure risk calculation, RUL estimation,
    root-cause diagnostics, and prescriptive maintenance recommendations.
    """

    def __init__(self, models_dir=None):
        self.models_dir = Path(models_dir) if models_dir else MODELS_DIR
        self.classifier = None
        self.regressor = None
        self.scaler = None
        self.metrics = {}
        self.labels = {0: "Healthy", 1: "Warning", 2: "Fault"}
        self.load_models()

    def load_models(self):
        clf_path = self.models_dir / "condition_classifier.joblib"
        reg_path = self.models_dir / "rul_regressor.joblib"
        scaler_path = self.models_dir / "scaler.joblib"
        metrics_path = self.models_dir / "model_metrics.json"

        if clf_path.exists() and reg_path.exists() and scaler_path.exists():
            try:
                self.classifier = joblib.load(clf_path)
                self.regressor = joblib.load(reg_path)
                self.scaler = joblib.load(scaler_path)
                if metrics_path.exists():
                    with open(metrics_path, "r", encoding="utf-8") as f:
                        self.metrics = json.load(f)
                return True
            except Exception as e:
                print(f"Warning: Failed to load trained models ({e}). Using intelligent heuristic fallback.")
                return False
        return False

    def extract_features(self, temp, vib, rpm, load, humidity):
        """Construct feature dataframe matching training pipeline."""
        df = pd.DataFrame([{
            "temperature_c": float(temp),
            "vibration_g": float(vib),
            "rpm": float(rpm),
            "load_percent": float(load),
            "humidity_percent": float(humidity),
            "vibration_energy": float(vib) ** 2,
            "thermal_load_index": (float(temp) * float(load)) / 100.0,
            "speed_ratio": float(rpm) / 1500.0,
            "temp_vibe_interaction": float(temp) * float(vib)
        }])
        return df

    def diagnose_root_cause(self, temp, vib, rpm, load, condition):
        """Diagnose specific mechanical failure modes."""
        causes = []
        if vib >= 0.20:
            causes.append("High Vibration (Bearing cage failure, inner-race defect, or severe angular misalignment)")
        elif vib >= 0.08:
            causes.append("Elevated Vibration (Developing unbalance or rotor looseness)")

        if temp >= 60.0:
            causes.append("Excessive Temperature (Motor winding thermal overload or inadequate cooling)")
        elif temp >= 45.0:
            causes.append("Elevated Temperature (Moderate thermal dissipation stress)")

        if 0 < rpm < 1350:
            causes.append("Under-speed Phenomenon (Mechanical friction drag or voltage drop)")
        elif rpm <= 0:
            causes.append("Machine stationary / at rest")

        if load >= 75.0:
            causes.append("Heavy Dynamic Load (Operating above rated capacity)")

        if not causes:
            causes.append("Nominal Machine Operation (All telemetry within ISO standard limits)")

        return " | ".join(causes)

    def prescribe_action(self, condition, failure_risk):
        """Generate prescriptive maintenance recommendations."""
        if condition == "Fault" or failure_risk >= 70.0:
            return {
                "action": "CRITICAL SHUTDOWN & IMMEDIATE INSPECTION",
                "priority": "P1 - Critical",
                "timeframe": "Immediate (< 4 Hours)",
                "steps": [
                    "Isolate electrical supply to rotating motor.",
                    "Inspect bearing housings for overheating and physical play.",
                    "Verify shaft alignment and vibration spectral harmonics.",
                    "Replace damaged rolling element bearings before restart."
                ]
            }
        elif condition == "Warning" or failure_risk >= 30.0:
            return {
                "action": "PREVENTIVE MAINTENANCE & LUBRICATION INSPECTION",
                "priority": "P2 - Warning",
                "timeframe": "Within 24 to 48 Hours",
                "steps": [
                    "Schedule non-intrusive vibration analysis.",
                    "Inspect bearing grease levels and replenish lubricant.",
                    "Check dynamic belt tension and motor mounting bolts.",
                    "Monitor thermal trends closely."
                ]
            }
        else:
            return {
                "action": "ROUTINE MONITORING",
                "priority": "P3 - Normal",
                "timeframe": "Standard Schedule (Monthly)",
                "steps": [
                    "Continue continuous IoT telemetry ingestion.",
                    "Verify scheduled preventative maintenance log."
                ]
            }

    def predict(self, telemetry: dict):
        """
        Accepts dictionary containing:
          temperature_c, vibration_g, rpm, load_percent, humidity_percent
        Returns full predictive maintenance diagnostic report.
        """
        temp = float(telemetry.get("temperature_c", 40.0))
        vib = float(telemetry.get("vibration_g", 0.05))
        rpm = float(telemetry.get("rpm", 1450))
        load = float(telemetry.get("load_percent", 50.0))
        humidity = float(telemetry.get("humidity_percent", 50.0))

        if self.classifier is not None and self.regressor is not None and self.scaler is not None:
            # ML Pipeline Inference
            X = self.extract_features(temp, vib, rpm, load, humidity)
            X_scaled = self.scaler.transform(X)

            pred_class_idx = int(self.classifier.predict(X_scaled)[0])
            pred_condition = self.labels.get(pred_class_idx, "Healthy")

            # Probability distribution
            probs = self.classifier.predict_proba(X_scaled)[0]
            # probs order: [p_healthy, p_warning, p_fault]
            p_healthy = float(probs[0]) if len(probs) > 0 else 0.0
            p_warning = float(probs[1]) if len(probs) > 1 else 0.0
            p_fault = float(probs[2]) if len(probs) > 2 else 0.0

            # Expose the actual maximum predicted class probability
            confidence_percent = round(float(max(probs)) * 100.0, 1)
            is_heuristic = False

            # Failure risk index: weighted risk score 0 to 100%
            failure_risk = round((p_warning * 45.0 + p_fault * 100.0), 2)
            if pred_condition == "Fault":
                failure_risk = max(failure_risk, 85.0)

            # RUL Prediction
            rul_hours = round(float(self.regressor.predict(X_scaled)[0]), 1)
        else:
            # Intelligent Physics-based Fallback
            confidence_percent = None
            is_heuristic = True
            if vib >= 0.20 or temp >= 60.0:
                pred_condition = "Fault"
                failure_risk = round(min(100.0, 75.0 + (vib * 50)), 2)
                rul_hours = round(max(2.0, 24.0 - (vib * 30)), 1)
            elif vib >= 0.08 or temp >= 45.0 or rpm < 1400:
                pred_condition = "Warning"
                failure_risk = round(min(70.0, 35.0 + (vib * 150)), 2)
                rul_hours = round(max(30.0, 200.0 - (vib * 500)), 1)
            else:
                pred_condition = "Healthy"
                failure_risk = round(max(2.0, vib * 80), 2)
                rul_hours = round(max(600.0, 1000.0 - (vib * 1500)), 1)

        # Anomaly score (0 to 100)
        norm_vib = min(1.0, vib / 0.50)
        norm_temp = min(1.0, max(0.0, (temp - 30.0) / 50.0))
        anomaly_score = round((norm_vib * 60.0 + norm_temp * 40.0), 2)

        root_cause = self.diagnose_root_cause(temp, vib, rpm, load, pred_condition)
        prescriptive = self.prescribe_action(pred_condition, failure_risk)

        return {
            "machine_id": telemetry.get("machine_id", "MOTOR_01"),
            "timestamp": telemetry.get("timestamp", ""),
            "input_metrics": {
                "temperature_c": temp,
                "vibration_g": vib,
                "rpm": rpm,
                "load_percent": load,
                "humidity_percent": humidity
            },
            "predicted_condition": pred_condition,
            "confidence_percent": confidence_percent,
            "is_heuristic": is_heuristic,
            "failure_risk_percent": failure_risk,
            "estimated_rul_hours": rul_hours,
            "anomaly_score": anomaly_score,
            "root_cause_analysis": root_cause,
            "prescriptive_action": prescriptive,
            "model_version": "RandomForest-v1.0" if not is_heuristic else "Physics-Heuristic-v1.0"
        }
