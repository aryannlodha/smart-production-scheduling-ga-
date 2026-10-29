# Serial Communication Protocol Specification

## 1. Overview & Protocol Principles

The communication between the Python host application and the ESP32 physical prototype is established over standard USB Virtual COM Port (VCP).

- **Baud Rate**: `115200` bps
- **Data Format**: 8 Data bits, No Parity, 1 Stop bit (8-N-1)
- **Framing**: Newline-delimited text (`\n` or `\r\n`)
- **Payload Encoding**: JSON (JavaScript Object Notation)

### Key Architectural Guidelines
1. **Python is the Source of Truth**: All scheduling, mathematical models, virtual clock progression, and optimization logic reside solely on the Python host. The ESP32 is strictly an I/O peripheral for physical feedback and interaction.
2. **Crash-Resistant Parsing**: The ESP32 firmware utilizes ArduinoJson with static memory allocation and boundary checking. Incomplete, corrupted, or malformed JSON strings are safely discarded without locking up the controller.
3. **Decoupled Fallback**: The Python dashboard and scheduling algorithms function identically in **software-only mode** if no serial connection is detected or if the USB cable is disconnected.

---

## 2. Message Envelope Format

Every packet transmitted across the serial bus follows this standard structure:

```json
{
  "type": "<MESSAGE_TYPE>",
  "timestamp": 1234567.89,
  "data": { ... }
}
```

- `type` (String, required): Defines the semantic action.
- `timestamp` (Float/Long, optional): Wall-clock time (Python) or `millis()` counter (ESP32).
- `data` (Object, required): Contextual key-value payload.

---

## 3. Messages: ESP32 $\to$ Python (Events & Inputs)

### 3.1 `STARTUP`
Emitted immediately upon ESP32 power-on / boot initialization.
```json
{
  "type": "STARTUP",
  "timestamp": 450,
  "data": {}
}
```

### 3.2 `HEARTBEAT`
Transmitted every 5,000 ms to confirm link integrity.
```json
{
  "type": "HEARTBEAT",
  "timestamp": 5450,
  "data": {}
}
```

### 3.3 `BREAKDOWN`
Fired when a user presses one of the physical workstation fault buttons.
```json
{
  "type": "BREAKDOWN",
  "timestamp": 18230,
  "data": {
    "machine": "M1"
  }
}
```
*(Available machines: `"M1"`, `"M2"`, `"M3"`)*

### 3.4 `START`
Fired when the physical Start button is pressed.
```json
{
  "type": "START",
  "timestamp": 24100,
  "data": {}
}
```

### 3.5 `RESET`
Fired when the physical Reset button is pressed.
```json
{
  "type": "RESET",
  "timestamp": 31200,
  "data": {}
}
```

---

## 4. Messages: Python $\to$ ESP32 (State Commands & Telemetry)

### 4.1 `STATUS_UPDATE`
Pushes workstation operating states and brief text to the physical panel.
```json
{
  "type": "STATUS_UPDATE",
  "timestamp": 1729864200.12,
  "data": {
    "machines": {
      "M1": "BUSY",
      "M2": "IDLE",
      "M3": "DOWN"
    },
    "display": "T=14.0 Cmax=48"
  }
}
```
- Machine status values:
  - `"IDLE"`: Machine ready; Green LED solid.
  - `"BUSY"`: Machine processing; Green LED blinking.
  - `"DOWN"`: Machine failed; Green LED off, Red LED solid.

### 4.2 `SCHEDULE_UPD`
Notifies the controller that a rescheduled plan has been calculated and adopted.
```json
{
  "type": "SCHEDULE_UPD",
  "timestamp": 1729864210.45,
  "data": {
    "makespan": 54.0,
    "method": "GA (Rescheduled)"
  }
}
```

### 4.3 `DISPLAY_TEXT`
Explicit multi-line update for the 128x64 OLED screen.
```json
{
  "type": "DISPLAY_TEXT",
  "timestamp": 1729864220.00,
  "data": {
    "line1": "Smart Scheduling",
    "line2": "Rescheduled OK",
    "line3": "M1: OK M2: RUN M3: ERR",
    "line4": "Makespan: 54 min"
  }
}
```

---

## 5. Sequence Diagram: Machine Breakdown Rescheduling

```
User               ESP32 (Hardware)               Python (Scheduler)
 │                        │                                │
 ├──[Press M1 Fault]─────>│                                │
 │                        ├─── BREAKDOWN {"machine":"M1"} ─>│
 │                        │                                ├── [Pause M1 Operation]
 │                        │                                ├── [Preserve Completed Ops]
 │                        │                                ├── [Run GA Rescheduler]
 │                        │                                ├── [Compute Revised Makespan]
 │                        │<── STATUS_UPDATE {M1:"DOWN"} ──┤
 │                        │<── SCHEDULE_UPD {makespan:54} ─┤
 │                        ├── [Turn M1 Red LED ON]         │
 │                        ├── [Update OLED: M1 ERR]        │
 │                        │                                │
```
