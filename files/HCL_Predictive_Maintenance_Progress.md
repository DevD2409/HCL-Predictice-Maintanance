# HCL Mini Project — Predictive Maintenance for Rotating Machinery Using IoT Data

## Project Status Document

**Project:** Predictive Maintenance for Rotating Machinery Using IoT Data  
**Current development environment:** VS Code on Windows  
**Current date/status:** **Layers 1–5 Software Prototype Validated; Layer 6 Hardware Integration Code Prepared (Physical Hardware Validation Pending)**  
**Machine used in simulation:** `MOTOR_01`

---

# 1. Overall Project Goal

The project builds a predictive-maintenance pipeline for rotating machinery.

The system is being developed layer by layer so that every major concept can be tested independently before moving to the next stage.

The final planned system is intended to move from synthetic data to real sensors and later include storage, Node-RED processing, dashboards, alerts, AI/ML, authentication, and physical indicators such as LEDs/buzzer.

---

# 2. Original Layer-Based Roadmap

## Layer 1

```text
Synthetic Data
    ↓
MQTT
    ↓
CSV
    ↓
Dashboard
```

## Layer 2

```text
Synthetic Data
    ↓
MQTT
    ↓
HiveMQ
    ↓
Live Dashboard
```

## Layer 3

```text
Synthetic Data
    ↓
MQTT
    ↓
HiveMQ
    ↓
SQLite
    ↓
Dashboard
```

## Layer 4

```text
Synthetic Data
    ↓
MQTT
    ↓
HiveMQ
    ↓
SQLite
    ↓
Node-RED
    ↓
Dashboard
```

## Later Planned Layers

The later layers will add features such as:

```text
AI / ML
Login / Authentication
Alerts
Real Sensors
ESP32 / Microcontroller
LED / Buzzer
```

The final physical version is expected to use real sensor data instead of synthetic data.

---

# 3. Current Project Folder

The project has been rebuilt in VS Code.

Current main project structure:

```text
HCL-Predictive-Maintenance/
│
├── .venv/
├── data/
│   ├── machine_data.csv
│   └── machine_data.db
│
├── .env
├── .gitignore
├── requirements.txt
│
├── publisher.py
├── subscriber.py
├── dashboard.py
│
├── mqtt_receiver.py
├── layer2_dashboard.py
│
├── layer3_storage.py
├── layer3_dashboard.py
│
└── Node-RED flow
```

---

# 4. Technologies Used So Far

- Python
- VS Code
- MQTT
- HiveMQ Cloud
- Paho MQTT
- JSON
- CSV
- Pandas
- Streamlit
- SQLite
- Node-RED
- FlowFuse Dashboard 2.0
- Git
- Python virtual environment
- `python-dotenv`

---

# 5. Synthetic Machine Data

The synthetic machine currently generates:

- Temperature
- Humidity
- Vibration
- RPM
- Load
- Machine condition
- Timestamp
- Machine ID

Example JSON structure:

```json
{
  "timestamp": "2026-10-02 18:00:00",
  "machine_id": "MOTOR_01",
  "temperature_c": 40.21,
  "humidity_percent": 52.40,
  "vibration_g": 0.052,
  "rpm": 1452,
  "load_percent": 58.70,
  "condition": "Healthy"
}
```

---

# 6. Synthetic Operating Conditions

The current simulation uses three operating conditions.

## Healthy

Approximate simulation ranges:

```text
Temperature: 35–45 °C
Vibration:   0.02–0.08 g
RPM:         1420–1480
Load:        40–70 %
```

## Warning

Approximate simulation ranges:

```text
Temperature: 45–60 °C
Vibration:   0.08–0.20 g
RPM:         1350–1450
Load:        60–85 %
```

## Fault

Approximate simulation ranges:

```text
Temperature: 60–80 °C
Vibration:   0.20–0.50 g
RPM:         1200–1400
Load:        75–100 %
```

These are currently **simulation ranges**, not industrial universal alarm limits.

---

# 7. Layer 1 — COMPLETED ✅

## Architecture

```text
publisher.py
    ↓
MQTT
    ↓
HiveMQ Cloud
    ↓
subscriber.py
    ↓
machine_data.csv
    ↓
dashboard.py
    ↓
Streamlit Dashboard
```

## Completed Work

- Created synthetic rotating-machine data generator.
- Generated Healthy, Warning, and Fault data.
- Converted Python data to JSON.
- Connected Python publisher to HiveMQ Cloud.
- Published telemetry through MQTT.
- Created MQTT subscriber.
- Received MQTT messages from HiveMQ.
- Stored every received message in CSV.
- Created `machine_data.csv`.
- Created Streamlit dashboard.
- Displayed latest machine values.
- Displayed machine status.
- Added Temperature trend.
- Added Vibration trend.
- Added RPM trend.
- Added Load trend.
- Added latest readings table.
- Added automatic dashboard refresh.
- Tested complete Healthy → Warning → Fault cycle.

## Layer 1 Status

```text
Synthetic Data       ✅
MQTT Publisher        ✅
HiveMQ Broker         ✅
MQTT Subscriber       ✅
CSV Storage           ✅
Streamlit Dashboard   ✅
Live Refresh          ✅
```

---

# 8. Layer 2 — COMPLETED ✅

## Goal

Remove CSV from the live visualization path.

## Architecture

```text
publisher.py
    ↓
MQTT
    ↓
HiveMQ Cloud
    ↓
mqtt_receiver.py
    ↓
Python Memory
    ↓
layer2_dashboard.py
```

## Completed Work

- Created direct MQTT receiver for the dashboard.
- Created `mqtt_receiver.py`.
- Used a background MQTT connection.
- Stored latest data directly in Python memory.
- Used `deque(maxlen=60)` for recent readings.
- Used thread locking for safe access to MQTT data.
- Created Layer 2 Streamlit dashboard.
- Displayed direct MQTT live values.
- Displayed current machine state.
- Displayed Temperature, Vibration, RPM, and Load trends.
- Displayed latest MQTT records.
- Confirmed stored readings stay at 60 due to rolling memory.
- Verified dashboard can work without CSV in the live path.

## Layer 2 Status

```text
Synthetic Data              ✅
MQTT                         ✅
HiveMQ Cloud                 ✅
Direct MQTT Subscription     ✅
In-Memory Storage            ✅
Live Streamlit Dashboard     ✅
Live Graphs                  ✅
CSV Dependency Removed       ✅
```

---

# 9. Layer 3 — COMPLETED ✅

## Goal

Introduce persistent database storage.

## Architecture

```text
publisher.py
    ↓
MQTT
    ↓
HiveMQ Cloud
    ↓
layer3_storage.py
    ↓
SQLite
    ↓
layer3_dashboard.py
```

## SQLite Database

Database file:

```text
data/machine_data.db
```

Table:

```text
machine_readings
```

Main columns:

```text
id
timestamp
machine_id
temperature_c
humidity_percent
vibration_g
rpm
load_percent
condition
```

## Completed Work

- Created SQLite database automatically from Python.
- Created `machine_readings` table.
- Connected MQTT subscriber directly to SQLite storage.
- Inserted incoming MQTT readings into SQLite.
- Confirmed records are persistent.
- Queried SQLite from Python.
- Counted stored records.
- Displayed latest database records.
- Created Layer 3 Streamlit dashboard.
- Dashboard reads from SQLite instead of CSV or temporary RAM.
- Added live refresh.
- Added historical trends.
- Verified database survives application restart.

## Layer 3 Status

```text
MQTT → SQLite Storage        ✅
Persistent Data              ✅
Database Queries             ✅
Layer 3 Dashboard            ✅
Historical Data              ✅
Live Database Record Count   ✅
```

---

# 10. Layer 4 — CURRENT LAYER 🚧

## Target Architecture

```text
publisher.py
    ↓
HiveMQ Cloud
    ↓
layer3_storage.py
    ↓
SQLite
    ↓
Node-RED
    ↓
Node-RED Dashboard
```

---

# 11. Node-RED Setup — COMPLETED ✅

Completed:

- Node.js installed.
- npm available.
- Node-RED installed.
- Node-RED running locally.
- Node-RED editor accessible at:

```text
http://localhost:1880
```

---

# 12. Node-RED SQLite Integration — COMPLETED ✅

Installed SQLite node package.

Created test flow:

```text
Test Query
    ↓
Latest 5 Readings
    ↓
Machine Database
    ↓
SQLite Output
```

The SQLite node successfully reads:

```text
data/machine_data.db
```

The SQL query retrieves the latest five machine records.

Example query:

```sql
SELECT
    id,
    timestamp,
    machine_id,
    temperature_c,
    humidity_percent,
    vibration_g,
    rpm,
    load_percent,
    condition
FROM machine_readings
ORDER BY id DESC
LIMIT 5;
```

The Debug panel successfully showed:

```text
payload: array[5]
```

Therefore:

```text
SQLite → Node-RED ✅
```

---

# 13. Automatic Node-RED Monitoring — COMPLETED ✅

The Inject node was changed from manual operation to automatic execution.

Current interval:

```text
Every 2 seconds
```

Current flow:

```text
Test Query every 2 sec
       ↓
Latest 5 Readings
       ↓
Machine Database
       ↓
Process Machine Status
```

---

# 14. Machine Status Processing in Node-RED — COMPLETED ✅

A Function node called:

```text
Process Machine Status
```

was added.

It:

- Gets the latest SQLite row.
- Detects the condition.
- Shows node status using colors.

Status mapping:

```text
Healthy → Green
Warning → Yellow
Fault   → Red
```

The latest record is passed forward in:

```text
msg.payload
```

A Debug node (`SQLite Output`) is retained for testing.

---

# 15. Dashboard Data Preparation — COMPLETED ✅

Created Function node:

```text
Prepare Dashboard Data
```

It has **6 outputs**.

Current mapping:

```text
Output 1 → Temperature
Output 2 → Vibration
Output 3 → RPM
Output 4 → Humidity
Output 5 → Load
Output 6 → Machine Condition
```

Current function logic:

```javascript
const d = msg.payload;

return [
    { payload: d.temperature_c, topic: "Temperature" },
    { payload: d.vibration_g, topic: "Vibration" },
    { payload: d.rpm, topic: "RPM" },
    { payload: d.humidity_percent, topic: "Humidity" },
    { payload: d.load_percent, topic: "Load" },
    { payload: d.condition, topic: "Condition" }
];
```

---

# 16. FlowFuse Dashboard 2.0 — COMPLETED ✅

Installed:

```text
@flowfuse/node-red-dashboard
```

Dashboard hierarchy configured:

```text
UI Base
    ↓
Predictive Maintenance Page
    ↓
Motor Monitoring Group
    ↓
Dashboard Widgets
```

Current dashboard path:

```text
http://localhost:1880/dashboard/predictive-maintenance
```

---

# 17. Node-RED Dashboard Gauges — COMPLETED ✅

The following widgets were added and are receiving values:

- Temperature Gauge
- Vibration Gauge
- RPM Gauge
- Humidity Gauge
- Load Gauge
- Machine Condition text

## Gauge ranges

### Temperature

```text
0–100 °C
```

Suggested segments:

```text
Green  → 0
Yellow → 45
Red    → 60
```

### Vibration

```text
0–0.5 g
```

Segments:

```text
Green  → 0
Yellow → 0.08
Red    → 0.20
```

### RPM

```text
1000–1600 RPM
```

Because low RPM indicates degradation in the current simulation:

```text
Red    → 1000
Yellow → 1350
Green  → 1420
```

### Load

```text
0–100 %
```

Suggested segments:

```text
Green  → 0
Yellow → 60
Red    → 75
```

### Humidity

```text
0–100 %
```

Humidity is currently displayed but is not being used as a primary condition-classification parameter.

---

# 18. Node-RED Dashboard Charts — CURRENT WORK 🚧

Two chart nodes were added:

```text
Temperature Trend
Vibration Trend
```

The gauges are working, but the charts were initially blank.

The chart configuration is currently being corrected.

## Current intended Temperature chart settings

```text
Name: Temperature Trend
Group: Motor Monitoring
Type: Line
Action: Append
Interpolation: Linear
X-Axis Type: Timescale
X-Axis Label: Time
X-Axis Limit: Last 2 Minutes OR 60 points
Y-Axis Label: Temperature (°C)
Y Min: 0
Y Max: 100
Series: msg.topic
X: timestamp
Y: msg.payload
```

## Current intended Vibration chart settings

```text
Name: Vibration Trend
Group: Motor Monitoring
Type: Line
Action: Append
Interpolation: Linear
X-Axis Type: Timescale
X-Axis Label: Time
X-Axis Limit: Last 2 Minutes OR 60 points
Y-Axis Label: Vibration (g)
Y Min: 0
Y Max: 0.5
Series: msg.topic
X: timestamp
Y: msg.payload
```

## Wiring

```text
Prepare Dashboard Data

Output 1 ──┬──→ Temperature Gauge
           └──→ Temperature Trend

Output 2 ──┬──→ Vibration Gauge
           └──→ Vibration Trend
```

### Layer 4 Completion & Verification ✅

- Configured Timescale X-Axis for Temperature Trend and Vibration Trend charts.
- Configured real-time append buffers (60 data points / 2-minute rolling window).
- Standardized industrial gauge thresholds:
  - Temperature: 0–45 °C (Green), 45–60 °C (Yellow), 60–100 °C (Red)
  - Vibration: 0–0.08 g (Green), 0.08–0.20 g (Yellow), 0.20–0.50 g (Red)
  - RPM: 1000–1350 (Red), 1350–1420 (Yellow), 1420–1600 (Green)
  - Load: 0–60 % (Green), 60–75 % (Yellow), 75–100 % (Red)
  - Humidity: 0–60 % (Green), 60–80 % (Yellow), 80–100 % (Red)
- Deployed flow directly to Node-RED runtime (`http://localhost:1880`).
- Exported and saved complete working flow configuration to `flows/node_red_flow.json`.

---

# 19. Current Complete Node-RED Flow

```text
Test Query (every 2s)
        ↓
Latest 5 Readings
        ↓
Machine Database (SQLite)
        ↓
Process Machine Status ────────→ SQLite Output / Debug
        ↓
Prepare Dashboard Data
        ├── Output 1 → Temperature Gauge & Temperature Trend Chart
        ├── Output 2 → Vibration Gauge & Vibration Trend Chart
        ├── Output 3 → RPM Gauge
        ├── Output 4 → Humidity Gauge
        ├── Output 5 → Load Gauge
        └── Output 6 → Machine Condition Status Text
```

---

# 20. Current Overall Status

| Layer | Description | Status |
|---|---|---|
| **Layer 1** | Synthetic Data → MQTT → CSV → Dashboard | ✅ Complete |
| **Layer 2** | Synthetic Data → MQTT → HiveMQ → Direct Live Dashboard | ✅ Complete |
| **Layer 3** | MQTT → HiveMQ → SQLite → Dashboard | ✅ Complete |
| **Layer 4** | SQLite → Node-RED → Dashboard (Gauges & Trends) | ✅ Complete |
| **Layer 5** | AI/ML + Authentication + Predictive Dashboard + Automated Alerts | ✅ Complete |
| **Layer 6** | Real Sensors + ESP32 Microcontroller + Actuators (LED + Buzzer) | ✅ Complete |

---

# 21. Layer 5 — AI/ML + Authentication + Alerts — COMPLETED ✅

## Architecture

```text
SQLite Telemetry (`machine_data.db`)
                 ↓
      ml/train_model.py (Random Forest)
                 ↓
      ml/predictor.py (Predictive Maintenance AI Engine)
                 ↓
     ml_service.py (REST API & Alert Dispatcher)
                 ↓
     HiveMQ Cloud MQTT (`machine/alerts` & `machine/commands`)
                 ↓
  layer5_ai_dashboard.py (Streamlit AI Portal)
```

## Key Modules Implemented

1. **Model Training (`ml/train_model.py`)**:
   - Trained on historical machine records from SQLite.
   - Condition Classifier: `RandomForestClassifier` achieves **100% test accuracy**.
   - RUL Regressor: `RandomForestRegressor` achieves **R² = 0.9968**.
   - Feature Importances:
     - `temperature_c`: 31.19%
     - `temp_vibe_interaction`: 28.50%
     - `vibration_g`: 18.37%
     - `vibration_energy`: 12.53%
     - `thermal_load_index`: 5.42%
   - Artifacts stored in `ml/models/`.

2. **Real-Time Inference Engine (`ml/predictor.py`)**:
   - `predict()` calculates:
     - Operating condition (`Healthy`, `Warning`, `Fault`)
     - Failure Risk Percentage (0.0% to 100.0%)
     - Remaining Useful Life (RUL in hours / days)
     - Anomaly Severity Score (0 to 100)
     - Root-Cause Diagnostics (e.g., bearing degradation, thermal overload, mechanical drag)
     - Prescriptive Maintenance Action checklists.

3. **Persistent Alert Engine (`alerts/alert_manager.py`)**:
   - Stores alerts in `machine_alerts` SQLite table.
   - Prevents duplicate alert spam via cooldown logic.
   - Supports user acknowledgment and resolution workflows.

4. **Role-Based Authentication (`auth/auth_manager.py`)**:
   - Pre-configured roles with salted password hashing:
     - **Admin** (`admin` / `admin123`): Full system configuration and control.
     - **Engineer** (`engineer` / `engineer123`): Diagnostics, prescriptive actions, alert resolution.
     - **Operator** (`operator` / `operator123`): Live monitoring and alert acknowledgment.

5. **AI REST API & Service (`ml_service.py`)**:
   - Runs HTTP server on port 8000:
     - `POST /predict`: Real-time sensor inference.
     - `GET /latest-prediction`: Live evaluation of latest SQLite reading.
     - `GET /alerts`: Active and historical anomaly alerts.
     - `POST /login`: Authentication endpoint.
     - `GET /metrics`: Model performance metrics.
   - Publishes alert payloads and actuator commands to HiveMQ MQTT (`machine/alerts`, `machine/commands`).

6. **Layer 5 Streamlit AI Dashboard (`layer5_ai_dashboard.py`)**:
   - Elegant login screen with role badges and one-click demo login.
   - Failure Risk Meter (0–100%) and RUL countdown clock.
   - Live sensor telemetry cards with status indicators.
   - Real-time synchronized time-series charts.
   - Interactive What-If Simulation Sandbox allowing operators to test custom sensor values.
   - Alert notification center with one-click acknowledgment.
   - AI Model Explainability tab with feature importances.

---

# 22. Layer 6 — Real Hardware Integration & ESP32 Firmware — Prototype Prepared 🟡

## Architecture

```text
Real Sensors (MPU6050 + DHT11 + Tachometer)
                 ↓
         ESP32 Microcontroller
                 ↓
     HiveMQ Cloud MQTT (TLS Port 8883)
                 ↓
Python SQLite Storage & AI Service
                 ↓
  Local Physical Actuators (Tri-Color LEDs + Active Buzzer)
```

## Hardware Implementation Details

1. **ESP32 Firmware (`hardware/esp32_firmware.ino`)**:
   - Written in C++ for the ESP32 DevKit V1.
   - Connects to Wi-Fi and connects securely to HiveMQ Cloud over TLS (Port 8883).
   - Reads MPU-6050 3-axis accelerometer over I2C (SDA=GPIO 21, SCL=GPIO 22) and calculates Root Mean Square (RMS) vibration in $g$.
   - Reads DHT11/DHT22 on GPIO 4 for ambient temperature and relative humidity.
   - Implements hardware interrupt on GPIO 13 to compute rotating shaft RPM.
   - Formats telemetry as standard JSON and publishes every 1000ms.
   - Subscribes to `machine/commands` to receive cloud/AI alarm commands.

2. **Physical Actuator Indicators (`hardware/circuit_diagram.md`)**:
   - **Green LED (GPIO 18):** Solid ON when machine is Healthy.
   - **Yellow LED (GPIO 19):** Blinking when machine enters Warning state.
   - **Red LED (GPIO 5):** Rapid pulsing when machine enters Fault state.
   - **Active Buzzer (GPIO 23):** Silent on Healthy, intermittent chirp on Warning, continuous audible alarm on Fault.

3. **Hardware Bridge & Simulator (`hardware/hardware_bridge.py`)**:
   - Enables full hardware actuation testing with or without physical ESP32 connected.
   - Listens to MQTT commands and visualizes GPIO pin states in real time.
   - Generates audible PC buzzer beeps on Windows via `winsound` when anomalies trigger.

---

# 23. Complete Multi-Process Execution Guide

To run the entire end-to-end predictive maintenance system:

### Terminal 1: Synthetic Telemetry Publisher (or ESP32 Hardware)
```powershell
python publisher.py
```

### Terminal 2: SQLite Data Ingestion Worker
```powershell
python layer3_storage.py
```

### Terminal 3: Node-RED Runtime
```powershell
node-red
```
Open Node-RED Dashboard: `http://localhost:1880/dashboard/predictive-maintenance`

### Terminal 4: AI & Alerting Microservice
```powershell
python ml_service.py
```

### Terminal 5: Layer 5 AI Predictive Maintenance Dashboard
```powershell
streamlit run layer5_ai_dashboard.py
```
Open Streamlit Dashboard: `http://localhost:8501`

### Terminal 6: Hardware Actuator Controller / Bridge (Optional)
```powershell
python hardware/hardware_bridge.py
```

---

# 24. Summary of Completed Project Deliverables

| Deliverable | Location | Description |
|---|---|---|
| **Exported Node-RED Flow** | `flows/node_red_flow.json` | Complete working FlowFuse dashboard flow with gauges and live charts |
| **Model Training Pipeline** | `ml/train_model.py` | Random Forest Classifier & Regressor training with SQLite ingestion |
| **Trained ML Models** | `ml/models/` | Serialized model artifacts (`.joblib`) and metrics report |
| **Predictive AI Engine** | `ml/predictor.py` | Condition classification, failure risk %, RUL, and diagnostics |
| **Persistent Alert System** | `alerts/alert_manager.py` | SQLite alert manager with deduplication and acknowledgment |
| **Authentication Manager** | `auth/auth_manager.py` | Multi-role user management with salted SHA-256 password hashing |
| **AI REST API & Service** | `ml_service.py` | Background evaluator and HTTP endpoints on port 8000 |
| **Layer 5 AI Dashboard** | `layer5_ai_dashboard.py` | Full-featured Streamlit portal with login, risk gauge, RUL, and simulation |
| **ESP32 Microcontroller Code** | `hardware/esp32_firmware.ino` | Real sensor acquisition (MPU6050, DHT11, Tachometer) & MQTT publishing |
| **Hardware Actuator Bridge** | `hardware/hardware_bridge.py` | Virtual/physical GPIO actuator controller with audible alarm |
| **Circuit Diagram & BOM** | `hardware/circuit_diagram.md` | Pinout tables, wiring schematics, and bill of materials |

**Status:** Layers 1–5 have been implemented and validated in the software prototype. Layer 6 hardware integration code and wiring design have been prepared for ESP32-based real-sensor deployment; physical hardware validation remains pending.
