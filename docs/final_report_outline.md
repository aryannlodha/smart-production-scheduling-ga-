# Final Academic Project Report Outline
## Smart Production Scheduling and Dynamic Rescheduling Using Genetic Algorithm: A Physical Prototype-Based Approach

*Undergraduate Project-Based Learning (PBL) Report Structure — Department of Industrial Engineering and Management (IEM)*

---

### Cover Page & Front Matter
- **Title**: Smart Production Scheduling and Dynamic Rescheduling Using Genetic Algorithm: A Physical Prototype-Based Approach
- **Course**: Operations Management / Production Planning and Control (PBL)
- **Author / Project Details**: [Project Submission Details]
- **Supervisor / Project Guide**: [Professor / Faculty Advisor Name]
- **Department & Institution**: Department of Industrial Engineering & Management, [University Name]
- **Date / Academic Year**: [Academic Year 2025–2026]
- **Certificate of Originality & Supervisor Sign-off**
- **Acknowledgements**
- **Executive Abstract**: Problem background, JSSP formulation, GA optimization, baseline heuristics, dynamic breakdown handling, physical ESP32 prototype, and quantitative findings.
- **Table of Contents, List of Figures, List of Tables, Nomenclature & Abbreviations**

---

### Chapter 1: Introduction
- **1.1 Background & Context**: Production scheduling in manufacturing systems; challenges of high-mix, low-volume shop floors.
- **1.2 Industrial Problem Statement**: NP-hard combinatorial nature of Job Shop Scheduling; limitations of static scheduling in volatile environments prone to unexpected equipment failures.
- **1.3 Project Objectives**:
  - Formulate a mathematically verified JSSP model.
  - Implement and benchmark dispatching heuristics (FCFS, SPT, EDD) vs. a metaheuristic Genetic Algorithm.
  - Design a predictive-reactive dynamic rescheduler for machine breakdowns.
  - Develop a cyber-physical prototype utilizing an ESP32 microcontroller with LED and OLED telemetry.
- **1.4 Scope & Delimitations**: Focus on deterministic processing times and fixed technological routes; demonstration-scale prototype rather than factory-wide automation.

---

### Chapter 2: Literature Review & Theoretical Framework
- **2.1 Classical Job Shop Scheduling Problem (JSSP)**: Mathematical complexity ($O((n!)^m)$); non-polynomial hard classification.
- **2.2 Priority Dispatching Heuristics**: Mechanistic logic, merits, and myopic pitfalls of FCFS, SPT (Baker's theorem), and EDD (Jackson's rule).
- **2.3 Metaheuristic Optimization via Genetic Algorithms**:
  - Foundational principles (Holland, 1975; Goldberg, 1989).
  - Chromosome representations: Direct job permutations vs. Operation-Based Encoding (Gen & Cheng, 1997; Cheng et al., 1996, 1999).
  - Precedence-preserving crossover operators: POX (Shi et al., 2006).
- **2.4 Dynamic Rescheduling under Disruptions**: Predictive-reactive strategies; right-shift rescheduling vs. regenerative re-optimization (Vieira et al., 2003; Ouelhadj & Petrovic, 2009).
- **2.5 Cyber-Physical Production Systems (CPPS)**: Industry 4.0 principles, hardware-in-the-loop simulation, and physical demonstration interfaces.
- **2.6 Research Scope & Academic Contribution**: Hands-on integration of transparent Python scheduling logic with accessible micro-embedded hardware.

---

### Chapter 3: Mathematical Modeling & Problem Formulation
- **3.1 Problem Definition & Parameters**: Sets of jobs ($\mathcal{J}$), machines ($\mathcal{M}$), technological routes ($\mathcal{O}_i$), processing durations ($p_{ij}$), and due dates ($D_i$).
- **3.2 Decision Variables**: Operation start times ($S_{ij}$) and finish times ($C_{ij}$).
- **3.3 Hard Constraints**:
  - Operation duration: $C_{ij} = S_{ij} + p_{ij}$
  - Job precedence: $S_{i,j+1} \ge C_{ij}$
  - Machine capacity exclusivity: Disjunctive non-overlap constraints.
  - Machine breakdown intervals: Unavailability intervals $[t_{\text{break}}, t_{\text{repair}})$.
- **3.4 Primary Objective Function**: Makespan minimization ($\min C_{\max} = \max C_i$).
- **3.5 Secondary Key Performance Indicators**:
  - Total Job Tardiness ($T = \sum \max(0, C_i - D_i)$).
  - Machine Utilization Percentage ($U_k = B_k / (C_{\max} - Downtime_k) \times 100\%$).
  - Machine Idle Time ($Idle_k = (C_{\max} - Downtime_k) - B_k$).
- **3.6 Benchmark Dataset**: Technical specifications of the 8-job, 3-machine, 18-operation dataset.

---

### Chapter 4: System Architecture & Software Implementation
- **4.1 System Overview & Modular Architecture**: Data Layer, Scheduling Engine, Simulation Layer, Metrics & Visualization, Hardware Communications.
- **4.2 Schedule Decoder Engine**: Linear scanning algorithm, tracking earliest machine and job availability, and handling downtime intervals.
- **4.3 Priority Dispatching Simulator**: Multi-machine event-driven simulation of FCFS, SPT, and EDD policies.
- **4.4 Genetic Algorithm Engine**:
  - Chromosome representation walkthrough.
  - Tournament selection ($k=5$).
  - Precedence Operation Crossover (POX) algorithm step-by-step.
  - Swap mutation and elitism preservation.
- **4.5 Dynamic Rescheduling & Virtual-Clock Simulation**:
  - State machine: `WAITING`, `RUNNING`, `COMPLETED`, `PAUSED`.
  - Disturbance injection, historical operation freezing, and partial rescheduling.
  - Interruption policies: `RESUME` vs. `RESTART`.
- **4.6 Interactive Web Dashboard**: Multi-page Streamlit UI, Plotly Gantt charts, and user controls.

---

### Chapter 5: Embedded Hardware Prototype & Integration
- **5.1 Architecture & Hardware-in-the-Loop Concept**: Decoupled design; Python host engine and ESP32 peripheral interface.
- **5.2 Bill of Materials (BOM) & Budget Analysis**: Component selection, Indian cost breakdown (~₹1,150–₹1,450 INR), and vendor sourcing.
- **5.3 Electrical Circuit Design**:
  - Schematic and breadboard layout.
  - Dual-LED workstation status indicators (Active-HIGH with 220Ω limiting resistors).
  - Tactile push buttons (Internal pull-ups for GPIO 32/33; External 10kΩ pull-ups for input-only GPIO 34/35/36).
  - SSD1306 0.96" I2C OLED display wiring.
- **5.4 Firmware Implementation**: Arduino C++ loop, button debouncing, non-blocking LED blinking, and JSON serialization.
- **5.5 Serial Communication Protocol**: Newline-delimited JSON format, event definitions (`STARTUP`, `BREAKDOWN`, `STATUS_UPDATE`), and fault-tolerant parsing.

---

### Chapter 6: Experimental Results & Comparative Discussion
- **6.1 Static Scheduling Benchmarks**:
  - Tabular comparison: Makespan, Tardiness, Utilization, Idle Time, Computation Time.
  - Analysis: GA ($C_{\max} = 38.0$) vs. FCFS ($41.0$) vs. SPT ($42.0$) vs. EDD ($42.0$).
  - Operational discussion: Why local heuristics produce higher idle time (25% higher idle time than GA).
- **6.2 Genetic Algorithm Convergence & Stability**:
  - Multi-seed analysis (10 random seeds); mean makespan ($38.0$) and standard deviation.
  - Generation-by-generation fitness improvement curve.
- **6.3 Machine Breakdown & Rescheduling Performance**:
  - Failure scenarios on $M_1$, $M_2$, and $M_3$ at $t=10.0$ with 8.0-unit repair duration.
  - Resilience analysis: Bottleneck sensitivity (M1: +10.5%, M2: +0.0%, M3: +21.1%).
  - Real-time response: Rescheduling execution time ($< 0.3$ seconds).
- **6.4 Verification & Validation**: 60-test pytest suite results confirming zero constraint violations.

---

### Chapter 7: Conclusions, Reflections & Future Work
- **7.1 Project Conclusions**: Synthesis of findings; validation of GA metaheuristic and physical demonstration concept.
- **7.2 Engineering Implementation Review**: Synthesis of mathematical modeling, algorithmic optimization, and hardware integration.
- **7.3 Operational Limitations**: Assumptions regarding deterministic processing and fixed routing.
- **7.4 Future Recommendations**: Extension to Flexible Job Shop Scheduling ($FJSP$), automated machine sensor feedback, and reinforcement learning reschedulers.

---

### References & Appendices
- **Academic References**: Formal citations (Pinedo, Baker, Gen & Cheng, Vieira, etc.).
- **Appendix A**: Complete Python Source Code Listing.
- **Appendix B**: ESP32 C++ Firmware Code Listing.
- **Appendix C**: Benchmark Datasets (`jobs.csv`, `operations.csv`, `machines.csv`).
- **Appendix D**: Full Experimental Output CSV Tables.
- **Appendix E**: Circuit Schematics and Breadboard Wiring Photographs.
