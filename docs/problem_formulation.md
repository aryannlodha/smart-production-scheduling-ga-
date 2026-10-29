# Mathematical Problem Formulation

## 1. Classical Job Shop Scheduling Problem (JSSP)

The classical Job Shop Scheduling Problem (JSSP) is an NP-hard combinatorial optimization problem widely studied in Operations Research and Industrial Engineering.

In our production system:
- A set of $n$ jobs $\mathcal{J} = \{J_1, J_2, \dots, J_n\}$ must be processed on a set of $m$ machines $\mathcal{M} = \{M_1, M_2, \dots, M_m\}$.
- Each job $J_i$ consists of a predetermined sequence of $n_i$ operations:
  $$\mathcal{O}_i = (O_{i,1}, O_{i,2}, \dots, O_{i,n_i})$$
- Operation $O_{i,j}$ represents the $j$-th operation in the technological route of job $J_i$.
- Each operation $O_{i,j}$ requires processing on a designated machine $\mu(O_{i,j}) \in \mathcal{M}$ for an uninterrupted duration $p_{i,j} > 0$.

---

## 2. Decision Variables

For each operation $O_{i,j}$:
- $S_{i,j} \ge 0$: Start time of operation $O_{i,j}$.
- $C_{i,j} \ge 0$: Completion time of operation $O_{i,j}$.

Relationship:
$$C_{i,j} = S_{i,j} + p_{i,j}$$

For each job $J_i$, its overall completion time is:
$$C_i = C_{i,n_i}$$

---

## 3. System Constraints

### 3.1 Job Precedence Constraints
An operation cannot begin until its immediate predecessor in the job's route is completely finished:
$$S_{i,j+1} \ge C_{i,j} \quad \forall i \in \{1,\dots,n\}, \; \forall j \in \{1,\dots,n_i - 1\}$$

Job release times:
$$S_{i,1} \ge r_i \quad \forall i \in \{1,\dots,n\}$$
where $r_i \ge 0$ is the release (arrival) date of job $J_i$ (defaulted to $0$).

### 3.2 Machine Exclusivity (Capacity) Constraints
A machine can process at most one operation at any given instant. For any pair of distinct operations $O_{i,j}$ and $O_{k,l}$ assigned to the same machine ($\mu(O_{i,j}) = \mu(O_{k,l})$):
$$S_{i,j} \ge C_{k,l} \quad \text{OR} \quad S_{k,l} \ge C_{i,j}$$

### 3.3 Non-Preemption Under Normal Operation
Once an operation begins processing on a healthy machine, it cannot be interrupted or suspended.

### 3.4 Machine Unavailability & Breakdown Constraint
If machine $M_k$ experiences downtime during the simulated interval $[t_{\text{break}}, t_{\text{repair}})$, no operation may be processed on $M_k$ during this window:
$$\text{If } \mu(O_{i,j}) = M_k, \quad [S_{i,j}, C_{i,j}) \cap [t_{\text{break}}, t_{\text{repair}}) = \emptyset$$

---

## 4. Objective Function

The primary objective of the initial schedule is to **minimize the Makespan** ($C_{\max}$), which is the total completion time of the entire batch of jobs:

$$\min C_{\max} = \max_{i \in \{1,\dots,n\}} C_i$$

---

## 5. Secondary Key Performance Indicators (KPIs)

While $C_{\max}$ is the single optimization fitness criterion in the Genetic Algorithm, the following secondary operational metrics are monitored and reported:

### 5.1 Total Job Tardiness ($T$)
Given job due dates $D_i$:
$$L_i = C_i - D_i \quad (\text{Job Latency})$$
$$T_i = \max(0, C_i - D_i) \quad (\text{Job Tardiness})$$
$$T = \sum_{i=1}^n T_i = \sum_{i=1}^n \max(0, C_i - D_i)$$

### 5.2 Machine Utilization ($\%$)
For each machine $M_k$, given total busy processing time $B_k = \sum_{O_{i,j} \in \mathcal{O}(M_k)} p_{i,j}$ and total downtime $Downtime_k$ within the makespan horizon $[0, C_{\max}]$:
$$AvailableTime_k = C_{\max} - Downtime_k$$
$$Utilization_k = \left( \frac{B_k}{AvailableTime_k} \right) \times 100\%$$
$$\bar{U} = \frac{1}{m} \sum_{k=1}^m Utilization_k$$

### 5.3 Machine Idle Time
$$IdleTime_k = AvailableTime_k - B_k$$
$$TotalIdleTime = \sum_{k=1}^m IdleTime_k$$

---

## 6. Default Project Instance

- **Workstations**: 3 machines ($M_1, M_2, M_3$)
- **Batch Size**: 8 jobs ($J_1 \dots J_8$)
- **Total Operations**: 18 distinct operations
- **Technological Routes**:
  - $J_1$: $M_1 (5) \to M_2 (4) \to M_3 (6)$
  - $J_2$: $M_1 (3) \to M_3 (7)$
  - $J_3$: $M_2 (6) \to M_3 (4)$
  - $J_4$: $M_1 (4) \to M_2 (5) \to M_3 (3)$
  - $J_5$: $M_1 (7) \to M_3 (5)$
  - $J_6$: $M_2 (3) \to M_3 (6)$
  - $J_7$: $M_1 (6) \to M_2 (4)$
  - $J_8$: $M_1 (5) \to M_3 (4)$
