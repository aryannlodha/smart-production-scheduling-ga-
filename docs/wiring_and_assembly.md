# Circuit Wiring, Breadboard Layout, and Assembly Guide

## 1. Pin Assignment Table

| ESP32 Pin Label | GPIO Number | Connected Component | Connection Details | Circuit Type |
|:---------------:|:-----------:|:-------------------:|:-------------------|:-------------|
| **D25** | GPIO 25 | Machine 1 Green LED | Anode $\to$ 220Ω $\to$ GPIO 25; Cathode $\to$ GND | Digital Output (Active HIGH) |
| **D26** | GPIO 26 | Machine 1 Red LED | Anode $\to$ 220Ω $\to$ GPIO 26; Cathode $\to$ GND | Digital Output (Active HIGH) |
| **D27** | GPIO 27 | Machine 2 Green LED | Anode $\to$ 220Ω $\to$ GPIO 27; Cathode $\to$ GND | Digital Output (Active HIGH) |
| **D14** | GPIO 14 | Machine 2 Red LED | Anode $\to$ 220Ω $\to$ GPIO 14; Cathode $\to$ GND | Digital Output (Active HIGH) |
| **D12** | GPIO 12 | Machine 3 Green LED | Anode $\to$ 220Ω $\to$ GPIO 12; Cathode $\to$ GND | Digital Output (Active HIGH) |
| **D13** | GPIO 13 | Machine 3 Red LED | Anode $\to$ 220Ω $\to$ GPIO 13; Cathode $\to$ GND | Digital Output (Active HIGH) |
| **D32** | GPIO 32 | Start Button | Terminal 1 $\to$ GPIO 32; Terminal 2 $\to$ GND | Digital Input (Internal Pull-Up) |
| **D33** | GPIO 33 | Reset Button | Terminal 1 $\to$ GPIO 33; Terminal 2 $\to$ GND | Digital Input (Internal Pull-Up) |
| **D34** | GPIO 34 | M1 Breakdown Button | Terminal 1 $\to$ GPIO 34 & 10kΩ to 3.3V; Terminal 2 $\to$ GND | Input-Only (External Pull-Up) |
| **D35** | GPIO 35 | M2 Breakdown Button | Terminal 1 $\to$ GPIO 35 & 10kΩ to 3.3V; Terminal 2 $\to$ GND | Input-Only (External Pull-Up) |
| **VP / D36** | GPIO 36 | M3 Breakdown Button | Terminal 1 $\to$ GPIO 36 & 10kΩ to 3.3V; Terminal 2 $\to$ GND | Input-Only (External Pull-Up) |
| **D21** | GPIO 21 | OLED SDA | OLED SDA $\to$ GPIO 21 | I2C Data Line |
| **D22** | GPIO 22 | OLED SCL | OLED SCL $\to$ GPIO 22 | I2C Clock Line |
| **3V3** | 3.3V Rail | OLED VCC & Pull-Ups | Power supply for display and 10kΩ pull-ups | Regulated 3.3V Power |
| **GND** | Ground Rail | LED Cathodes, Buttons, OLED GND | Common ground reference across circuit | Common GND |

---

## 2. Electrical Wiring Schematics

### 2.1 LED Workstation Indicators (Active HIGH)
For each machine workstation ($M_1, M_2, M_3$):
```
ESP32 GPIO ───[ 220 Ω ]───( Anode >| Cathode )─── GND
```
- **Forward Current**: With $V_{OH} = 3.3\text{V}$ and $V_F \approx 2.0\text{V}$, $I \approx \frac{3.3 - 2.0}{220} \approx 5.9\text{ mA}$ (well within the ESP32 GPIO maximum 12mA rating).
- **Operation States**:
  - Green Solid: Workstation Idle / Available.
  - Green Blinking (500ms): Workstation Busy processing an operation.
  - Red Solid: Workstation Failed / Down (Repair in progress).

### 2.2 Tactile Push Buttons (Active LOW)
- **Start (GPIO 32) & Reset (GPIO 33)**: Utilize the ESP32's built-in internal pull-up resistor (`pinMode(pin, INPUT_PULLUP)`):
```
ESP32 GPIO 32/33 ──────┬──────[ Push Button ]────── GND
                       │
             (Internal Pull-up to 3.3V)
```
- **Breakdown Triggers (GPIO 34, 35, 36)**:
  > [!CAUTION]
  > **Crucial ESP32 Hardware Note**: Pins GPIO 34, 35, 36 (Sens_VP), and 39 (Sens_VN) on the ESP32 are **input-only** pins (GPI). They do **NOT** have internal pull-up or pull-down resistors inside the silicon!
  > Therefore, you **must wire an external 10 kΩ pull-up resistor** from the GPIO pin to the 3.3V rail:
```
                3.3V Rail
                   │
                [ 10 kΩ ]
                   │
ESP32 GPIO 34/35/36 ───┴──────[ Push Button ]────── GND
```
- When pressed, the input is pulled directly to GND (reads `LOW`). When released, the 10kΩ resistor pulls it cleanly to 3.3V (reads `HIGH`), preventing floating input noise.

### 2.3 SSD1306 OLED Display (I2C)
```
OLED VCC  ─── 3.3V
OLED GND  ─── GND
OLED SDA  ─── GPIO 21
OLED SCL  ─── GPIO 22
```

---

## 3. Step-by-Step Breadboard Assembly Instructions

1. **Safety Pre-Check**: Ensure the ESP32 is **unplugged** from the laptop before placing wires.
2. **Mount ESP32**: Insert the ESP32 DevKit board bridging the central divider trench of the breadboard.
3. **Power Rails**:
   - Run a jumper wire from the ESP32 **GND** pin to the blue negative (-) power rail.
   - Run a jumper wire from the ESP32 **3V3** pin to the red positive (+) power rail.
4. **Wire LEDs**:
   - Insert 3 Green and 3 Red LEDs representing Workstations 1, 2, and 3.
   - Connect the cathode (shorter lead / flat rim) of all 6 LEDs to the blue ground rail.
   - Connect a 220Ω resistor to the anode (longer lead) of each LED.
   - Run jumper wires from the resistors to the respective GPIO pins (25, 26, 27, 14, 12, 13).
5. **Wire Control Buttons**:
   - Mount 5 tactile push buttons across the breadboard.
   - Connect one pin of each button to GND.
   - Connect the opposing pin of Start and Reset buttons to GPIO 32 and 33.
   - Connect the opposing pin of M1, M2, M3 Breakdown buttons to GPIO 34, 35, 36, and install the three 10kΩ pull-up resistors to the 3.3V rail.
6. **Wire OLED Screen**:
   - Connect VCC to 3.3V, GND to Ground, SDA to GPIO 21, and SCL to GPIO 22.
7. **Double Check**: Check for any shorts between 3.3V and GND before plugging in USB!

---

## 4. Firmware Flashing Guide (Arduino IDE)

1. **Install Arduino IDE 2.x** from [arduino.cc](https://www.arduino.cc/en/software).
2. **Add ESP32 Board Support**:
   - In Arduino IDE, go to `File -> Preferences`.
   - In "Additional Boards Manager URLs", paste:
     `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Go to `Tools -> Board -> Boards Manager`, search for `esp32`, and install `esp32 by Espressif Systems`.
3. **Install Required Libraries**:
   - Go to `Tools -> Manage Libraries...`
   - Search and install **`ArduinoJson`** (by Benoit Blanchon, v6.x or v7.x).
   - Search and install **`Adafruit SSD1306`** (by Adafruit).
   - Search and install **`Adafruit GFX Library`** (by Adafruit).
4. **Select Board & Port**:
   - `Tools -> Board -> esp32 -> DOIT ESP32 DEVKIT V1` (or generic `ESP32 Dev Module`).
   - Connect USB cable, select port: `Tools -> Port -> COMx` (check Windows Device Manager).
5. **Open & Upload**:
   - Open `firmware/esp32_controller/esp32_controller.ino`.
   - Click the **Upload** arrow button.
   - *(Note: If upload stalls at "Connecting......", press and hold the `BOOT` button on the ESP32 until the upload progress percentage appears).*
6. **Verify Operation**:
   - Open Serial Monitor at **115200 baud**.
   - You will see the startup JSON: `{"type":"STARTUP","timestamp":...,"data":{}}`.
