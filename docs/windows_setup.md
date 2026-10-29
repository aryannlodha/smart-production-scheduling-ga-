# Windows Setup, Environment, and Troubleshooting Guide

## 1. System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Version 3.10 or 3.11 (Python 3.11.9 recommended)
- **Microcontroller Toolchain**: Arduino IDE 2.x (required only for flashing ESP32 firmware)
- **Hardware Connection**: Available USB 2.0/3.0 port

---

## 2. Python Environment Setup on Windows

### Step 2.1: Verify Python Installation
Open **PowerShell** or **Command Prompt** (CMD) and run:
```powershell
python --version
pip --version
```
*(If Python is not found, download it from [python.org](https://www.python.org/downloads/) and ensure you check **"Add python.exe to PATH"** during installation).*

### Step 2.2: Navigate to Project Directory
```powershell
cd "c:\Users\aryan\Desktop\Classroom\Projects\OM PBL"
```

### Step 2.3: Create and Activate Virtual Environment (Recommended)
```powershell
# Create virtual environment named 'venv'
python -m venv venv

# Activate on PowerShell:
.\venv\Scripts\Activate.ps1

# (If PowerShell gives an ExecutionPolicy error, run this once:
#  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser)

# Activate on Command Prompt (cmd.exe):
.\venv\Scripts\activate.bat
```

### Step 2.4: Install Required Packages
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Running the System

### 3.1 Launch Automated Tests
Run the comprehensive 60-test verification suite:
```powershell
pytest tests/ -v
```
All tests should pass cleanly in ~2 seconds.

### 3.2 Launch Interactive Streamlit Dashboard
```powershell
streamlit run app.py
```
This automatically opens your browser at `http://localhost:8501`.

---

## 4. Hardware Driver Setup for ESP32 (Windows)

When connecting the ESP32 to Windows via USB for the first time:

1. Connect the ESP32 board to your PC with a high-quality micro-USB data cable.
2. Open **Device Manager** on Windows (`Win + X` $\to$ `Device Manager`).
3. Expand **Ports (COM & LPT)**:
   - You should see either **Silicon Labs CP210x USB to UART Bridge (COMx)** or **USB-SERIAL CH340 (COMx)**.
   - Note down the `COM` number (e.g., `COM3`, `COM4`).
4. **Missing Driver?**
   - If a yellow exclamation mark appears under "Other devices", download the official driver:
     - **CP2102 Driver**: Silicon Labs CP210x Universal Windows Driver.
     - **CH340 Driver**: WCH CH341SER Windows Driver.

---

## 5. Arduino IDE & Firmware Flashing

1. Download and install **Arduino IDE 2.3+** from [arduino.cc](https://www.arduino.cc/en/software).
2. Open Arduino IDE, navigate to `File -> Preferences`. In **Additional Boards Manager URLs**, add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Open `Tools -> Board -> Boards Manager`, search for `esp32`, click **Install**.
4. Open `Tools -> Manage Libraries...`, search and install:
   - `ArduinoJson` (v6 or v7)
   - `Adafruit SSD1306`
   - `Adafruit GFX Library`
5. Open `firmware\esp32_controller\esp32_controller.ino`.
6. Select Board: `DOIT ESP32 DEVKIT V1` and your active `COM` port.
7. Click the **Upload** button.

---

## 6. Troubleshooting Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'streamlit'` | Virtual environment not activated or pip installed to wrong python | Verify active python: `Get-Command python`; ensure `pip install -r requirements.txt` was run in that environment. |
| ESP32 port does not appear in dashboard or Device Manager | Faulty or charging-only USB cable | Replace with a certified micro-USB data cable. Test on different USB port. |
| `PermissionError: [Errno 13] Access is denied: 'COM3'` | Serial port occupied by Arduino IDE Serial Monitor | Close Arduino IDE Serial Monitor or Cura/terminal tools before connecting via dashboard. |
| Streamlit page reloads or loses state | Session state cleared | Normal on browser refresh. Click "Load Default Data" to restore problem instance in 1 click. |
| ESP32 upload times out with "Connecting......" | Bootloader pin not pulled down automatically | Hold the physical **BOOT** button on the ESP32 for 2 seconds when Arduino IDE shows "Connecting......" until upload starts. |
