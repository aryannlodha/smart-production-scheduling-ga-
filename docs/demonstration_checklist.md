# Demonstration Checklist for Professor Evaluation

This checklist provides a structured, fail-safe guide for the 3-member team to demonstrate the **Smart Production Scheduling & Dynamic Rescheduling System** during lab assessments, viva examinations, and project evaluations.

---

## 1. Pre-Demonstration Setup Checklist (15 Minutes Before Evaluation)

### 💻 Laptop & Environment
- [ ] Laptop charger plugged in (prevents CPU throttling during GA optimization).
- [ ] Terminal opened in project root: `cd "c:\Users\aryan\Desktop\Classroom\Projects\OM PBL"`.
- [ ] Virtual environment activated: `.\venv\Scripts\Activate.ps1`.
- [ ] Test suite verified green: `pytest tests/ -v` (confirm 60/60 tests pass).
- [ ] Streamlit dashboard launched: `streamlit run app.py` (running on `http://localhost:8501`).
- [ ] Browser window zoomed to 100% or 110% for clear projection / viewing.

### 🔌 Physical Prototype (If Demonstrating with ESP32)
- [ ] Micro-USB data cable firmly seated between ESP32 DevKit and laptop.
- [ ] Device Manager verified: ESP32 COM port identified (e.g., `COM3`).
- [ ] Arduino IDE Serial Monitor closed (prevents `PermissionError: Port Busy`).
- [ ] Breadboard power rail verified (Red wire on 3V3, Blue wire on GND).
- [ ] All 6 LEDs visually checked (none loose).
- [ ] On Dashboard Page 6 ("Hardware Status"), select COM port and click **Connect** (Indicator turns 🟢 `CONNECTED`).

### 🛡️ Software-Only Fallback Plan
- [ ] If no hardware is available or a cable fails, inform the evaluator: *"Our system features automatic decoupling. We will demonstrate the dynamic scheduling and breakdown behavior in Software-Only Mode via the web dashboard."*

---

## 2. Live Step-by-Step Demonstration Script (5-Minute Viva Flow)

| Step | Dashboard Page | Action | What to Explain to Professor |
|:---:|:--------------:|--------|-----------------------------|
| **1** | **Page 1: Production Inputs** | 1. Click **"📂 Load Default Data"**.<br>2. Click **"✅ Validate & Build Problem"**. | *"We have formulated a classical fixed-route Job Shop Scheduling Problem (JSSP) with 8 jobs, 3 machines, and 18 operations. Every operation has strict job precedence ($S_{i,j+1} \ge C_{ij}$) and machine exclusivity."* |
| **2** | **Page 2: Scheduling** | 1. Show GA Hyperparameters (Pop=100, Gen=100, Cx=0.8, Mut=0.1).<br>2. Click **"🚀 Run All Methods"**. | *"We benchmark our Genetic Algorithm against standard industry dispatching rules: FCFS, SPT, and EDD. The GA uses an Operation-Based Chromosome with Precedence Operation Crossover (POX) to explore global combinations without generating invalid sequences."* |
| **3** | **Page 3: Results & KPIs** | 1. Point to the Comparison Table.<br>2. Scroll down to GA Convergence curve. | *"Notice the quantitative results: FCFS yields a makespan of 41.0, SPT yields 42.0 with tardiness, while GA finds an optimal schedule of 38.0 time units (7.3% to 9.5% improvement). Average machine utilization increases from 69% to 76.3%, and idle time drops by 25%."* |
| **4** | **Page 4: Gantt Chart** | 1. Select `GA` from dropdown.<br>2. Hover over machine bars. | *"Here is the interactive Gantt chart. Each color represents a job. Notice that operations on each machine never overlap, and operation sequences strictly honor technological routing."* |
| **5** | **Page 5: Dynamic Rescheduling** | 1. Select Machine `M1`, Breakdown Time `t = 10.0`, Repair Duration `8.0`.<br>2. Click **"🚀 Run Breakdown Simulation"** (or press physical M1 button on ESP32). | *"This is our core contribution: Cyber-Physical Dynamic Rescheduling. At t=10, Machine 1 experiences an unexpected failure. Completed operations prior to t=10 are permanently frozen. Running operations on unaffected machines continue. The interrupted operation pauses and resumes with remaining time. The GA recalculates the remaining workload in just 0.15 seconds, shifting makespan from 38.0 to 42.0."* |
| **6** | **Page 6: Hardware Status** | 1. Show live state sync.<br>2. Press Start/Reset/Fault buttons. | *"Our ESP32 controller mirrors shop floor machine states using Green (Normal/Busy) and Red (Down) LEDs and an OLED screen, communicating with Python via a newline-delimited JSON protocol."* |

---

## 3. Anticipated Viva Questions & Model Answers

### Q1: "Why did you use an Operation-Based Chromosome instead of a simple job permutation?"
> **Answer**: *"A simple permutation of job IDs cannot represent multi-stage jobs where operations must follow an exact sequence across different machines. In our operation-based representation, a job with $k$ operations appears exactly $k$ times in the chromosome. When decoded sequentially from left to right, the $n$-th appearance of job $J_i$ is mapped to its $n$-th technological operation. This mathematically guarantees that job precedence is 100% preserved without needing penalty functions or repair heuristics."*

### Q2: "Can you prove that your Genetic Algorithm guarantees the global optimal schedule?"
> **Answer**: *"No. A Genetic Algorithm is a stochastic metaheuristic designed for NP-hard problems where finding the absolute global optimum via exhaustive search would require evaluating $(n!)^m \approx 6.5 \times 10^{13}$ schedules. GA efficiently searches the space to deliver near-optimal solutions in sub-second CPU time (~0.5s), which is essential for real-time industrial rescheduling."*

### Q3: "What happens to in-progress operations when a machine breaks down?"
> **Answer**: *"Our system implements a configurable interruption policy. By default, it uses `RESUME`: the running operation is paused, its elapsed processing time is recorded, and upon machine repair it resumes with only its remaining duration. Operations running on unaffected machines continue uninterrupted, and completed operations are preserved in the revised schedule."*

### Q4: "Why run Python on the PC instead of running the GA directly inside the ESP32?"
> **Answer**: *"Combinatorial optimization on populations of 100 individuals across 100 generations involves significant memory allocation and floating-point computations. The ESP32 is an embedded microcontroller optimized for real-time I/O, button debouncing, and indicator driving. Decoupling the scheduling brain (Python) from the physical interface (ESP32) reflects realistic Industry 4.0 Cyber-Physical System (CPS) architecture."*

---

## 4. Post-Demonstration Wrap-Up
- [ ] Export latest benchmark CSVs from Dashboard or `run_experiments.py`.
- [ ] Cleanly disconnect serial port using the **"Disconnect"** button on Page 6.
- [ ] Save any screenshots of comparative Gantt charts for report appendix.
