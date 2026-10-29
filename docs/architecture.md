# System Architecture

## 1. Executive Summary

This project implements a cyber-physical production scheduling and dynamic rescheduling system for a Job Shop Scheduling Problem (JSSP). The architecture cleanly decouples the heavy combinatorial optimization engine (running on Python on the host PC) from the physical production control interface (an ESP32 microcontroller with physical buttons, machine-status LEDs, and an OLED display).

```
+-----------------------------------------------------------------------------------+
|                                  HOST PC (Python)                                 |
|                                                                                   |
|  +------------------------+  +------------------------+  +---------------------+  |
|  |     Data Layer         |  |   Scheduling Engine    |  |  Metrics & Eval     |  |
|  | - jobs.csv             |  | - JSSP Decoder         |  | - Makespan (Cmax)   |  |
|  | - operations.csv       |  | - Baselines (FCFS/SPT) |  | - Total Tardiness   |  |
|  | - machines.csv         |  | - Genetic Algorithm    |  | - Machine Util /    |  |
|  | - Data validator       |  | - Rescheduling Engine  |  |   Idle Time         |  |
|  +------------------------+  +------------------------+  +---------------------+  |
|               |                           |                         |             |
|               +---------------------------+-------------------------+             |
|                                           |                                       |
|                               +-----------------------+                           |
|                               |  Streamlit Dashboard  |                           |
|                               |  (Web User Interface) |                           |
|                               +-----------------------+                           |
|                                           |                                       |
|                               +-----------------------+                           |
|                               | ESP32 Serial Handler  |                           |
|                               | (src/hardware/)       |                           |
|                               +-----------------------+                           |
+-------------------------------------------|---------------------------------------+
                                            | USB Serial (115200 Baud, JSON)
+-------------------------------------------|---------------------------------------+
|                                    ESP32 DEV BOARD                                |
|                                                                                   |
|  +------------------------+  +------------------------+  +---------------------+  |
|  |  Physical Inputs       |  |  State Management      |  |  Visual Feedback    |  |
|  | - Start Button (D32)   |  | - Machine States       |  | - M1-M3 Status LEDs |  |
|  | - Reset Button (D33)   |  |   (IDLE / BUSY / DOWN) |  | - SSD1306 OLED      |  |
|  | - M1 Break Button (D34)|  | - Non-blocking Timers  |  |   (Real-time State) |  |
|  | - M2 Break Button (D35)|  | - Serial Parser/Writer |  |                     |  |
|  | - M3 Break Button (D36)|  |                        |  |                     |  |
|  +------------------------+  +------------------------+  +---------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Component Breakdown

### Component A: Production Scheduling Engine (`src/scheduler/` & `src/baselines/`)
- **`src/scheduler/models.py`**: Immutable dataclasses representing `Job`, `Operation`, `Machine`, `ScheduledOperation`, and `ProblemInstance`. Includes complete validation of precedence Contiguity, positive durations, and machine existence.
- **`src/scheduler/decoder.py`**: Deterministic schedule builder that converts an operation-based chromosome into start times $S_{ij}$ and completion times $C_{ij}$ while enforcing machine non-overlap, job precedence, and downtime intervals.
- **`src/baselines/dispatching.py`**: Production-standard dynamic dispatching policies:
  - **FCFS** (First-Come, First-Served)
  - **SPT** (Shortest Processing Time)
  - **EDD** (Earliest Due Date)

### Component B: Genetic Algorithm & Dynamic Rescheduler (`src/genetic_algorithm/` & `src/simulation/`)
- **`src/genetic_algorithm/ga.py`**:
  - Operation-based chromosome encoding.
  - Precedence Operation Crossover (POX).
  - Swap mutation.
  - Elitism and Tournament selection.
  - Makespan minimization fitness function.
- **`src/simulation/engine.py`**:
  - Virtual clock advancement.
  - Tracking discrete states: `WAITING`, `RUNNING`, `COMPLETED`, `PAUSED`.
  - Machine breakdown injection.
  - Preservation of completed operations and ongoing unaffected operations.
  - Dynamic rescheduling triggered upon failure.

### Component C: Physical Production-Control Prototype (`firmware/` & `src/hardware/`)
- **`firmware/esp32_controller/esp32_controller.ino`**:
  - Arduino C++ firmware running on ESP32 DevKit V1.
  - Debounced push-button inputs for factory control and fault injection.
  - Dual-color status LEDs per workstation (Green = Normal/Active, Red = Machine Down).
  - I2C OLED display for live simulation metrics.
- **`src/hardware/serial_comm.py`**:
  - Background asynchronous serial worker thread.
  - Robust newline-delimited JSON messaging.
  - Seamless fallback to software-only simulation mode if the physical microcontroller is disconnected.

---

## 3. Data Flow and Inter-Module Communication

1. **Input Phase**: User loads or edits `jobs.csv`, `operations.csv`, `machines.csv` via the Streamlit GUI or file system.
2. **Initial Optimization**:
   - Baseline dispatchers run synchronously to generate comparative benchmark schedules.
   - Genetic Algorithm evolves population over $N$ generations to discover a near-optimal schedule minimizing $C_{\max}$.
3. **Execution & Simulation**:
   - The virtual clock advances. Operations transition from `WAITING` $\to$ `RUNNING` $\to$ `COMPLETED`.
   - Serial messages stream machine state updates to the ESP32 to update physical LEDs and the OLED display.
4. **Disturbance & Dynamic Rescheduling**:
   - An event occurs (either via the physical breakdown push-button or dashboard click).
   - The engine halts the target machine, pauses any operation in progress, freezes already-completed operations, and invokes the GA rescheduler with remaining workload.
   - The revised schedule is generated, validated, and pushed both to the Gantt chart display and the ESP32 controller.
