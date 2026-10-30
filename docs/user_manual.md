# User Manual & Step-by-Step Demonstration Guide

## 1. Introduction

This manual provides complete instructions for running and demonstrating the **Smart Production Scheduling and Dynamic Rescheduling System**. The application can be operated either in **Full Hardware-in-the-Loop Mode** (with ESP32 connected) or in **Software-Only Demonstration Mode** (using only the laptop).

---

## 2. Navigating the Dashboard Pages

Run the application:
```powershell
streamlit run app.py
```

### Page 1: 📋 Production Inputs
1. Click **"📂 Load Default Data"** to load the standard 8-job, 3-machine benchmark problem.
2. Review the editable tables:
   - **Jobs**: Job IDs, release times, due dates.
   - **Operations**: Step-by-step technological routes ($M_1, M_2, M_3$) and processing times.
   - **Machines**: Machine IDs and initial available times.
3. Click **"✅ Validate & Build Problem"**. The system checks:
   - Contiguous operation numbering (1, 2, ...).
   - Valid machine references.
   - Positive processing times ($p_{ij} > 0$).
   - Absence of duplicate operations.
4. You will see a summary confirmation: `8 jobs, 3 machines, 18 operations`.

---

### Page 2: ⚙️ Scheduling
1. Review or tune the Genetic Algorithm hyperparameters (Default: Population = 100, Generations = 100, Crossover = 0.8, Mutation = 0.1, Seed = 42).
2. Click **"🚀 Run All Methods"** to execute:
   - **FCFS** (First-Come, First-Served)
   - **SPT** (Shortest Processing Time)
   - **EDD** (Earliest Due Date)
   - **GA** (Genetic Algorithm with live generation progress bar)
3. The dashboard executes all four algorithms and prints their respective makespan and calculation times.

---

### Page 3: 📊 Results & KPIs
1. **Performance Comparison Table**: Compares Makespan ($C_{\max}$), Total Tardiness ($T$), Average Utilization (%), Total Idle Time, and Computation Time across all 4 rules.
2. **Machine Utilization Breakdown**: Details busy time, idle time, and utilization percentage for each machine ($M_1, M_2, M_3$).
3. **Job Tardiness Table**: Displays completion times and tardiness for every individual job relative to its committed due date.
4. **GA Convergence Graph**: Plotly curve demonstrating how makespan improves across generations.
5. **CSV Export**: Click "📥 Download comparison.csv" to export the quantitative experimental data for project report inclusion.

---

### Page 4: 📈 Gantt Chart
1. Select any scheduling method from the dropdown menu to inspect its interactive Gantt chart.
2. Hover over any operation block to inspect:
   - Job ID and Operation Number.
   - Assigned Machine.
   - Start Time ($S_{ij}$) and Completion Time ($C_{ij}$).
   - Operation Processing Duration.
3. Use the **"Compare Two Schedules"** feature at the bottom to inspect the side-by-side Gantt charts of the GA schedule against FCFS or SPT.

---

### Page 5: 🔧 Dynamic Rescheduling (Breakdown Simulation)
This is the core evaluation scenario:
1. Select the baseline schedule (e.g., `GA`).
2. Configure the breakdown event:
   - **Machine to Fail**: Choose $M_1$, $M_2$, or $M_3$ (e.g., $M_1$).
   - **Breakdown Time**: Choose when the failure occurs (e.g., $t = 10.0$).
   - **Repair Duration**: Choose downtime length (e.g., $8.0$ time units; machine unavailable from $t=10$ to $t=18$).
   - **Interruption Policy**: `RESUME` (preserves work done; resumes with remaining time after repair).
3. Click **"🚀 Run Breakdown Simulation"**:
   - The simulation clock freezes at $t = 10.0$.
   - The dashboard reports operations completed prior to breakdown, operations currently running on other machines, and operations paused.
   - The engine locks $M_1$ as unavailable until $t = 18.0$.
   - The Genetic Algorithm re-optimizes the remaining pending work without altering historical operations.
   - The revised Gantt chart is displayed, showing the hatched red breakdown interval and the rescheduled operations.
   - A KPI delta table shows the exact percentage impact on makespan and tardiness.

---

### Page 6: 🔌 Hardware Status
1. **Connect**: Select the serial COM port for your ESP32 and click **"🔗 Connect"**.
2. **Status Indicator**: Confirms `CONNECTED` status.
3. **Real-time Synchronization**:
   - Machine status (Idle/Busy/Down) displays both on screen and on the physical LEDs.
   - Pressing the physical breakdown buttons on the breadboard immediately triggers the breakdown and rescheduling workflow in Python!
