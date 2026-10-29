# Smart Production Scheduling and Dynamic Rescheduling Using Genetic Algorithm: A Physical Prototype-Based Approach

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)
[![Hardware: ESP32](https://img.shields.io/badge/Hardware-ESP32-green.svg)](https://www.espressif.com/)
[![Tests: Pytest (60 Passed)](https://img.shields.io/badge/Tests-60%20Passed-brightgreen.svg)](tests/)

An undergraduate **Industrial Engineering and Management (IEM) / Operations Management** Project-Based Learning (PBL) system.

The project models a multi-job, multi-machine Job Shop Scheduling Problem (JSSP), searches for makespan-minimizing schedules using a customized **Genetic Algorithm (GA)**, evaluates performance against classic dispatching heuristics (**FCFS, SPT, EDD**), simulates machine breakdowns in discrete virtual time, dynamically reschedules remaining tasks, and demonstrates the workflow via an interactive **Streamlit dashboard** coupled with an **ESP32 physical control panel**.

---

## 📌 Project Overview

```
                        +---------------------------------------------+
                        |           STREAMLIT WEB DASHBOARD           |
                        |  - Inputs  - Gantt Chart  - Dynamic Sim     |
                        +---------------------------------------------+
                                              │
                                              ▼
                        +---------------------------------------------+
                        |        PYTHON JSSP SCHEDULING ENGINE        |
                        |  - Operation-Based Chromosome Decoder       |
                        |  - Genetic Algorithm (POX Crossover)        |
                        |  - Dispatching Rules (FCFS, SPT, EDD)       |
                        |  - Discrete-Event Simulation & Rescheduler  |
                        +---------------------------------------------+
                                              │
                                              ▼ (USB Serial / JSON)
                        +---------------------------------------------+
                        |       ESP32 PHYSICAL CONTROL PROTOTYPE      |
                        |  - Machine Status LEDs (M1, M2, M3)         |
                        |  - Breakdown Injection Buttons              |
                        |  - SSD1306 OLED Telemetry Display           |
                        +---------------------------------------------+
```

---

## 🚀 Key Features

1. **JSSP Mathematical Scheduling Engine**:
   - Fixed-route Job Shop Scheduling Problem with configurable jobs, operations, routes, and durations.
   - Comprehensive constraint verification: contiguous operation numbering, job precedence ($S_{i,j+1} \ge C_{i,j}$), and machine exclusivity.
2. **Genetic Algorithm Optimization**:
   - **Operation-Based Chromosome Encoding** guaranteeing precedence feasibility without repair heuristics.
   - **Precedence Operation Crossover (POX)** and **Swap Mutation**.
   - Tournament selection and elitism.
   - Makespan ($C_{\max}$) minimization fitness function.
3. **Multi-Heuristic Comparative Benchmarks**:
   - Implements **FCFS** (First-Come, First-Served), **SPT** (Shortest Processing Time), and **EDD** (Earliest Due Date) as multi-machine dispatching simulations.
   - Computes Makespan, Total Tardiness, Machine Utilization (%), and Machine Idle Time.
4. **Dynamic Rescheduling Simulation**:
   - Simulates machine breakdown at any arbitrary point in virtual time.
   - Freezes and preserves completed operations.
   - Pauses interrupted operations with configurable resumption policy (`RESUME` with remaining time or `RESTART`).
   - Automatically re-optimizes remaining pending operations using the GA.
5. **Physical Hardware Prototype (ESP32 DevKit)**:
   - Workstation status indicators (Green solid = Available, Green blinking = Busy, Red solid = Breakdown).
   - Physical fault-injection push buttons to trigger machine breakdown in real time.
   - SSD1306 128x64 OLED display providing live schedule telemetry.
   - Full **software-only fallback mode** when hardware is not plugged in.
6. **Automated Verification**:
   - Comprehensive test suite with **60 unit and integration tests** passing via `pytest`.

---

## 🛠️ Quick Start (Windows)

### 1. Clone / Navigate to Project
```powershell
cd "c:\Users\aryan\Desktop\Classroom\Projects\OM PBL"
```

### 2. Set Up Virtual Environment & Install Dependencies
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Run Automated Tests
```powershell
pytest tests/ -v
```
*(All 60 tests will pass in ~2 seconds).*

### 4. Launch the Interactive Dashboard
```powershell
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 📂 Project Structure

```
├── app.py                         # Streamlit multi-page interactive web dashboard
├── requirements.txt               # Python package dependencies
├── .gitignore                     # Git ignore rules for Python & IDEs
├── README.md                      # Primary project documentation
├── data/
│   ├── jobs.csv                   # Job definitions, release times, due dates
│   ├── operations.csv             # Technological routes, operation sequence, durations
│   └── machines.csv               # Workstation metadata and available times
├── src/
│   ├── scheduler/
│   │   ├── models.py              # Dataclasses & CSV loading with strict validation
│   │   └── decoder.py             # Active schedule builder & constraint validator
│   ├── genetic_algorithm/
│   │   └── ga.py                  # Core GA: POX crossover, swap mutation, tournament, elitism
│   ├── baselines/
│   │   └── dispatching.py         # FCFS, SPT, and EDD dispatching heuristics
│   ├── simulation/
│   │   └── engine.py              # Virtual clock simulator, breakdown handler & rescheduler
│   ├── metrics/
│   │   ├── performance.py         # Makespan, tardiness, utilization & idle time calculations
│   │   ├── visualization.py       # Interactive Plotly & Matplotlib Gantt chart generators
│   │   └── experiments.py         # Batch experiment runner & CSV export utilities
│   └── hardware/
│       └── serial_comm.py         # USB serial communication handler with JSON protocol
├── firmware/
│   └── esp32_controller/
│       └── esp32_controller.ino  # Arduino C++ firmware for ESP32, LEDs, buttons & OLED
├── tests/
│   └── test_scheduling.py        # 60 automated test cases (pytest)
└── docs/
    ├── architecture.md            # System architecture and data flow
    ├── problem_formulation.md     # Mathematical formulation of JSSP & KPIs
    ├── ga_explanation.md          # In-depth GA operators, chromosome decoding & theory
    ├── hardware_bom.md            # Hardware Bill of Materials & Indian pricing (INR)
    ├── wiring_and_assembly.md     # Circuit schematic, breadboard wiring & pinout map
    ├── serial_protocol.md         # JSON serial protocol specification
    ├── windows_setup.md           # Step-by-step Windows & Arduino IDE configuration
    ├── user_manual.md             # Complete dashboard demonstration walkthrough
    ├── experiment_plan.md         # Benchmarking methodology & empirical study plan
    ├── literature_review.md       # Literature review, citations & research scope
    └── team_work_distribution.md  # 3-member team role matrix & timeline
```

---

## 🔌 Hardware Demonstration (ESP32)

```
       ESP32 DevKit V1                 Breadboard Circuit
     +-----------------+          +---------------------------+
     |  GPIO 25, 26    |--------->| M1 Status LEDs (Green/Red)|
     |  GPIO 27, 14    |--------->| M2 Status LEDs (Green/Red)|
     |  GPIO 12, 13    |--------->| M3 Status LEDs (Green/Red)|
     |  GPIO 32, 33    |<---------| Start & Reset Buttons     |
     |  GPIO 34, 35, 36|<---------| M1, M2, M3 Break Buttons  |
     |  GPIO 21, 22    |--------->| SSD1306 I2C OLED Display  |
     +-----------------+          +---------------------------+
               │
               ▼ (Micro-USB Cable, 115200 Baud JSON)
         Host Laptop (Python Engine + Streamlit Dashboard)
```

- Complete wiring schematics and assembly steps are provided in [`docs/wiring_and_assembly.md`](docs/wiring_and_assembly.md).
- Detailed component pricing (~₹1,150 – ₹1,450 INR) is provided in [`docs/hardware_bom.md`](docs/hardware_bom.md).

---

## 👥 Three-Member Team Responsibilities

- **Member 1 (Operations Management & OR Modeling)**: Problem formulation, benchmark datasets, baseline dispatching heuristics (FCFS, SPT, EDD), KPI analysis, and literature review.
- **Member 2 (Python & Genetic Algorithm Optimization)**: Chromosome decoder, GA operators (POX, swap mutation), dynamic rescheduling engine, automated testing, and web dashboard.
- **Member 3 (Embedded Systems & Hardware Integration)**: Breadboard circuit assembly, pull-up resistors configuration, ESP32 firmware development, and serial JSON protocol integration.

Detailed breakdown available in [`docs/team_work_distribution.md`](docs/team_work_distribution.md).

---

## 📄 License

This project is developed for educational and academic purposes under the MIT License.
