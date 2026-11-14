# Wokwi ESP32 Simulation Guide

This guide explains how to simulate the ESP32 Production Control Panel on **Wokwi** (https://wokwi.com) — a free, professional-grade online hardware simulator.

## Why Wokwi?

| Platform | ESP32 Support | Free | OLED | LEDs | Buttons | Serial Monitor | Verdict |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **Wokwi** | ✅ Full | ✅ | ✅ SSD1306 | ✅ | ✅ | ✅ | **Best choice** |
| TinkerCAD | ❌ Limited | ✅ | ❌ | ✅ | ✅ | ❌ | No ESP32 |
| Proteus | ✅ | ❌ Paid | ✅ | ✅ | ✅ | ✅ | Professional but expensive |

## Quick Start — Step by Step

### Step 1: Open Wokwi

1. Go to **https://wokwi.com**
2. Sign up / Sign in (free account).
3. Click **"New Project"** → Select **"ESP32"** as the board.

### Step 2: Upload the Firmware Code

1. In the Wokwi code editor (left panel), **delete all existing code**.
2. Open the file: `firmware/esp32_controller/esp32_controller.ino`
3. Copy the **entire** contents and paste into the Wokwi editor.

### Step 3: Set Up the Virtual Circuit

**Option A — Manual (recommended for learning):**

1. Click the **"+"** button in the simulation area to add components.
2. Add these components:
   - 6 × LED (3 green, 3 red)
   - 6 × Resistor (220Ω each)
   - 5 × Push Button
   - 1 × SSD1306 OLED (128×64, I2C)
3. Wire them according to the pin mapping table below.

**Option B — Import diagram.json:**

1. In your Wokwi project, click the **diagram.json** tab (next to the code editor).
2. Replace its contents with the file: `firmware/wokwi/diagram.json`
3. The circuit will auto-populate.

### Step 4: Install Libraries

Click the **"Library Manager"** tab (📚 icon) in Wokwi and add:
- `ArduinoJson` (by Benoit Blanchon)
- `Adafruit SSD1306`
- `Adafruit GFX Library`

### Step 5: Run the Simulation

1. Click the green **▶ Start** button.
2. The OLED display should show:
   ```
   Smart Production
   Scheduling System

   Initializing...
   ```
   Then switch to:
   ```
   Production Panel
   Waiting for host
   ```
3. All 3 green LEDs should turn ON (machines IDLE).

### Step 6: Test Button Presses

| Button | Action | Expected Result |
|--------|--------|-----------------|
| **START** (green) | Click | Serial prints `{"type":"START",...}`, OLED shows "Production Started" |
| **RESET** (blue) | Click | Serial prints `{"type":"RESET",...}`, all LEDs go green, OLED shows "System Reset" |
| **M1 FAIL** (red) | Click | Serial prints `{"type":"BREAKDOWN","data":{"machine":"M1"},...}`, M1 LED switches to red |
| **M2 FAIL** (red) | Click | Same for M2 |
| **M3 FAIL** (red) | Click | Same for M3 |

### Step 7: Test Serial Input (Simulating Python Messages)

1. Open the **Serial Monitor** at the bottom of Wokwi.
2. Type this JSON and press Enter:
   ```json
   {"type":"STATUS_UPDATE","data":{"machines":{"M1":"BUSY","M2":"IDLE","M3":"DOWN"},"display":"Makespan: 38"}}
   ```
3. **Expected**:
   - M1 Green LED blinks (BUSY)
   - M2 Green LED stays solid (IDLE)
   - M3 Red LED turns ON (DOWN)
   - OLED shows "Makespan: 38"
   - Serial responds with `{"type":"ACK",...}`

4. Try another message:
   ```json
   {"type":"DISPLAY_TEXT","data":{"line1":"Schedule Active","line2":"GA Running...","line3":"M1:RUN M2:OK M3:ERR","line4":"t=15 / Makespan=42"}}
   ```
   - OLED display updates with all 4 lines.

5. Try setting a single machine:
   ```json
   {"type":"MACHINE_STATE","data":{"machine":"M2","state":"BUSY"}}
   ```
   - M2 Green LED starts blinking.

## Pin Mapping Reference

| Component | GPIO Pin | Wokwi Connection |
|-----------|----------|-------------------|
| M1 Green LED | 25 | `esp32:25` → 220Ω → LED → GND |
| M1 Red LED | 26 | `esp32:26` → 220Ω → LED → GND |
| M2 Green LED | 27 | `esp32:27` → 220Ω → LED → GND |
| M2 Red LED | 14 | `esp32:14` → 220Ω → LED → GND |
| M3 Green LED | 12 | `esp32:12` → 220Ω → LED → GND |
| M3 Red LED | 13 | `esp32:13` → 220Ω → LED → GND |
| START Button | 32 | `esp32:32` ← Button → GND (internal pull-up) |
| RESET Button | 33 | `esp32:33` ← Button → GND (internal pull-up) |
| M1 Breakdown Button | 34 | `esp32:34` ← Button → GND (needs external 10kΩ pull-up to 3.3V*) |
| M2 Breakdown Button | 35 | `esp32:35` ← Button → GND (needs external 10kΩ pull-up to 3.3V*) |
| M3 Breakdown Button | 36 | `esp32:36` ← Button → GND (needs external 10kΩ pull-up to 3.3V*) |
| OLED SDA | 21 | `esp32:21` → OLED SDA |
| OLED SCL | 22 | `esp32:22` → OLED SCL |
| OLED VCC | 3V3 | `esp32:3V3` → OLED VCC |
| OLED GND | GND | `esp32:GND` → OLED GND |

> **\* Note on GPIO 34/35/36**: On the real ESP32, these are input-only pins with NO internal pull-up resistors. On physical hardware, you need external 10kΩ pull-up resistors from these pins to 3.3V. **In Wokwi, the simulator handles this automatically** — buttons connected to GND work fine in simulation even without external pull-ups. But for the real circuit, always add the 10kΩ pull-ups.

## LED Behavior Summary

| Machine State | Green LED | Red LED |
|:---:|:---:|:---:|
| IDLE | 🟢 Solid ON | ⚫ OFF |
| BUSY | 🟢 Blinking (500ms) | ⚫ OFF |
| DOWN | ⚫ OFF | 🔴 Solid ON |

## What You CAN Test on Wokwi

✅ Button press detection and debouncing  
✅ LED state changes (IDLE → BUSY → DOWN)  
✅ OLED display text updates  
✅ JSON parsing of incoming serial messages  
✅ JSON serialization of outgoing events  
✅ Heartbeat message every 5 seconds  
✅ Buffer overflow handling  
✅ ACK responses to STATUS_UPDATE and SCHEDULE_UPD  

## What You CANNOT Test on Wokwi

❌ Real-time serial communication with Python on your laptop  
❌ Full integration with the Streamlit dashboard  
❌ Real button feel and LED brightness  

> **For full integration testing**, you need the physical ESP32 connected via USB. The Python code (`serial_comm.py`) will communicate over the real COM port.

## Demonstration Script for Wokwi

Use this script during your demo to show the system working:

1. **Start simulation** → Show OLED init message and green LEDs
2. **Press START** → Show serial output, OLED updates to "Production Started"
3. **Send STATUS_UPDATE via serial** → Show M1=BUSY (blinking), M2=IDLE, M3=IDLE
4. **Press M1 FAIL button** → Show M1 turns red, serial sends BREAKDOWN event
5. **Send new STATUS_UPDATE** → Show rescheduled state (M1=DOWN, M2=BUSY, M3=BUSY)
6. **After "repair"**, send STATUS_UPDATE with M1=IDLE → M1 green LED turns back on
7. **Press RESET** → All LEDs go green, OLED shows "System Reset"

## Sharing the Wokwi Project

After setting up, click **Share** → Copy the link. You can share it with your team and professor. They can run the simulation in their browser without installing anything.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| OLED not displaying | Check SDA→GPIO21, SCL→GPIO22, VCC→3V3, GND→GND |
| Button not responding | Make sure button connects the GPIO pin to GND (not VCC) |
| "Library not found" error | Add ArduinoJson, Adafruit SSD1306, Adafruit GFX via Library Manager |
| Serial monitor empty | Make sure baud rate in monitor matches 115200 |
| LEDs not lighting | Check resistor connections — resistor goes between GPIO and LED anode |
