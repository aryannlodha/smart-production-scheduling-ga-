# Literature Review & Theoretical Foundation

## 1. Classical Job Shop Scheduling (JSSP)

Production scheduling is an essential decision-making process in manufacturing systems that allocates scarce production resources (machines, workstations, tooling) to incoming jobs over time to achieve specific operational objectives (Pinedo, 2016).

The **Job Shop Scheduling Problem (JSSP)** is classified as strongly **NP-hard** (Garey, Johnson & Sethi, 1976). Unlike the simpler Flow Shop Scheduling Problem where all jobs visit machines in the identical sequence, each job in a JSSP possesses its own distinct technological route. For an instance with $n$ jobs and $m$ machines where each job requires $m$ operations, the total search space comprises:
$$(n!)^m \text{ possible active schedules}$$

For even a small instance of 8 jobs and 3 machines, the theoretical search space spans $(8!)^3 \approx 6.5 \times 10^{13}$ permutations, making exact mathematical programming methods (such as Mixed-Integer Linear Programming or Branch-and-Bound) computationally prohibitive for rapid real-time scheduling.

---

## 2. Priority Dispatching Heuristics

In industrial practice, shop floor controllers historically rely on priority dispatching rules due to their instantaneous computation speed and operational simplicity (Haupt, 1989; Panwalkar & Iskander, 1977):
- **First-Come, First-Served (FCFS)**: Jobs are processed in order of their arrival into the shop or buffer. While perceived as equitable, FCFS frequently produces long queues and excessive makespan.
- **Shortest Processing Time (SPT)**: Selects the waiting operation with the smallest processing duration. Baker (1974) proved that SPT mathematically minimizes mean flow time and mean work-in-process (WIP) inventory in single-machine systems, though it tends to create severe delays for longer jobs in multi-machine networks.
- **Earliest Due Date (EDD)**: Prioritizes operations belonging to jobs with the earliest delivery deadline. Jackson (1955) demonstrated that EDD minimizes the maximum lateness ($L_{\max}$) in single-machine settings.

In multi-stage Job Shops, however, myopic dispatching rules evaluate only local conditions and struggle to balance global workflow, often resulting in prolonged machine idle time and elevated makespan.

---

## 3. Genetic Algorithms in Production Scheduling

To overcome the myopic limitations of dispatching rules, metaheuristics have gained widespread adoption. Holland (1975) and Goldberg (1989) formulated the foundational theory of Genetic Algorithms (GAs).

Key theoretical milestones for JSSP include:
- **Chromosome Representation**: Early approaches using binary encoding or direct job permutations struggled with constraint feasibility. Cheng, Gen & Tsujimura (1996, 1999) and Gen & Cheng (1997) established the **Operation-Based Representation**. By encoding a chromosome where each job ID appears exactly as many times as its total operation count, every gene permutation represents a technologically feasible schedule upon sequential decoding.
- **Genetic Operators**: Bierwirth (1995) introduced Precedence Preserving Crossover (PPX), and Shi et al. (2006) refined Precedence Operation Crossover (POX), ensuring offspring inherit valid precedence relationships without requiring repair heuristics.

---

## 4. Dynamic Rescheduling & Disruptions

Real-world manufacturing environments are inherently non-deterministic. Shop floors are subject to unexpected disturbances, including machine breakdowns, urgent job arrivals, and processing delays (Vieira, Herrmann & Lin, 2003; Ouelhadj & Petrovic, 2009).

Dynamic scheduling strategies are broadly divided into:
1. **Completely Reactive Scheduling**: No forward plan is maintained; decisions are made exclusively in real time via dispatching rules.
2. **Predictive-Reactive Scheduling**: An optimized baseline schedule is generated initially. When a disruption occurs, a rescheduling policy is triggered:
   - *Right-Shift Rescheduling*: Shifts remaining operations forward by the breakdown duration. While fast, it ignores opportunities to resequence unaffected jobs.
   - *Regenerative (Partial/Complete) Rescheduling*: Freezes all historically completed operations and actively running operations on unaffected machines, while using a metaheuristic (such as GA) to re-optimize all remaining pending operations.

Our system adopts **Predictive-Reactive Regenerative Rescheduling**, preserving historical integrity while re-optimizing pending tasks.

---

## 5. Cyber-Physical Production Systems (CPPS) & Demonstration Scope

Recent literature in Industry 4.0 underscores the integration of computational algorithms with physical shop floor hardware—termed Cyber-Physical Systems (CPS) (Monostori, 2014; Lee, Bagheri & Kao, 2015).

### Academic Project Contribution Scope
- **What is Established**: The JSSP mathematical formulation, the Genetic Algorithm metaheuristic, dispatching rules, and breakdown rescheduling concepts are well-documented in published literature.
- **Our Project's Contribution**: The contribution of this undergraduate PBL project lies in the **tangible, hands-on integration**:
  1. Implementing a verified, transparent Python scheduling and rescheduling engine from scratch (without black-box solvers).
  2. Providing a transparent, direct quantitative comparison against standard dispatching baselines (FCFS, SPT, EDD).
  3. Building a physical, low-cost embedded hardware demonstration prototype (ESP32) that allows students and evaluators to press a physical fault button, watch machine indicator LEDs react in real time, and observe cyber-physical dynamic rescheduling in action.
