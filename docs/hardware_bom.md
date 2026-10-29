# Hardware Bill of Materials (BOM) & Budget Estimation

## 1. Prototype Overview

The hardware prototype is a physical control panel and indicator station representing 3 shop floor machines ($M_1, M_2, M_3$). It demonstrates real-time human-in-the-loop interaction and cyber-physical communication with the scheduling engine.

> [!IMPORTANT]
> **Approval Notice**: This document is an engineering recommendation for team review. **Do not make any purchases** until the team and project guide have finalized and approved the budget.

---

## 2. Itemized Bill of Materials (India / INR)

| Item # | Component Description | Specifications / Part # | Qty | Purpose in System | Est. Unit Price (INR) | Total Est. Price (INR) | Recommended Online / Local Sources |
|:------:|-----------------------|-------------------------|:---:|-------------------|:---------------------:|:----------------------:|------------------------------------|
| **1** | ESP32 Development Board | DevKit V1 (30-pin, CP2102/CH340, Wi-Fi+BT) | 1 | Microcontroller running serial protocol, LED control & button interrupt routines | ₹450 – ₹650 | ₹550 | Robu.in, Amazon India, MakerBazar |
| **2** | Green LEDs (5mm) | Diffused Green, Forward Voltage ~2.2V, 20mA max | 3 | Workstation Status: Normal / Idle / Active | ₹3 – ₹5 | ₹12 | Robu.in, Local Electronics Market |
| **3** | Red LEDs (5mm) | Diffused Red, Forward Voltage ~2.0V, 20mA max | 3 | Workstation Status: Machine Fault / Breakdown | ₹3 – ₹5 | ₹12 | Robu.in, Local Electronics Market |
| **4** | Current Limiting Resistors | 220 Ω, 0.25W Metal Film (±1% or ±5%) | 6 | Protect LEDs & ESP32 GPIOs from overcurrent | ₹1 – ₹2 | ₹10 | Robu.in, Local Electronics Market |
| **5** | Pull-Up Resistors | 10 kΩ, 0.25W Carbon Film | 3 | External pull-up for input-only pins (GPIO 34, 35, 36) | ₹1 – ₹2 | ₹5 | Robu.in, Local Electronics Market |
| **6** | Tactile Push Buttons | 6x6x5mm 4-pin momentary tactile switch | 5 | Factory Start, Reset, and Machine Fault Triggers (M1, M2, M3) | ₹5 – ₹8 | ₹30 | Robu.in, MakerBazar |
| **7** | OLED Display Module | 0.96" SSD1306, 128x64 pixels, I2C interface (4-pin) | 1 | Live production metrics display (Virtual Time, Status, Job KPIs) | ₹180 – ₹280 | ₹230 | Amazon India, Robu.in |
| **8** | Solderless Breadboard | 830 tie-point (full size) with power rails | 1 | Circuit prototyping without soldering | ₹90 – ₹140 | ₹110 | Robu.in, Amazon India |
| **9** | Jumper Wires | 40-pin Male-to-Male (20cm) ribbon cable | 1 | Breadboard to ESP32 interconnects | ₹60 – ₹90 | ₹75 | Robu.in, MakerBazar |
| **10** | USB Data Cable | Micro-USB to USB-A (or Type-C, matching board) | 1 | Data transfer and 5V power from host laptop | ₹100 – ₹180 | ₹140 | Amazon India, Local mobile shop |
| **11** | Demonstration Baseplate | A4 Foam-board or 3mm acrylic sheet | 1 | Mounting platform for labeling M1, M2, M3 workstations | ₹50 – ₹100 | ₹80 | Local Stationery shop |

---

## 3. Budget Summary

- **Total Estimated Hardware Cost**: **₹1,150 – ₹1,450 INR** (~$14 – $18 USD)
- **Shared Team Cost (3 Members)**: **~₹380 – ₹480 INR per student**

---

## 4. Component Purchasing Checklist

Before ordering, verify the following details with suppliers:
- [ ] **ESP32 Data Cable**: Ensure the micro-USB cable supports **data transmission** (has 4 internal wires D+, D-, VCC, GND). Many cheap charging-only cables omit data lines and will fail to establish serial communication.
- [ ] **ESP32 Pinout**: Standard 30-pin ESP32 DevKit V1 is recommended for straightforward breadboard spacing.
- [ ] **OLED I2C Address**: Most SSD1306 modules use address `0x3C` (default in our firmware). Check the silk-screen on the back of the OLED PCB.
- [ ] **Dual-color / RGB LED Alternative**: If 5mm individual LEDs are unavailable, common-cathode RGB LEDs can be substituted using the same pinout and 220Ω resistors.
