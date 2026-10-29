/*
  ESP32 Production Control Panel Firmware
  ========================================

  Hardware:
  - 3 RGB LEDs (or 3 sets of R/G LEDs) for machine status
  - 5 push buttons: Start, Reset, M1 Breakdown, M2 Breakdown, M3 Breakdown
  - 1 SSD1306 OLED display (I2C)

  Communication:
  - USB Serial at 115200 baud
  - Newline-delimited JSON protocol

  The ESP32 is the physical interface / controller.
  Python on the laptop is the scheduling engine and source of truth.
*/

#include <Arduino.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ===== Pin Definitions =====
// Machine Status LEDs (Active HIGH)
// Each machine has a Green LED (available/idle) and a Red LED (busy/down)
#define M1_LED_GREEN 25
#define M1_LED_RED   26
#define M2_LED_GREEN 27
#define M2_LED_RED   14
#define M3_LED_GREEN 12
#define M3_LED_RED   13

// Push Buttons (Active LOW with internal pull-up)
#define BTN_START    32
#define BTN_RESET    33
#define BTN_M1_BREAK 34
#define BTN_M2_BREAK 35
#define BTN_M3_BREAK 36

// OLED Display (I2C)
#define OLED_WIDTH   128
#define OLED_HEIGHT  64
#define OLED_ADDR    0x3C
#define OLED_SDA     21
#define OLED_SCL     22

// ===== Configuration =====
#define SERIAL_BAUD  115200
#define DEBOUNCE_MS  250        // Button debounce time
#define HEARTBEAT_MS 5000       // Heartbeat interval
#define SERIAL_BUFFER_SIZE 512  // Max JSON message size

// ===== OLED Display =====
Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
bool oledAvailable = false;

// ===== Machine States =====
enum MachineState {
  STATE_IDLE,
  STATE_BUSY,
  STATE_DOWN
};

MachineState machineStates[3] = {STATE_IDLE, STATE_IDLE, STATE_IDLE};
const char* machineNames[3] = {"M1", "M2", "M3"};

// ===== Button State =====
struct Button {
  int pin;
  unsigned long lastPress;
  bool lastState;
};

Button buttons[5] = {
  {BTN_START,    0, HIGH},
  {BTN_RESET,    0, HIGH},
  {BTN_M1_BREAK, 0, HIGH},
  {BTN_M2_BREAK, 0, HIGH},
  {BTN_M3_BREAK, 0, HIGH}
};

// ===== Serial Buffer =====
char serialBuffer[SERIAL_BUFFER_SIZE];
int bufferIndex = 0;

// ===== Timing =====
unsigned long lastHeartbeat = 0;
String displayLine1 = "Production Panel";
String displayLine2 = "Ready";
String displayLine3 = "";
String displayLine4 = "";

// ===== Function Prototypes =====
void setupPins();
void setupOLED();
void handleButtons();
void handleSerial();
void processMessage(const char* json);
void sendEvent(const char* type, const char* data = nullptr);
void updateLEDs();
void updateDisplay();
void setMachineState(int machineIdx, MachineState state);

// ===== Setup =====
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(100);

  setupPins();
  setupOLED();

  // Send startup message
  sendEvent("STARTUP");

  displayLine1 = "Production Panel";
  displayLine2 = "Waiting for host";
  updateDisplay();
}

// ===== Main Loop =====
void loop() {
  handleButtons();
  handleSerial();
  updateLEDs();

  // Periodic heartbeat
  if (millis() - lastHeartbeat >= HEARTBEAT_MS) {
    sendEvent("HEARTBEAT");
    lastHeartbeat = millis();
  }

  delay(10); // Small delay to prevent watchdog issues
}

// ===== Pin Setup =====
void setupPins() {
  // LED outputs
  int ledPins[] = {
    M1_LED_GREEN, M1_LED_RED,
    M2_LED_GREEN, M2_LED_RED,
    M3_LED_GREEN, M3_LED_RED
  };
  for (int i = 0; i < 6; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
  }

  // Button inputs with pull-up
  // Note: GPIO 34, 35, 36 do not have internal pull-ups on ESP32
  // Use external 10k pull-up resistors for these pins
  pinMode(BTN_START, INPUT_PULLUP);
  pinMode(BTN_RESET, INPUT_PULLUP);
  pinMode(BTN_M1_BREAK, INPUT);  // Needs external pull-up
  pinMode(BTN_M2_BREAK, INPUT);  // Needs external pull-up
  pinMode(BTN_M3_BREAK, INPUT);  // Needs external pull-up
}

// ===== OLED Setup =====
void setupOLED() {
  Wire.begin(OLED_SDA, OLED_SCL);
  if (display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    oledAvailable = true;
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("Smart Production");
    display.println("Scheduling System");
    display.println();
    display.println("Initializing...");
    display.display();
  }
}

// ===== Button Handling =====
void handleButtons() {
  unsigned long now = millis();

  for (int i = 0; i < 5; i++) {
    bool currentState = digitalRead(buttons[i].pin);

    // Detect falling edge (button press, active LOW)
    if (currentState == LOW && buttons[i].lastState == HIGH) {
      if (now - buttons[i].lastPress >= DEBOUNCE_MS) {
        buttons[i].lastPress = now;

        switch (i) {
          case 0: // START
            sendEvent("START");
            displayLine2 = "Production Started";
            break;
          case 1: // RESET
            sendEvent("RESET");
            for (int m = 0; m < 3; m++) {
              machineStates[m] = STATE_IDLE;
            }
            displayLine2 = "System Reset";
            break;
          case 2: // M1 BREAKDOWN
            sendEvent("BREAKDOWN", "{\"machine\":\"M1\"}");
            displayLine2 = "M1 BREAKDOWN!";
            setMachineState(0, STATE_DOWN);
            break;
          case 3: // M2 BREAKDOWN
            sendEvent("BREAKDOWN", "{\"machine\":\"M2\"}");
            displayLine2 = "M2 BREAKDOWN!";
            setMachineState(1, STATE_DOWN);
            break;
          case 4: // M3 BREAKDOWN
            sendEvent("BREAKDOWN", "{\"machine\":\"M3\"}");
            displayLine2 = "M3 BREAKDOWN!";
            setMachineState(2, STATE_DOWN);
            break;
        }
        updateDisplay();
      }
    }
    buttons[i].lastState = currentState;
  }
}

// ===== Serial Handling =====
void handleSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (bufferIndex > 0) {
        serialBuffer[bufferIndex] = '\0';
        processMessage(serialBuffer);
        bufferIndex = 0;
      }
    } else {
      if (bufferIndex < SERIAL_BUFFER_SIZE - 1) {
        serialBuffer[bufferIndex++] = c;
      } else {
        // Buffer overflow — discard
        bufferIndex = 0;
      }
    }
  }
}

// ===== Process Incoming JSON Message =====
void processMessage(const char* json) {
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, json);

  if (error) {
    // Invalid JSON — ignore silently
    return;
  }

  const char* type = doc["type"] | "UNKNOWN";

  if (strcmp(type, "STATUS_UPDATE") == 0) {
    // Update machine states
    JsonObject machines = doc["data"]["machines"];
    for (int i = 0; i < 3; i++) {
      if (machines.containsKey(machineNames[i])) {
        const char* state = machines[machineNames[i]];
        if (strcmp(state, "IDLE") == 0) {
          setMachineState(i, STATE_IDLE);
        } else if (strcmp(state, "BUSY") == 0) {
          setMachineState(i, STATE_BUSY);
        } else if (strcmp(state, "DOWN") == 0) {
          setMachineState(i, STATE_DOWN);
        }
      }
    }

    // Update display text
    const char* displayText = doc["data"]["display"] | nullptr;
    if (displayText) {
      displayLine3 = String(displayText);
    }
    updateDisplay();

    // Send acknowledgement
    sendEvent("ACK", "{\"ack\":\"STATUS_UPDATE\"}");
  }
  else if (strcmp(type, "DISPLAY_TEXT") == 0) {
    const char* line1 = doc["data"]["line1"] | nullptr;
    const char* line2 = doc["data"]["line2"] | nullptr;
    const char* line3 = doc["data"]["line3"] | nullptr;
    const char* line4 = doc["data"]["line4"] | nullptr;

    if (line1) displayLine1 = String(line1);
    if (line2) displayLine2 = String(line2);
    if (line3) displayLine3 = String(line3);
    if (line4) displayLine4 = String(line4);
    updateDisplay();
  }
  else if (strcmp(type, "SCHEDULE_UPD") == 0) {
    displayLine2 = "Schedule Updated";
    updateDisplay();
    sendEvent("ACK", "{\"ack\":\"SCHEDULE_UPD\"}");
  }
  else if (strcmp(type, "MACHINE_STATE") == 0) {
    const char* machine = doc["data"]["machine"] | "M1";
    const char* state = doc["data"]["state"] | "IDLE";
    int idx = -1;
    for (int i = 0; i < 3; i++) {
      if (strcmp(machineNames[i], machine) == 0) {
        idx = i;
        break;
      }
    }
    if (idx >= 0) {
      if (strcmp(state, "IDLE") == 0) setMachineState(idx, STATE_IDLE);
      else if (strcmp(state, "BUSY") == 0) setMachineState(idx, STATE_BUSY);
      else if (strcmp(state, "DOWN") == 0) setMachineState(idx, STATE_DOWN);
    }
  }
}

// ===== Send Event to Python =====
void sendEvent(const char* type, const char* data) {
  StaticJsonDocument<256> doc;
  doc["type"] = type;
  doc["timestamp"] = millis();

  if (data != nullptr) {
    // Parse the data string as JSON and attach it
    StaticJsonDocument<128> dataDoc;
    DeserializationError err = deserializeJson(dataDoc, data);
    if (!err) {
      doc["data"] = dataDoc.as<JsonObject>();
    }
  } else {
    doc.createNestedObject("data");
  }

  serializeJson(doc, Serial);
  Serial.println(); // Newline delimiter
}

// ===== Update LED Indicators =====
void updateLEDs() {
  int greenPins[3] = {M1_LED_GREEN, M2_LED_GREEN, M3_LED_GREEN};
  int redPins[3]   = {M1_LED_RED,   M2_LED_RED,   M3_LED_RED};

  for (int i = 0; i < 3; i++) {
    switch (machineStates[i]) {
      case STATE_IDLE:
        digitalWrite(greenPins[i], HIGH);  // Green ON
        digitalWrite(redPins[i], LOW);     // Red OFF
        break;
      case STATE_BUSY:
        // Green blinking — use millis for non-blocking blink
        digitalWrite(greenPins[i], (millis() / 500) % 2 ? HIGH : LOW);
        digitalWrite(redPins[i], LOW);
        break;
      case STATE_DOWN:
        digitalWrite(greenPins[i], LOW);   // Green OFF
        digitalWrite(redPins[i], HIGH);    // Red ON
        break;
    }
  }
}

// ===== Set Machine State =====
void setMachineState(int machineIdx, MachineState state) {
  if (machineIdx >= 0 && machineIdx < 3) {
    machineStates[machineIdx] = state;
  }
}

// ===== Update OLED Display =====
void updateDisplay() {
  if (!oledAvailable) return;

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  // Line 1: Title
  display.setCursor(0, 0);
  display.println(displayLine1);

  // Line 2: Status
  display.setCursor(0, 12);
  display.println(displayLine2);

  // Machine status bar
  display.setCursor(0, 28);
  for (int i = 0; i < 3; i++) {
    display.print(machineNames[i]);
    display.print(":");
    switch (machineStates[i]) {
      case STATE_IDLE: display.print("OK "); break;
      case STATE_BUSY: display.print("RUN"); break;
      case STATE_DOWN: display.print("ERR"); break;
    }
    if (i < 2) display.print(" ");
  }

  // Lines 3-4: Additional info
  if (displayLine3.length() > 0) {
    display.setCursor(0, 42);
    display.println(displayLine3);
  }
  if (displayLine4.length() > 0) {
    display.setCursor(0, 54);
    display.println(displayLine4);
  }

  display.display();
}
