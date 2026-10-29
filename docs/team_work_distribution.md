# Three-Member Team Work Distribution Matrix

This project is structured for a 3-member undergraduate Industrial Engineering and Management (IEM) team. Each member holds primary ownership over a specific subsystem, while remaining knowledgeable about the complete integrated project.

---

## 1. Member Ownership Breakdown

### 👤 Member 1: Operations Management & Scheduling Models
**Role**: Lead Industrial Engineer & OR Modeler
- **Primary Deliverables**:
  - Mathematical problem formulation of the Job Shop Scheduling Problem ($S_{ij}$, $C_{ij}$, precedence, and non-overlap constraints).
  - Design of benchmark datasets (`jobs.csv`, `operations.csv`, `machines.csv`).
  - Implementation & mathematical verification of baseline dispatching heuristics (FCFS, SPT, EDD).
  - Definition and formulation of Key Performance Indicators (Makespan, Total Tardiness, Machine Utilization %, Idle Time).
  - Designing the experimental benchmarking plan and writing the Operations Management analysis in the final report.
- **Viva Defense Focus**: Mathematical constraints, dispatching rules logic, KPI definitions, and trade-offs between heuristic rules and metaheuristics.

---

### 👤 Member 2: Python Engine & Genetic Algorithm Optimization
**Role**: Lead Software & Algorithm Engineer
- **Primary Deliverables**:
  - Architecture and implementation of the Operation-Based Chromosome decoder (`src/scheduler/decoder.py`).
  - Core Genetic Algorithm operators: Tournament selection, Precedence Operation Crossover (POX), and Swap mutation (`src/genetic_algorithm/ga.py`).
  - Dynamic rescheduling engine and discrete-event simulation tracking operation states (WAITING, RUNNING, COMPLETED, PAUSED) (`src/simulation/engine.py`).
  - Automated testing suite (60 test cases covering validation, feasibility, and rescheduling) (`tests/test_scheduling.py`).
  - Streamlit dashboard user interface and Plotly Gantt chart visualizations (`app.py`, `src/metrics/visualization.py`).
- **Viva Defense Focus**: Chromosome decoding logic, how POX maintains feasibility, GA convergence behavior, and dynamic rescheduling state preservation.

---

### 👤 Member 3: Embedded Systems, Hardware & Integration
**Role**: Lead Embedded Systems & Physical Integration Engineer
- **Primary Deliverables**:
  - Bill of Materials (BOM) creation and component budget estimation (ESP32, LEDs, buttons, OLED, resistors).
  - Breadboard layout design, circuit schematic creation, and electrical wiring (handling active-LOW buttons and pull-up resistors on GPIO 34-36).
  - ESP32 C++ firmware development with debounced button polling, non-blocking LED indicators, and OLED status display (`firmware/esp32_controller/`).
  - Robust newline-delimited JSON serial communication protocol between ESP32 and Python (`src/hardware/serial_comm.py`).
  - Demonstration setup, physical hardware testing, and physical breakdown fault injection demo.
- **Viva Defense Focus**: Hardware schematic, why external pull-ups are required on ESP32 GPI pins, serial JSON message framing, and cyber-physical synchronization.

---

## 2. Integrated Milestone Timeline

```
Week 1: Problem Formulation, Dataset Design & Initial Architecture (All Members)
        ├── Member 1: Formulates constraints & prepares default CSV datasets.
        ├── Member 2: Sets up Python repository, data validation & decoder models.
        └── Member 3: Finalizes BOM, acquires components & configures Arduino IDE.

Week 2: Algorithm Implementation & Firmware Prototyping
        ├── Member 1: Implements FCFS, SPT, EDD dispatching simulation.
        ├── Member 2: Implements Genetic Algorithm (POX crossover, swap mutation, elitism).
        └── Member 3: Builds breadboard circuit & writes basic ESP32 firmware.

Week 3: Rescheduling Simulation & Serial Integration
        ├── Member 1: Tests metrics calculation & comparative KPI tables.
        ├── Member 2: Develops dynamic rescheduling engine & interactive dashboard.
        └── Member 3: Implements JSON serial protocol & integrates hardware buttons with Python.

Week 4: Automated Testing, Experiments & Final Presentation Prep (All Members)
        ├── Member 1: Runs experiments, exports CSVs & writes analysis chapter.
        ├── Member 2: Executes automated test suite & finalizes documentation.
        └── Member 3: Tests end-to-end hardware demo & prepares presentation slides.
```
