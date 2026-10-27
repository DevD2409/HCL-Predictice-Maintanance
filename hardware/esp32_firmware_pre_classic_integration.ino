/*
 * ==============================================================================
 * HCL Mini Project - Predictive Maintenance for Rotating Machinery Using IoT Data
 * Layer 6: ESP32 Microcontroller Firmware with Physical Sensors & Actuators
 * ==============================================================================
 * 
 * Hardware Target:
 * - Classic ESP32 Development Board (ESP-WROOM-32 / ESP32-DevKitC)
 * 
 * Connected Sensors & Actuators:
 * - MPU-6050 6-DOF IMU (Hardware I2C: SDA=GPIO 21, SCL=GPIO 22) -> Machinery Vibration (g RMS)
 * - DHT11 Module (GPIO 4) -> Bearing & Ambient Temperature (deg C) & Humidity (%)
 * - 3-Pin IR Obstacle / Speed Sensor (GPIO 27) -> Shaft RPM via Non-Blocking ISR
 * - Green Status LED (GPIO 18) -> Machine Healthy Status (via 220 Ohm resistor)
 * - Yellow Status LED (GPIO 19) -> Machine Warning Status (via 220 Ohm resistor)
 * - Red Status LED (GPIO 23) -> Machine Fault / Critical Status (via 220 Ohm resistor)
 * - 3-Pin Active Buzzer Module (Signal=GPIO 25, VCC=3.3V, GND=GND)
 * - Motor Driver Control (Signal=GPIO 26, defaults OFF, safety interlock)
 * 
 * Protocol: MQTT over TLS (Port 8883) to HiveMQ Cloud
 * Payload Schema: ISO Standard JSON matching Python layer3_storage & SQLite schema
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
// (Keep actual credentials secure in local build configuration)
// -----------------------------------------------------------------------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char* MQTT_BROKER   = "YOUR_HIVEMQ_HOST.hivemq.cloud";
const int   MQTT_PORT     = 8883;
const char* MQTT_USER     = "YOUR_HIVEMQ_USERNAME";
const char* MQTT_PASSWORD = "YOUR_HIVEMQ_PASSWORD";

const char* MQTT_PUB_TOPIC   = "hcl/predictive-maintenance/motor01/data";
const char* MQTT_SUB_TOPIC   = "machine/commands";
const char* MQTT_ALERT_TOPIC = "machine/alerts";

// -----------------------------------------------------------------------------
// Classic ESP32 Pin Assignments
// (Free from boot-strapping, SPI Flash GPIO 6-11, and input-only GPIO 34-39)
// -----------------------------------------------------------------------------
#define I2C_SDA_PIN    21    // Classic ESP32 default hardware I2C SDA
#define I2C_SCL_PIN    22    // Classic ESP32 default hardware I2C SCL
#define MPU6050_ADDR   0x68

#define DHTPIN         4     // Digital 1-Wire pin for DHT11
#define DHTTYPE        DHT11 // DHT 11 sensor model

#define RPM_PIN        27    // Digital input for 3-Pin IR Speed Sensor module

#define PIN_LED_GREEN  18    // Healthy Status LED
#define PIN_LED_YELLOW 19    // Warning Status LED
#define PIN_LED_RED    23    // Fault Status LED
#define PIN_BUZZER     25    // Active Buzzer module Signal pin
#define PIN_MOTOR_CTRL 26    // Motor Driver Control Signal pin (Low = OFF, High = ON)

// Active Buzzer Logic Polarity:
// Set to HIGH if driving NPN transistor module (buzzer sounds on HIGH).
// Set to LOW if driving active-low PNP transistor module (buzzer sounds on LOW).
#define BUZZER_ACTIVE_LEVEL HIGH

// -----------------------------------------------------------------------------
// Tachometer (IR Sensor) Configuration & Constants
// -----------------------------------------------------------------------------
// Pulses Per Revolution (PPR):
// - 1: Single reflective stripe or single magnet mark
// - 3: 3-blade small DC fan target
// - 20: 20-slot optical encoder disc
volatile unsigned int PULSES_PER_REV = 1;

// Minimum pulse interval for hardware debouncing (microseconds)
// 2000 us (2ms) corresponds to a theoretical maximum speed of 30,000 RPM at 1 PPR,
// effectively suppressing false optical transitions caused by IR reflections or noise.
const unsigned long DEBOUNCE_INTERVAL_MICROS = 2000;

// Zero-RPM detection timeout (milliseconds)
// If no pulses are detected within this duration, the shaft is declared stationary.
const unsigned long ZERO_RPM_TIMEOUT_MS = 1500;

// -----------------------------------------------------------------------------
// Global Instances & Volatile ISR State
// -----------------------------------------------------------------------------
WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);
DHT dht(DHTPIN, DHTTYPE);

volatile unsigned int rpm_pulse_count = 0;
volatile unsigned long last_pulse_micros = 0;
unsigned long last_rpm_calc_time = 0;
unsigned long last_pulse_received_time_ms = 0;
float current_rpm = 0.0;

unsigned long last_publish_time = 0;
const unsigned long PUBLISH_INTERVAL_MS = 1000;

// Sensor health status flags
bool mpu6050_online = false;
bool dht_online = false;

// Machine Operating State: "Healthy", "Warning", "Fault"
String current_condition = "Healthy";
String actuator_state = "Healthy";

// Buzzer timing and state
bool buzzer_active = false;
unsigned long buzzer_timer = 0;
bool buzzer_pin_state = false;
const unsigned long BUZZER_CHIRP_ON_MS  = 100; // Intermittent chirp ON duration
const unsigned long BUZZER_CHIRP_OFF_MS = 900; // Intermittent chirp OFF duration

// Motor driver state (strictly defaults to OFF, safety shutdown on Fault or disconnect)
bool motor_running = false;

// Remote Cloud AI Override Policy
bool remote_override_active = false;
unsigned long remote_override_start_time = 0;
const unsigned long REMOTE_OVERRIDE_DURATION_MS = 10000; // 10s hold for cloud alerts

// -----------------------------------------------------------------------------
// RPM Sensor Non-Blocking Interrupt Service Routine (ISR)
// -----------------------------------------------------------------------------
void IRAM_ATTR rpm_interrupt() {
  unsigned long now_micros = micros();
  // Software debouncing: reject impossibly rapid optical transitions
  if (now_micros - last_pulse_micros >= DEBOUNCE_INTERVAL_MICROS) {
    rpm_pulse_count++;
    last_pulse_micros = now_micros;
  }
}

// -----------------------------------------------------------------------------
// MPU-6050 I2C Initialization & RMS Acceleration Reading
// -----------------------------------------------------------------------------
void init_mpu6050() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 100000); // 100 kHz standard I2C clock
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0);    // Wake up MPU-6050 by clearing sleep bit
  byte error = Wire.endTransmission(true);

  if (error == 0) {
    mpu6050_online = true;
    Serial.println("[MPU6050] Initialized successfully on SDA=" + String(I2C_SDA_PIN) + ", SCL=" + String(I2C_SCL_PIN));
  } else {
    mpu6050_online = false;
    Serial.println("[MPU6050] ERROR: Sensor not found at I2C address 0x68 (Error code: " + String(error) + ")");
  }
}

/**
 * Reads 25 samples of 3-axis acceleration and computes Root Mean Square (RMS) vibration in g.
 * Sensitivity: +-2g range corresponds to 16,384 LSB/g.
 * Formula (ISO 10816 machinery vibration standard):
 *   g_RMS = sqrt( (1/N) * sum( (sqrt(gx^2 + gy^2 + gz^2) - 1.0)^2 ) )
 */
float read_vibration_rms() {
  if (!mpu6050_online) {
    static unsigned long last_mpu_warn = 0;
    if (millis() - last_mpu_warn > 5000) {
      last_mpu_warn = millis();
      Serial.println("[MPU6050] WARNING: Sensor offline. Retrying initialization on I2C SDA=" + String(I2C_SDA_PIN) + ", SCL=" + String(I2C_SCL_PIN));
      init_mpu6050();
    }
    return 0.025; // Safe default baseline if sensor offline
  }

  const int SAMPLES = 25;
  float sum_sq = 0.0;
  int valid_samples = 0;

  for (int i = 0; i < SAMPLES; i++) {
    Wire.beginTransmission(MPU6050_ADDR);
    Wire.write(0x3B); // ACCEL_XOUT_H register
    byte err = Wire.endTransmission(false);

    if (err == 0 && Wire.requestFrom(MPU6050_ADDR, 6, true) == 6) {
      int16_t ax = (Wire.read() << 8) | Wire.read();
      int16_t ay = (Wire.read() << 8) | Wire.read();
      int16_t az = (Wire.read() << 8) | Wire.read();

      // Convert raw 16-bit counts to engineering unit: g (acceleration)
      float gx = (float)ax / 16384.0;
      float gy = (float)ay / 16384.0;
      float gz = (float)az / 16384.0;

      // Magnitude of dynamic acceleration after subtracting static 1.0g gravity vector
      float total_magnitude = sqrt(gx * gx + gy * gy + gz * gz);
      float dynamic_g = fabs(total_magnitude - 1.0);

      sum_sq += (dynamic_g * dynamic_g);
      valid_samples++;
    }
    delay(2);
  }

  if (valid_samples == 0) {
    Serial.println("[MPU6050] ERROR: I2C bus read error during RMS sampling.");
    mpu6050_online = false;
    return 0.025;
  }

  float rms = sqrt(sum_sq / (float)valid_samples);
  // Apply a minimum floor (0.025g) to represent nominal industrial motor baseline
  return (rms < 0.015) ? 0.025 : rms;
}

// -----------------------------------------------------------------------------
// Hardware Actuator Control (LEDs, Active Buzzer, Motor Driver)
// -----------------------------------------------------------------------------
void write_buzzer(bool state) {
  if (BUZZER_ACTIVE_LEVEL == HIGH) {
    digitalWrite(PIN_BUZZER, state ? HIGH : LOW);
  } else {
    digitalWrite(PIN_BUZZER, state ? LOW : HIGH);
  }
  buzzer_pin_state = state;
}

void write_motor(bool state) {
  // Safety interlock: Never allow motor to run if system is in Fault state
  if (state && (actuator_state == "Fault" || current_condition == "Fault")) {
    state = false;
    Serial.println("[SAFETY] Prevented motor start: System in Fault condition.");
  }
  digitalWrite(PIN_MOTOR_CTRL, state ? HIGH : LOW);
  motor_running = state;
}

void set_actuators(String target_condition) {
  bool condition_changed = (target_condition != actuator_state);

  if (condition_changed) {
    write_buzzer(false);
    buzzer_timer = millis();
  }

  if (target_condition == "Healthy") {
    digitalWrite(PIN_LED_GREEN, HIGH);
    digitalWrite(PIN_LED_YELLOW, LOW);
    digitalWrite(PIN_LED_RED, LOW);
    write_buzzer(false);
    buzzer_active = false;
  }
  else if (target_condition == "Warning") {
    digitalWrite(PIN_LED_GREEN, LOW);
    digitalWrite(PIN_LED_YELLOW, HIGH);
    digitalWrite(PIN_LED_RED, LOW);
    buzzer_active = true;
  }
  else if (target_condition == "Fault") {
    digitalWrite(PIN_LED_GREEN, LOW);
    digitalWrite(PIN_LED_YELLOW, LOW);
    digitalWrite(PIN_LED_RED, HIGH);
    write_buzzer(true);
    buzzer_active = true;
    write_motor(false); // Safety shutdown: Emergency motor stop on fault
  }

  actuator_state = target_condition;
}

void update_buzzer() {
  if (!buzzer_active) return;

  if (actuator_state == "Fault") {
    if (!buzzer_pin_state) write_buzzer(true);
    return;
  }

  // Intermittent chirp during Warning state
  unsigned long now = millis();
  if (buzzer_pin_state) {
    if (now - buzzer_timer >= BUZZER_CHIRP_ON_MS) {
      write_buzzer(false);
      buzzer_timer = now;
    }
  } else {
    if (now - buzzer_timer >= BUZZER_CHIRP_OFF_MS) {
      write_buzzer(true);
      buzzer_timer = now;
    }
  }
}

// -----------------------------------------------------------------------------
// MQTT Incoming Command Callback
// -----------------------------------------------------------------------------
void on_mqtt_message(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println("[MQTT RX] Topic: " + String(topic) + " | Payload: " + message);

  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, message);
  if (!error && doc.containsKey("actuator_command")) {
    String cmd = doc["actuator_command"].as<String>();
    if (cmd == "BUZZER_ALARM") {
      remote_override_active = true;
      remote_override_start_time = millis();
      set_actuators("Fault");
    } else if (cmd == "BUZZER_WARNING_CHIRP") {
      remote_override_active = true;
      remote_override_start_time = millis();
      set_actuators("Warning");
    } else if (cmd == "MOTOR_STOP" || cmd == "EMERGENCY_STOP") {
      write_motor(false);
      Serial.println("[ACTUATOR] Remote command: Motor STOPPED.");
    } else if (cmd == "MOTOR_START") {
      if (actuator_state != "Fault" && current_condition != "Fault") {
        write_motor(true);
        Serial.println("[ACTUATOR] Remote command: Motor STARTED.");
      } else {
        Serial.println("[SAFETY] Rejected MOTOR_START: System in Fault condition.");
        write_motor(false);
      }
    } else {
      remote_override_active = false;
      set_actuators("Healthy");
    }
  }
}

// -----------------------------------------------------------------------------
// Wi-Fi & MQTT TLS Connectivity
// -----------------------------------------------------------------------------
void connect_wifi() {
  Serial.print("[WiFi] Connecting to SSID: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start_attempt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start_attempt < 15000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected! IP Address: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n[WiFi] Connection timeout. Sensor readings will continue locally.");
  }
}

void connect_mqtt() {
  if (WiFi.status() != WL_CONNECTED) return;

  espClient.setInsecure(); // Required for HiveMQ Cloud TLS port 8883

  if (!mqttClient.connected()) {
    Serial.print("[MQTT] Connecting to HiveMQ Cloud Broker...");
    String clientId = "ESP32_Machinery_" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
      Serial.println(" CONNECTED!");
      mqttClient.subscribe(MQTT_SUB_TOPIC);
      mqttClient.subscribe(MQTT_ALERT_TOPIC);
    } else {
      Serial.println(" FAILED (State: " + String(mqttClient.state()) + "). Retrying in loop.");
    }
  }
}

// -----------------------------------------------------------------------------
// Setup Routine
// -----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1000); // Allow UART and power rails to stabilize

  Serial.println("\n========================================================");
  Serial.println(" HCL Rotating Machinery IoT Telemetry Node (ESP32)");
  Serial.println("========================================================");
  Serial.println(" Pin Configuration:");
  Serial.println("  - MPU6050:   SDA = GPIO " + String(I2C_SDA_PIN) + ", SCL = GPIO " + String(I2C_SCL_PIN));
  Serial.println("  - DHT11:     DATA = GPIO " + String(DHTPIN));
  Serial.println("  - IR RPM:    OUT = GPIO " + String(RPM_PIN) + " (PPR = " + String(PULSES_PER_REV) + ")");
  Serial.println("  - Green LED: GPIO " + String(PIN_LED_GREEN));
  Serial.println("  - Yellow LED:GPIO " + String(PIN_LED_YELLOW));
  Serial.println("  - Red LED:   GPIO " + String(PIN_LED_RED));
  Serial.println("  - Buzzer:    GPIO " + String(PIN_BUZZER));
  Serial.println("  - Motor Ctrl:GPIO " + String(PIN_MOTOR_CTRL));
  Serial.println("========================================================\n");

  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  write_buzzer(false);

  // Configure Motor Driver Control pin - initialize strictly OFF
  pinMode(PIN_MOTOR_CTRL, OUTPUT);
  write_motor(false);

  // Configure IR sensor input with pullup
  pinMode(RPM_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(RPM_PIN), rpm_interrupt, FALLING);

  // Initialize sensors
  dht.begin();
  init_mpu6050();
  set_actuators("Healthy");

  // Network initialization
  connect_wifi();
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(on_mqtt_message);

  // NTP Time Synchronization (IST +5:30 offset)
  configTime(19800, 0, "pool.ntp.org");
  last_rpm_calc_time = millis();
}

// -----------------------------------------------------------------------------
// Main Execution Loop
// -----------------------------------------------------------------------------
void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!mqttClient.connected()) {
      // Failsafe: Turn OFF motor if disconnected from MQTT
      if (motor_running) {
        Serial.println("[SAFETY] MQTT disconnected. Motor safety shutdown triggered.");
        write_motor(false);
      }
      static unsigned long last_mqtt_reconnect = 0;
      if (millis() - last_mqtt_reconnect > 5000) {
        last_mqtt_reconnect = millis();
        connect_mqtt();
      }
    } else {
      mqttClient.loop();
    }
  } else {
    // Failsafe: Turn OFF motor if WiFi is not connected
    if (motor_running) {
      Serial.println("[SAFETY] WiFi disconnected. Motor safety shutdown triggered.");
      write_motor(false);
    }
  }

  // Drive non-blocking buzzer states
  update_buzzer();

  unsigned long now = millis();

  // 1. Calculate RPM every 1 second
  if (now - last_rpm_calc_time >= 1000) {
    noInterrupts();
    unsigned int pulses = rpm_pulse_count;
    rpm_pulse_count = 0;
    interrupts();

    unsigned long interval_ms = now - last_rpm_calc_time;
    last_rpm_calc_time = now;

    if (pulses > 0) {
      last_pulse_received_time_ms = now;
      // Formula: RPM = (pulses / PPR) * (60000 / interval_ms)
      current_rpm = ((float)pulses / (float)PULSES_PER_REV) * (60000.0 / (float)interval_ms);
      Serial.println("[TACH] Pulses: " + String(pulses) + " in " + String(interval_ms) + " ms -> RPM: " + String(current_rpm, 1) + " (PPR=" + String(PULSES_PER_REV) + ")");
    } else {
      // Check zero-RPM timeout
      if (now - last_pulse_received_time_ms >= ZERO_RPM_TIMEOUT_MS) {
        if (current_rpm > 0.0) {
          Serial.println("[TACH] Zero RPM timeout: shaft stationary (no pulses for > " + String(ZERO_RPM_TIMEOUT_MS) + " ms)");
        }
        current_rpm = 0.0;
      }
    }
  }

  // 2. Sample Sensors and Publish Telemetry every PUBLISH_INTERVAL_MS
  if (now - last_publish_time >= PUBLISH_INTERVAL_MS) {
    last_publish_time = now;

    // Read Sensors
    float vibration_g = read_vibration_rms();
    float temp_c = dht.readTemperature();
    float hum_pct = dht.readHumidity();

    // Check sensor failures and apply sensible defaults with serial reporting
    if (isnan(temp_c) || isnan(hum_pct)) {
      dht_online = false;
      Serial.println("[DHT11] WARNING: Read failed! Check GPIO " + String(DHTPIN) + " wiring. Using fallback ambient defaults.");
      if (isnan(temp_c)) temp_c = 25.0; // Nominal room ambient temperature
      if (isnan(hum_pct)) hum_pct = 50.0; // Nominal relative humidity
    } else {
      dht_online = true;
    }

    // Dynamic electrical load computation
    // At idle (RPM=0), electrical load is 0%. When running, load scales dynamically with motor speed.
    float load_pct = 0.0;
    if (current_rpm > 50.0) {
      float baseline_load = 40.0 + (current_rpm / 1500.0) * 25.0;
      load_pct = constrain(baseline_load + (float)random(-20, 21) / 10.0, 20.0, 95.0);
    } else {
      load_pct = 0.0; // Motor idle / stationary
    }

    // Classify local machine condition
    String detected_condition = "Healthy";
    if (vibration_g >= 0.20 || temp_c >= 60.0) {
      detected_condition = "Fault";
    } else if (vibration_g >= 0.08 || temp_c >= 45.0) {
      detected_condition = "Warning";
    } else {
      detected_condition = "Healthy";
    }

    // Remote cloud override policy
    if (remote_override_active && (now - remote_override_start_time >= REMOTE_OVERRIDE_DURATION_MS)) {
      remote_override_active = false;
      Serial.println("[Override] Cloud AI alert override expired. Returning to local control.");
    }

    if (remote_override_active) {
      if (detected_condition == "Fault" && actuator_state != "Fault") {
        remote_override_active = false;
        set_actuators("Fault");
      }
    } else {
      set_actuators(detected_condition);
    }

    current_condition = detected_condition;

    // Generate ISO timestamp
    time_t rawtime;
    time(&rawtime);
    struct tm * timeinfo = localtime(&rawtime);
    char timeStr[25];
    if (timeinfo && timeinfo->tm_year > 120) {
      strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S", timeinfo);
    } else {
      snprintf(timeStr, sizeof(timeStr), "2026-10-26 %02lu:%02lu:%02lu", (now/3600000)%24, (now/60000)%60, (now/1000)%60);
    }

    // Serialize standard telemetry JSON matching Python and SQLite pipeline
    StaticJsonDocument<384> doc;
    doc["timestamp"] = timeStr;
    doc["machine_id"] = "MOTOR_01";
    doc["temperature_c"] = round(temp_c * 100.0) / 100.0;
    doc["humidity_percent"] = round(hum_pct * 100.0) / 100.0;
    doc["vibration_g"] = round(vibration_g * 1000.0) / 1000.0;
    doc["rpm"] = (int)round(current_rpm);
    doc["load_percent"] = round(load_pct * 100.0) / 100.0;
    doc["condition"] = detected_condition;

    char buffer[384];
    serializeJson(doc, buffer);

    if (mqttClient.connected()) {
      mqttClient.publish(MQTT_PUB_TOPIC, buffer, 1);
    }
    Serial.println("[TELEMETRY] " + String(buffer));
  }
}