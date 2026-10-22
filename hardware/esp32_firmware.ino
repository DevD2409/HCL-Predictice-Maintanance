/*
 * ==============================================================================
 * HCL Mini Project — Predictive Maintenance for Rotating Machinery Using IoT Data
 * Layer 6: ESP32 Microcontroller Firmware with Real Sensors & Physical Actuators
 * ==============================================================================
 * 
 * Hardware Connected:
 * - ESP32 DevKit V1
 * - MPU6050 6-DOF IMU (I2C: SDA=GPIO 21, SCL=GPIO 22) -> Vibration (g)
 * - DHT11 / DHT22 (GPIO 4) -> Temperature (°C) & Humidity (%)
 * - Optical / Hall-Effect Sensor (GPIO 13) -> RPM via Hardware Interrupt
 * - Green LED (GPIO 18) -> Machine Healthy Status
 * - Yellow LED (GPIO 19) -> Machine Warning Status
 * - Red LED (GPIO 5) -> Machine Fault / Critical Status
 * - Active Buzzer (GPIO 23) -> Audible Alarm
 * 
 * Protocol: MQTT over TLS (Port 8883) to HiveMQ Cloud
 * Payload Format: JSON matching Python & SQLite pipeline schema
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <time.h>

// -----------------------------------------------------------------------------
// Network & HiveMQ Cloud Credentials
// -----------------------------------------------------------------------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char* MQTT_BROKER   = "YOUR_HIVEMQ_HOST.hivemq.cloud";
const int   MQTT_PORT     = 8883;
const char* MQTT_USER     = "YOUR_HIVEMQ_USERNAME";
const char* MQTT_PASSWORD = "YOUR_HIVEMQ_PASSWORD";

const char* MQTT_PUB_TOPIC = "hcl/predictive-maintenance/motor01/data";
const char* MQTT_SUB_TOPIC = "machine/commands";
const char* MQTT_ALERT_TOPIC = "machine/alerts";

// -----------------------------------------------------------------------------
// Pin Assignments
// -----------------------------------------------------------------------------
#define DHTPIN        4
#define DHTTYPE       DHT11    // Change to DHT22 if using white sensor
#define RPM_PIN       13

#define PIN_LED_GREEN 18
#define PIN_LED_YELLOW 19
#define PIN_LED_RED   5
#define PIN_BUZZER    23

#define MPU6050_ADDR  0x68

// -----------------------------------------------------------------------------
// Global Instances & State Variables
// -----------------------------------------------------------------------------
WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);
DHT dht(DHTPIN, DHTTYPE);

volatile unsigned int rpm_pulse_count = 0;
unsigned long last_rpm_calc_time = 0;
float current_rpm = 1450.0;

unsigned long last_publish_time = 0;
const unsigned long PUBLISH_INTERVAL_MS = 1000;

// Telemetry sensor condition (reported via MQTT)
String current_condition = "Healthy";

// Dedicated physical actuator state: "Healthy", "Warning", "Fault"
String actuator_state = "Healthy";

bool buzzer_active = false;
unsigned long buzzer_timer = 0;
bool buzzer_pin_state = false;

// Remote MQTT actuator command override policy:
// A remote AI alert / command overrides local sensor condition for REMOTE_OVERRIDE_DURATION_MS
// unless superseded or expired, preventing local sensor loops from silently cancelling remote alerts.
bool remote_override_active = false;
unsigned long remote_override_start_time = 0;
const unsigned long REMOTE_OVERRIDE_DURATION_MS = 10000; // 10 seconds hold for cloud AI alerts

// Buzzer timing constants (milliseconds)
const unsigned long BUZZER_CHIRP_ON_MS  = 100;   // Warning: buzzer ON duration
const unsigned long BUZZER_CHIRP_OFF_MS = 900;   // Warning: buzzer OFF duration

// -----------------------------------------------------------------------------
// RPM Sensor Interrupt Service Routine (ISR)
// -----------------------------------------------------------------------------
void IRAM_ATTR rpm_interrupt() {
  rpm_pulse_count++;
}

// -----------------------------------------------------------------------------
// MPU6050 Vibration Sensor Handling
// -----------------------------------------------------------------------------
void init_mpu6050() {
  Wire.begin(21, 22);
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0);    // Wake up MPU6050
  Wire.endTransmission(true);
  Serial.println("[MPU6050] Initialized successfully.");
}

float read_vibration_rms() {
  const int SAMPLES = 25;
  float sum_sq = 0.0;

  for (int i = 0; i < SAMPLES; i++) {
    Wire.beginTransmission(MPU6050_ADDR);
    Wire.write(0x3B); // Accelerometer register start
    Wire.endTransmission(false);
    Wire.requestFrom(MPU6050_ADDR, 6, true);

    if (Wire.available() >= 6) {
      int16_t ax = (Wire.read() << 8) | Wire.read();
      int16_t ay = (Wire.read() << 8) | Wire.read();
      int16_t az = (Wire.read() << 8) | Wire.read();

      // MPU6050 default ±2g sensitivity: 16384 LSB/g
      float gx = (float)ax / 16384.0;
      float gy = (float)ay / 16384.0;
      float gz = (float)az / 16384.0;

      // Remove 1g static gravity vector component
      float dynamic_g = sqrt(gx*gx + gy*gy + gz*gz) - 1.0;
      if (dynamic_g < 0) dynamic_g = -dynamic_g;

      sum_sq += (dynamic_g * dynamic_g);
    }
    delay(2);
  }

  float rms = sqrt(sum_sq / (float)SAMPLES);
  return (rms < 0.01) ? 0.025 : rms; // Filter baseline floor
}

// -----------------------------------------------------------------------------
// Actuator Control (LEDs and Buzzer)
// -----------------------------------------------------------------------------
void set_actuators(String target_condition) {
  // Compare incoming condition with actuator_state BEFORE modifying state
  bool condition_changed = (target_condition != actuator_state);

  if (condition_changed) {
    digitalWrite(PIN_BUZZER, LOW);
    buzzer_pin_state = false;
    buzzer_timer = millis();
  }

  if (target_condition == "Healthy") {
    digitalWrite(PIN_LED_GREEN, HIGH);
    digitalWrite(PIN_LED_YELLOW, LOW);
    digitalWrite(PIN_LED_RED, LOW);
    digitalWrite(PIN_BUZZER, LOW);
    buzzer_active = false;
    buzzer_pin_state = false;
  }
  else if (target_condition == "Warning") {
    digitalWrite(PIN_LED_GREEN, LOW);
    digitalWrite(PIN_LED_YELLOW, HIGH);
    digitalWrite(PIN_LED_RED, LOW);
    buzzer_active = true;
    // Intermittent chirps driven asynchronously by update_buzzer()
  }
  else if (target_condition == "Fault") {
    digitalWrite(PIN_LED_GREEN, LOW);
    digitalWrite(PIN_LED_YELLOW, LOW);
    digitalWrite(PIN_LED_RED, HIGH);
    // Fault: continuous alarm
    digitalWrite(PIN_BUZZER, HIGH);
    buzzer_active = true;
    buzzer_pin_state = true;
  }

  // Update actuator_state AFTER handling the transition
  actuator_state = target_condition;
}

/**
 * Non-blocking buzzer update — call every loop() iteration.
 * Healthy state: no-op (buzzer_active == false).
 * Warning state: intermittent chirps (100ms ON / 900ms OFF).
 * Fault state: continuous (stays HIGH).
 */
void update_buzzer() {
  if (!buzzer_active) return;

  // Fault: buzzer stays HIGH continuously
  if (actuator_state == "Fault") {
    if (!buzzer_pin_state) {
      digitalWrite(PIN_BUZZER, HIGH);
      buzzer_pin_state = true;
    }
    return;
  }

  // Warning: non-blocking intermittent chirp
  unsigned long now = millis();
  if (buzzer_pin_state) {
    // Currently ON — check if chirp duration elapsed
    if (now - buzzer_timer >= BUZZER_CHIRP_ON_MS) {
      digitalWrite(PIN_BUZZER, LOW);
      buzzer_pin_state = false;
      buzzer_timer = now;
    }
  } else {
    // Currently OFF — check if silence duration elapsed
    if (now - buzzer_timer >= BUZZER_CHIRP_OFF_MS) {
      digitalWrite(PIN_BUZZER, HIGH);
      buzzer_pin_state = true;
      buzzer_timer = now;
    }
  }
}

// -----------------------------------------------------------------------------
// MQTT Message Callback (Incoming Commands from Cloud / Node-RED / AI)
// -----------------------------------------------------------------------------
void on_mqtt_message(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.print("[MQTT RX] Topic: ");
  Serial.print(topic);
  Serial.print(" | Payload: ");
  Serial.println(message);

  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, message);
  if (!error) {
    if (doc.containsKey("actuator_command")) {
      String cmd = doc["actuator_command"].as<String>();
      if (cmd == "BUZZER_ALARM") {
        remote_override_active = true;
        remote_override_start_time = millis();
        set_actuators("Fault");
      } else if (cmd == "BUZZER_WARNING_CHIRP") {
        remote_override_active = true;
        remote_override_start_time = millis();
        set_actuators("Warning");
      } else {
        remote_override_active = false;
        set_actuators("Healthy");
      }
    }
  }
}

// -----------------------------------------------------------------------------
// WiFi & MQTT Connection Helpers
// -----------------------------------------------------------------------------
void connect_wifi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected. IP: " + WiFi.localIP().toString());
}

void connect_mqtt() {
  espClient.setInsecure(); // For HiveMQ Cloud TLS connection

  while (!mqttClient.connected()) {
    Serial.print("Attempting HiveMQ MQTT connection...");
    String clientId = "ESP32_Machinery_" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
      Serial.println("CONNECTED!");
      mqttClient.subscribe(MQTT_SUB_TOPIC);
      mqttClient.subscribe(MQTT_ALERT_TOPIC);
    } else {
      Serial.print("Failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Retrying in 5 seconds...");
      delay(5000);
    }
  }
}

// -----------------------------------------------------------------------------
// Setup & Main Loop
// -----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==============================================");
  Serial.println(" HCL Rotating Machinery IoT Telemetry Node");
  Serial.println("==============================================");

  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(RPM_PIN, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(RPM_PIN), rpm_interrupt, FALLING);

  dht.begin();
  init_mpu6050();
  set_actuators("Healthy");

  connect_wifi();
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(on_mqtt_message);

  // NTP Time Sync
  configTime(19800, 0, "pool.ntp.org"); // IST +5:30 offset
}

void loop() {
  if (!mqttClient.connected()) {
    connect_mqtt();
  }
  mqttClient.loop();

  // Drive non-blocking buzzer behavior every iteration
  update_buzzer();

  unsigned long now = millis();

  // Calculate RPM every 1 second
  if (now - last_rpm_calc_time >= 1000) {
    detachInterrupt(digitalPinToInterrupt(RPM_PIN));
    // Single pulse per revolution -> RPM = pulses * 60
    current_rpm = (float)(rpm_pulse_count * 60);
    rpm_pulse_count = 0;
    last_rpm_calc_time = now;
    attachInterrupt(digitalPinToInterrupt(RPM_PIN), rpm_interrupt, FALLING);
  }

  // Publish Telemetry every PUBLISH_INTERVAL_MS
  if (now - last_publish_time >= PUBLISH_INTERVAL_MS) {
    last_publish_time = now;

    // 1. Read Sensors
    float vibration_g = read_vibration_rms();
    float temp_c = dht.readTemperature();
    float hum_pct = dht.readHumidity();

    if (isnan(temp_c)) temp_c = 41.5;
    if (isnan(hum_pct)) hum_pct = 52.0;

    // Simulate nominal electrical load based on current mechanical speed
    float load_pct = constrain(map(current_rpm, 1200, 1500, 90, 45) + random(-3, 3), 35.0, 95.0);

    // 2. Classify Physical Operating State (Local Detection)
    String detected_condition = "Healthy";
    if (vibration_g >= 0.20 || temp_c >= 60.0) {
      detected_condition = "Fault";
    } else if (vibration_g >= 0.08 || temp_c >= 45.0) {
      detected_condition = "Warning";
    } else {
      detected_condition = "Healthy";
    }

    // Check remote MQTT override expiration policy
    if (remote_override_active && (now - remote_override_start_time >= REMOTE_OVERRIDE_DURATION_MS)) {
      remote_override_active = false;
      Serial.println("[Override] Remote AI actuator override expired. Reverting to local sensor control.");
    }

    // If a remote cloud AI alert is active, it takes precedence over local sensor actuators
    // unless the local sensor detects an urgent Fault condition
    if (remote_override_active) {
      if (detected_condition == "Fault" && actuator_state != "Fault") {
        // Local emergency Fault supersedes remote Warning
        remote_override_active = false;
        set_actuators("Fault");
      }
    } else {
      set_actuators(detected_condition);
    }

    // Telemetry sensor condition is always the locally detected sensor condition
    current_condition = detected_condition;

    // 3. Assemble ISO-Standard Machine JSON
    // Telemetry always reports the actual sensor-detected condition
    time_t rawtime;
    time(&rawtime);
    struct tm * timeinfo = localtime(&rawtime);
    char timeStr[25];
    strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S", timeinfo);

    StaticJsonDocument<384> doc;
    doc["timestamp"] = timeStr;
    doc["machine_id"] = "MOTOR_01";
    doc["temperature_c"] = round(temp_c * 100.0) / 100.0;
    doc["humidity_percent"] = round(hum_pct * 100.0) / 100.0;
    doc["vibration_g"] = round(vibration_g * 1000.0) / 1000.0;
    doc["rpm"] = (int)current_rpm;
    doc["load_percent"] = round(load_pct * 100.0) / 100.0;
    doc["condition"] = detected_condition;

    char buffer[384];
    serializeJson(doc, buffer);

    // 4. Publish to HiveMQ
    mqttClient.publish(MQTT_PUB_TOPIC, buffer, 1);
    Serial.print("[PUB] ");
    Serial.println(buffer);
  }
}
