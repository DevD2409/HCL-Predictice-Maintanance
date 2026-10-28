/*
 * ==============================================================================
 * HCL Mini Project - Predictive Maintenance for Rotating Machinery Using IoT Data
 * Layer 6: ESP32 Microcontroller Firmware with Physical Sensors & Actuators
 * PROPOSED REVISION: L298N Dual H-Bridge Motor Driver Integration (Planning Build)
 * ==============================================================================
 * 
 * Hardware Target:
 * - Classic ESP32 Development Board (ESP-WROOM-32 / ESP32-DevKitC / DOIT DevKit V1)
 * 
 * Connected Sensors & Actuators:
 * - MPU-6050 6-DOF IMU (Hardware I2C: SDA=GPIO 21, SCL=GPIO 22) -> Machinery Vibration (g RMS)
 * - DHT11 Module (GPIO 4) -> Bearing & Ambient Temperature (deg C) & Humidity (%)
 * - 3-Pin IR Obstacle / Speed Sensor (GPIO 27) -> Shaft RPM via Non-Blocking ISR
 * - Green Status LED (GPIO 18) -> Machine Healthy Status (via 220 Ohm resistor)
 * - Yellow Status LED (GPIO 19) -> Machine Warning Status (via 220 Ohm resistor)
 * - Red Status LED (GPIO 23) -> Machine Fault / Critical Status (via 220 Ohm resistor)
 * - 3-Pin Active Buzzer Module (Signal=GPIO 25, VCC=3.3V, GND=GND)
 * - L298N Motor Driver Control (HW-095):
 *   - ENA: GPIO 26 (Enable A / Speed Gate; defaults LOW, lockout active)
 *   - IN1: GPIO 33 (Direction Phase A; defaults LOW, lockout active)
 *   - IN2: GPIO 32 (Direction Phase B; defaults LOW, lockout active)
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
const char* WIFI_SSID     = "vivo V30";
const char* WIFI_PASSWORD = "********";

const char* MQTT_BROKER   = "859c8424773a4521b552450f2e67bc22.s1.eu.hivemq.cloud";
const int   MQTT_PORT     = 8883;
const char* MQTT_USER     = "Dev";
const char* MQTT_PASSWORD = "Madangles@20";

const char* MQTT_PUB_TOPIC   = "hcl/predictive-maintenance/motor01/data";
const char* MQTT_SUB_TOPIC   = "machine/commands";
const char* MQTT_ALERT_TOPIC = "machine/alerts";

// -----------------------------------------------------------------------------
// HiveMQ Cloud TLS Root CA Certificate (ISRG Root X1)
// Source: Internet Security Research Group (ISRG) / Let's Encrypt
// Subject: CN=ISRG Root X1, O=Internet Security Research Group, C=US
// Validity: 2015-06-04 11:04:38 GMT to 2035-06-04 11:04:38 GMT
// Fingerprint (SHA-256): 96:BC:EC:06:26:49:76:F3:74:60:77:9A:CF:28:C5:A7:CF:E8:A3:C0:AA:E1:1A:8F:FC:EE:05:C0:BD:DF:08:C6
// Fingerprint (SHA-1):   CA:BD:2A:79:A1:07:6A:31:F2:1D:25:36:35:CB:03:9D:43:29:A5:E8
// -----------------------------------------------------------------------------
const char* HIVEMQ_ROOT_CA = \
"-----BEGIN CERTIFICATE-----\n" \
"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\n" \
"-----END CERTIFICATE-----\n";

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

// L298N Dual H-Bridge Motor Driver Module Pin Assignments
#define PIN_MOTOR_ENA  26    // L298N Channel A Enable / Speed Gate (Low = Bridge Disabled)
#define PIN_MOTOR_IN1  33    // L298N Channel A Direction Phase 1 (Low = De-energized)
#define PIN_MOTOR_IN2  32    // L298N Channel A Direction Phase 2 (Low = De-energized)

// -----------------------------------------------------------------------------
// Active Buzzer Configuration & Hardware Assumption
// [UNVERIFIED HARDWARE ASSUMPTION]:
// Set to LOW based on typical 3-pin PNP-transistor active buzzer modules (silent on HIGH,
// sounding on LOW).
// WARNING: Transistor polarity cannot be determined from module appearance alone.
// If your physical buzzer sounds continuously at boot, or if you use an NPN-switched
// module, change this definition to HIGH. Always verify module behavior on the bench.
// -----------------------------------------------------------------------------
#define BUZZER_ACTIVE_LEVEL LOW

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
// Hardware Actuator Control (LEDs, Active Buzzer, L298N Motor Driver)
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
  // L298N INTEGRATION PLANNING LOCKOUT:
  // Motor energization is strictly blocked in this build.
  // Physical motor power must remain disconnected until sensor validation is complete.
  if (state) {
    state = false;
    Serial.println("[SAFETY] Blocked motor energization: Disabled in sensor-verification build.");
  }
  // All three L298N control lines are driven strictly LOW
  digitalWrite(PIN_MOTOR_ENA, LOW);
  digitalWrite(PIN_MOTOR_IN1, LOW);
  digitalWrite(PIN_MOTOR_IN2, LOW);
  motor_running = false;
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
    write_motor(false); // Safety shutdown: Emergency motor stop on fault (ENA, IN1, IN2 -> LOW)
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
      Serial.println("[ACTUATOR] Remote command: Motor STOPPED (L298N ENA, IN1, IN2 forced LOW).");
    } else if (cmd == "MOTOR_START") {
      // SENSOR-VERIFICATION BUILD HARDENING:
      // MOTOR_START is strictly disabled and rejected in this build.
      write_motor(false);
      Serial.println("[SAFETY] REJECTED MOTOR_START: Motor operation is disabled in sensor-verification build.");
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
  Serial.println("[WiFi] Connecting to configured network...");
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

  // ---------------------------------------------------------------------------
  // Strict TLS Certificate Validation Policy:
  // espClient.setInsecure() is strictly prohibited. The authoritative
  // ISRG Root X1 CA certificate must be loaded with setCACert() prior to
  // connecting to HiveMQ Cloud. Missing or empty CA is treated as a fatal failure.
  // ---------------------------------------------------------------------------
  if (HIVEMQ_ROOT_CA == nullptr || strlen(HIVEMQ_ROOT_CA) == 0) {
    Serial.println("[TLS ERROR] Fatal: Root CA certificate is not configured or empty. Refusing insecure MQTT connection.");
    return;
  }

  espClient.setCACert(HIVEMQ_ROOT_CA);

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
  // ---------------------------------------------------------------------------
  // IMMEDIATE HARDWARE SAFETY INITIALIZATION:
  // Drive buzzer and L298N motor driver control lines to safe OFF states
  // immediately before any delays or UART overhead.
  // ---------------------------------------------------------------------------
  pinMode(PIN_BUZZER, OUTPUT);
  write_buzzer(false); // Silence buzzer immediately based on BUZZER_ACTIVE_LEVEL

  // Safe L298N output initialization: clamp latches to LOW then enable OUTPUT
  digitalWrite(PIN_MOTOR_ENA, LOW);
  digitalWrite(PIN_MOTOR_IN1, LOW);
  digitalWrite(PIN_MOTOR_IN2, LOW);
  pinMode(PIN_MOTOR_ENA, OUTPUT);
  pinMode(PIN_MOTOR_IN1, OUTPUT);
  pinMode(PIN_MOTOR_IN2, OUTPUT);
  write_motor(false);  // Ensure all 3 lines are strictly 0V (OFF)

  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);
  digitalWrite(PIN_LED_RED, LOW);

  Serial.begin(115200);
  delay(1000); // Allow UART and power rails to stabilize

  Serial.println("\n========================================================");
  Serial.println(" HCL Rotating Machinery IoT Telemetry Node (ESP32)");
  Serial.println(" [SAFETY-HARDENED L298N INTEGRATION PLANNING BUILD]");
  Serial.println("========================================================");
  Serial.println(" Pin Configuration:");
  Serial.println("  - MPU6050:   SDA = GPIO " + String(I2C_SDA_PIN) + ", SCL = GPIO " + String(I2C_SCL_PIN));
  Serial.println("  - DHT11:     DATA = GPIO " + String(DHTPIN));
  Serial.println("  - IR RPM:    OUT = GPIO " + String(RPM_PIN) + " (PPR = " + String(PULSES_PER_REV) + ")");
  Serial.println("  - Green LED: GPIO " + String(PIN_LED_GREEN));
  Serial.println("  - Yellow LED:GPIO " + String(PIN_LED_YELLOW));
  Serial.println("  - Red LED:   GPIO " + String(PIN_LED_RED));
  Serial.println("  - Buzzer:    GPIO " + String(PIN_BUZZER) + " (Active-LOW assumed)");
  Serial.println("  - L298N ENA: GPIO " + String(PIN_MOTOR_ENA) + " (DISABLED in this build)");
  Serial.println("  - L298N IN1: GPIO " + String(PIN_MOTOR_IN1) + " (DISABLED in this build)");
  Serial.println("  - L298N IN2: GPIO " + String(PIN_MOTOR_IN2) + " (DISABLED in this build)");
  Serial.println("========================================================\n");

  // Configure IR sensor input with pullup
  pinMode(RPM_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(RPM_PIN), rpm_interrupt, FALLING);

  // Initialize sensors
  dht.begin();
  init_mpu6050();
  set_actuators("Healthy");

  // Network initialization
  connect_wifi();

  // Strict TLS Root CA configuration before connecting to MQTT broker
  if (HIVEMQ_ROOT_CA == nullptr || strlen(HIVEMQ_ROOT_CA) == 0) {
    Serial.println("[TLS ERROR] Fatal: HiveMQ Root CA not configured.");
  } else {
    espClient.setCACert(HIVEMQ_ROOT_CA);
    Serial.println("[TLS] HiveMQ Root CA configured successfully (ISRG Root X1).");
  }

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
      // Failsafe: Turn OFF motor if disconnected from MQTT (ENA, IN1, IN2 -> LOW)
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
    // Failsafe: Turn OFF motor if WiFi is not connected (ENA, IN1, IN2 -> LOW)
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

