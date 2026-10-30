# Final Presentation Outline & Viva Defense Scripts
## Smart Production Scheduling and Dynamic Rescheduling Using Genetic Algorithm: A Physical Prototype-Based Approach

*Undergraduate Project-Based Learning (PBL) Presentation Deck Structure & Speaking Scripts*

---

## ⏱️ Section 1: The 1-Minute Elevator Pitch

> *"Good morning, respected professors. In modern manufacturing, shop floor efficiency depends critically on scheduling complex jobs across multiple machines. However, traditional industry dispatching rules like First-Come First-Served (FCFS) or Shortest Processing Time (SPT) are myopic—they only make local decisions, causing high idle times and production bottlenecks.*
>
> *To solve this, our team developed an end-to-end cyber-physical production scheduling system. We modeled a multi-machine Job Shop Scheduling Problem and implemented a custom Genetic Algorithm using an Operation-Based Chromosome representation that mathematically guarantees 100% constraint feasibility. On our 8-job benchmark, our GA achieved a makespan of 38 hours—outperforming FCFS and SPT by up to 9.5% and reducing idle time by 25%.*
>
> *Crucially, when unexpected machine breakdowns strike, our system freezes completed history, pauses interrupted work, and dynamically reschedules all pending operations in under 0.3 seconds. We have coupled this Python optimization engine with a physical ESP32 breadboard prototype featuring workstation status LEDs, an OLED telemetry screen, and fault injection buttons—bringing smart Industry 4.0 scheduling into a tangible, physical demonstration. Thank you."*

---

## ⏱️ Section 2: The 5-Minute Full Viva Presentation Script

### Minute 1: Problem Definition & Operational Context
*"Good morning. Our project addresses a fundamental challenge in Operations Management: the Job Shop Scheduling Problem (JSSP). In high-mix, low-volume manufacturing, jobs possess distinct technological routes. With 8 jobs and 3 machines, the search space contains over 65 trillion combinations, making exhaustive search impossible.
Traditionally, factories rely on heuristic rules such as FCFS or SPT. While fast, they create severe shop floor imbalances. Furthermore, when a machine breaks down, static schedules collapse. Our objective was to develop an intelligent scheduling engine using a Genetic Algorithm, benchmark it against dispatching rules, simulate dynamic breakdown rescheduling, and demonstrate the process using a physical ESP32 control panel."*

### Minute 2: Mathematical Model & Chromosome Encoding
*"To solve JSSP, we formulated the hard constraints: operation durations, job precedence where operation $j+1$ cannot start before operation $j$ completes, and machine exclusivity. Our primary objective is minimizing Makespan ($C_{\max}$).
A central innovation of our software is the Operation-Based Chromosome representation. Rather than simply permuting job IDs, a job with $k$ operations appears exactly $k$ times. As our linear decoder reads left to right, the $n$-th occurrence corresponds to the $n$-th operation. Combined with Precedence Operation Crossover (POX) and swap mutation, this guarantees that every offspring produced by our GA is 100% technologically feasible without needing repair heuristics."*

### Minute 3: Quantitative Experimental Benchmarks
*"We conducted empirical benchmarking on an 8-job, 3-machine, 18-operation dataset. Comparing all four methods:
- FCFS achieved a makespan of 41.0 with 36 hours of machine idle time.
- SPT achieved 42.0 with job tardiness.
- Our Genetic Algorithm converged to a makespan of 38.0—a 7.3% to 9.5% improvement—while increasing average machine utilization from 69% to 76.3% and cutting idle time to 27 hours.
Multi-seed sensitivity testing across 10 random seeds confirmed rock-solid stability with a mean makespan of 38.0 and zero constraint violations across our 60-test automated verification suite."*

### Minute 4: Dynamic Rescheduling Under Breakdown
*"In real factories, disturbances occur. We built a discrete-event simulation tracking four distinct operation states: WAITING, RUNNING, COMPLETED, and PAUSED.
When a machine fails (for example, Machine 1 at virtual time $t=10$ with an 8-hour repair window), our engine automatically preserves all operations completed prior to $t=10$. Operations on unaffected machines continue. The interrupted operation is paused and resumes after repair with only its remaining processing time. The GA re-optimizes the pending workload in just 0.15 seconds, shifting the makespan from 38.0 to 42.0. This demonstrates reactive shop floor resilience."*

### Minute 5: Cyber-Physical Hardware Prototype & Demo
*"To bring this to life, we developed a physical demonstration panel using an ESP32 microcontroller connected via a newline-delimited JSON serial protocol over USB.
Each workstation has Green and Red status LEDs. Green indicates idle or busy, and Red indicates a breakdown. When an evaluator presses the physical M1 breakdown button on our breadboard, the ESP32 dispatches a fault event to Python, the scheduler recalculates the revised plan, and telemetry is reflected on our physical OLED display in real time. We will now demonstrate the live software dashboard and prototype. Thank you."*

---

## 📊 Section 3: Slide Deck Structure (10–12 Slides)

| Slide # | Slide Title | Visual Content & Diagrams | Focus Area |
|:-------:|-------------|---------------------------|:----------:|
| **1** | **Title Slide** | Project Title, Course, Project Details, Guide Name | Context |
| **2** | **Industrial Problem & Context** | High-mix Job Shop challenges; $(8!)^3$ combinatorial complexity graphic | Problem Definition |
| **3** | **Project Architecture & Scope** | Decoupled Architecture: Python Engine $\leftrightarrow$ USB JSON $\leftrightarrow$ ESP32 Prototype | System Architecture |
| **4** | **Mathematical Model & Constraints** | Formulas: $C_{ij} = S_{ij} + p_{ij}$; $S_{i,j+1} \ge C_{ij}$; $\min C_{\max}$; Tardiness & Utilization | Math & Formulation |
| **5** | **Genetic Algorithm Design** | Operation-Based Chromosome Diagram; POX Crossover Walkthrough | Algorithmic Logic |
| **6** | **Benchmarking Results (GA vs. FCFS/SPT/EDD)** | Quantitative Comparison Table (Makespan, Util %, Idle, CPU Time); Convergence Plot | Results & Analysis |
| **7** | **Gantt Chart Analysis** | Interactive Plotly Gantt Chart of 38.0 makespan baseline schedule | Schedule Visualization |
| **8** | **Dynamic Machine Breakdown Simulation** | Breakdown scenario at $t=10$: Paused, Preserved & Rescheduled Gantt Chart | Dynamic Simulation |
| **9** | **Physical Hardware Interface (ESP32)** | Circuit schematic; Breadboard photo; Pinout table; OLED status display | Hardware Prototype |
| **10** | **Serial Protocol & Cyber-Physical Sync** | Message Sequence Diagram (JSON payload format, event-response loop) | Communication Protocol |
| **11** | **Verification & Engineering Rigor** | Pytest 60/60 Green badge; Multi-seed statistical stability table | Testing & Quality |
| **12** | **Conclusion & Operational Impact** | Summary of contributions; Future work (FJSP, industrial sensors); Q&A | Wrap-Up |

---

## 🎯 Section 4: Technical Defense Focus Areas

- **Operations Research & Scheduling**:
  - Mathematical constraints, dispatching rules (FCFS, SPT, EDD), tardiness calculations, and capacity utilization metrics.
- **Software Architecture & Genetic Algorithms**:
  - Chromosome decoding, why POX maintains precedence validity, computational complexity, simulation states, and pytest test suite.
- **Embedded Hardware & Communications**:
  - Circuit wiring, why external pull-ups are required on GPIO 34-36, serial JSON protocol framing, ESP32 firmware loop, and power ratings.
