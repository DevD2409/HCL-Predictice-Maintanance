import json
import os
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "machine_data.db"
ML_DIR = Path("ml")
MODELS_DIR = ML_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def extract_features(df):
    """Generate engineering features for rotating machinery predictive maintenance."""
    features = pd.DataFrame()
    features["temperature_c"] = df["temperature_c"]
    features["vibration_g"] = df["vibration_g"]
    features["rpm"] = df["rpm"]
    features["load_percent"] = df["load_percent"]
    features["humidity_percent"] = df["humidity_percent"]

    # Advanced engineered features
    features["vibration_energy"] = df["vibration_g"] ** 2
    features["thermal_load_index"] = (df["temperature_c"] * df["load_percent"]) / 100.0
    features["speed_ratio"] = df["rpm"] / 1500.0
    features["temp_vibe_interaction"] = df["temperature_c"] * df["vibration_g"]
    return features


def load_dataset():
    """Load machine telemetry from SQLite or fallback to CSV."""
    if DB_PATH.exists():
        print(f"Loading data from SQLite: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM machine_readings", conn)
        conn.close()
    elif (DATA_DIR / "machine_data.csv").exists():
        print(f"Loading data from CSV: {DATA_DIR / 'machine_data.csv'}")
        df = pd.read_csv(DATA_DIR / "machine_data.csv")
    else:
        raise FileNotFoundError("Neither SQLite DB nor CSV found in data/ directory.")

    df = df.dropna(subset=["temperature_c", "vibration_g", "rpm", "load_percent", "condition"])
    print(f"Loaded {len(df)} records. Conditions distribution:\n{df['condition'].value_counts()}\n")
    return df


def generate_rul_target(df):
    """
    Synthesize Remaining Useful Life (RUL in hours) based on physical degradation.
    - Healthy: 720 to 1200 hours
    - Warning: 72 to 240 hours
    - Fault: 1 to 24 hours
    """
    rul = []
    np.random.seed(42)
    for _, row in df.iterrows():
        cond = row["condition"]
        vib = row["vibration_g"]
        temp = row["temperature_c"]

        if cond == "Healthy":
            base = 1000 - (vib * 1000) - (temp * 2)
            rul.append(max(600, min(1200, base + np.random.uniform(-50, 50))))
        elif cond == "Warning":
            base = 200 - ((vib - 0.08) * 600) - ((temp - 45) * 3)
            rul.append(max(40, min(260, base + np.random.uniform(-20, 20))))
        else:  # Fault
            base = 20 - ((vib - 0.20) * 30) - ((temp - 60) * 0.5)
            rul.append(max(1.0, min(30.0, base + np.random.uniform(-3, 3))))
    return np.array(rul)


def train():
    print("=" * 60)
    print(" HCL Predictive Maintenance — AI/ML Model Training")
    print("=" * 60)

    df = load_dataset()
    X = extract_features(df)
    feature_names = list(X.columns)

    # Classification Target
    label_mapping = {"Healthy": 0, "Warning": 1, "Fault": 2}
    inv_label_mapping = {0: "Healthy", 1: "Warning", 2: "Fault"}
    y_class = df["condition"].map(label_mapping)

    # RUL Regression Target
    y_rul = generate_rul_target(df)

    # Split dataset
    X_train, X_test, y_train_c, y_test_c, y_train_r, y_test_r = train_test_split(
        X, y_class, y_rul, test_size=0.2, random_state=42, stratify=y_class
    )

    # Fit scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 1. Condition Classifier (Random Forest)
    print("\n[1/2] Training Condition Classifier (Random Forest)...")
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    clf.fit(X_train_scaled, y_train_c)

    y_pred_c = clf.predict(X_test_scaled)
    acc = accuracy_score(y_test_c, y_pred_c)
    print(f"Classifier Test Accuracy: {acc * 100:.2f}%\n")
    print("Classification Report:")
    print(classification_report(y_test_c, y_pred_c, target_names=["Healthy", "Warning", "Fault"]))

    # 2. RUL Regressor (Random Forest)
    print("[2/2] Training Remaining Useful Life (RUL) Regressor...")
    reg = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        random_state=42,
        n_jobs=-1
    )
    reg.fit(X_train_scaled, y_train_r)

    y_pred_r = reg.predict(X_test_scaled)
    r2 = r2_score(y_test_r, y_pred_r)
    print(f"RUL Regressor R² Score: {r2:.4f}")

    # Feature Importances
    importances = clf.feature_importances_
    feat_imp = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
    print("\nFeature Importances:")
    for feat, imp in feat_imp:
        print(f"  - {feat:22}: {imp * 100:.2f}%")

    # Save models
    clf_path = MODELS_DIR / "condition_classifier.joblib"
    reg_path = MODELS_DIR / "rul_regressor.joblib"
    scaler_path = MODELS_DIR / "scaler.joblib"
    metrics_path = MODELS_DIR / "model_metrics.json"

    joblib.dump(clf, clf_path)
    joblib.dump(reg, reg_path)
    joblib.dump(scaler, scaler_path)

    metrics = {
        "accuracy": round(float(acc), 4),
        "r2_score": round(float(r2), 4),
        "feature_names": feature_names,
        "feature_importances": {feat: round(float(imp), 4) for feat, imp in feat_imp},
        "labels": label_mapping,
        "training_samples": len(X_train),
        "test_samples": len(X_test)
    }

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nArtifacts successfully saved to {MODELS_DIR}:")
    print(f"  - {clf_path}")
    print(f"  - {reg_path}")
    print(f"  - {scaler_path}")
    print(f"  - {metrics_path}")
    print("\nModel Training Complete [SUCCESS]")


if __name__ == "__main__":
    train()
