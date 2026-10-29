# Genetic Algorithm: Theory, Design, and Implementation

## 1. What is a Genetic Algorithm?

A Genetic Algorithm (GA) is an adaptive metaheuristic search technique inspired by Charles Darwin's theory of natural selection and biological evolution. It is especially suited for solving complex, non-linear, and discrete combinatorial optimization problems—such as the Job Shop Scheduling Problem (JSSP)—where exhaustive enumeration is computationally intractable.

A candidate solution is encoded as a **chromosome**. A set of chromosomes forms a **population**. Over successive **generations**, genetic operators (**selection**, **crossover**, **mutation**) combine and perturb high-performing individuals (measured by a **fitness function**), driving the population toward superior schedules.

> **Important Metaheuristic Distinction:** A Genetic Algorithm is a stochastic metaheuristic. It explores the search space efficiently to identify high-quality, near-optimal solutions in reasonable computational time. It does **not** mathematically guarantee discovering the global theoretical minimum.

---

## 2. Chromosome Encoding: Operation-Based Representation

A critical challenge in applying GAs to JSSP is ensuring that genetic operators generate feasible schedules that respect technological precedence constraints.

We adopt the widely recognized **Operation-Based Chromosome Representation** (Gen & Cheng, 1997; Cheng, Gen & Tsujimura, 1996, 1999).

### Structure:
- Each job $J_i$ with $n_i$ operations appears in the chromosome **exactly $n_i$ times**.
- Total chromosome length equals the total number of operations:
  $$L = \sum_{i=1}^n n_i$$
- When scanning the chromosome from left to right, the $k$-th occurrence of gene symbol $J_i$ unambiguously represents the $k$-th operation ($O_{i,k}$) of job $J_i$.

### Concrete Walkthrough Example:
Consider 3 jobs:
- $J_1$: 3 operations ($O_{1,1}, O_{1,2}, O_{1,3}$)
- $J_2$: 2 operations ($O_{2,1}, O_{2,2}$)
- $J_3$: 2 operations ($O_{3,1}, O_{3,2}$)

Chromosome:
`['J1', 'J2', 'J3', 'J1', 'J3', 'J2', 'J1']`

Decoding sequence:
1. `J1` (1st appearance) $\to$ Operation $O_{1,1}$
2. `J2` (1st appearance) $\to$ Operation $O_{2,1}$
3. `J3` (1st appearance) $\to$ Operation $O_{3,1}$
4. `J1` (2nd appearance) $\to$ Operation $O_{1,2}$ (Guaranteed to follow $O_{1,1}$)
5. `J3` (2nd appearance) $\to$ Operation $O_{3,2}$ (Guaranteed to follow $O_{3,1}$)
6. `J2` (2nd appearance) $\to$ Operation $O_{2,2}$ (Guaranteed to follow $O_{2,1}$)
7. `J1` (3rd appearance) $\to$ Operation $O_{1,3}$ (Guaranteed to follow $O_{1,2}$)

**Why this representation is ideal:** Any arbitrary permutation of this gene multiset automatically satisfies job precedence constraints! Precedence violations are mathematically impossible under this representation.

---

## 3. Schedule Decoding Engine

The decoder (`src/scheduler/decoder.py`) converts the decoded operation sequence into an active schedule:
1. Track the current earliest availability time for each machine ($m\_avail[M]$) and each job ($j\_avail[J]$).
2. For each gene in the chromosome:
   - Identify the specific operation $O_{i,j}$ and its designated machine $\mu(O_{i,j})$.
   - Calculate candidate start time:
     $$S_{candidate} = \max(m\_avail[\mu(O_{i,j})], j\_avail[J_i])$$
   - Shift $S_{candidate}$ forward if it collides with any known downtime/unavailability interval on that machine.
   - Assign $S_{i,j} = S_{candidate}$, and $C_{i,j} = S_{i,j} + p_{i,j}$.
   - Update availability:
     $$m\_avail[\mu(O_{i,j})] = C_{i,j}, \quad j\_avail[J_i] = C_{i,j}$$

---

## 4. Genetic Operators

### 4.1 Selection: Tournament Selection
- Randomly draw $k$ candidate chromosomes from the population (default $k=5$).
- Select the individual with the best (lowest) makespan fitness.
- High selection pressure towards fit solutions while maintaining population diversity.

### 4.2 Crossover: Precedence Operation Crossover (POX)
Standard 1-point or 2-point crossovers disrupt the exact gene counts required by the operation-based representation. We use **Precedence Operation Crossover (POX)**:
1. Randomly partition the set of job IDs into two disjoint subsets, $\mathcal{J}_1$ and $\mathcal{J}_2$ (e.g., $\mathcal{J}_1 = \{J_1, J_4, J_7\}$, $\mathcal{J}_2 = \{J_2, J_3, J_5, J_6, J_8\}$).
2. To create **Child 1**:
   - Copy all genes belonging to $\mathcal{J}_1$ from **Parent 1** directly into Child 1 at their exact positions.
   - Fill the remaining unoccupied positions with genes belonging to $\mathcal{J}_2$ copied from **Parent 2** in the exact sequential order they appear in Parent 2.
3. To create **Child 2**:
   - Reverse the parent roles (copy $\mathcal{J}_1$ from Parent 2; fill remaining with $\mathcal{J}_2$ from Parent 1).

**Benefit:** Preserves the operation count of every job and respects parental sub-sequences without producing invalid offspring.

### 4.3 Mutation: Swap Mutation
- Two distinct gene positions $i$ and $j$ are chosen uniformly at random.
- The genes at positions $i$ and $j$ are swapped.
- Because swapping does not change the frequency of any job ID, the mutated chromosome remains 100% valid.

### 4.4 Elitism
- In each generation, the top $E$ best-performing individuals (default $E=2$) are cloned directly into the subsequent generation without modification.
- Prevents the loss of the best found solution due to stochastic crossover or mutation disruption.

---

## 5. Configuration & Hyperparameters

| Parameter | Default Value | Role / Justification |
|-----------|---------------|----------------------|
| Population Size ($N$) | 100 | Balances solution diversity with evaluation speed on standard laptops |
| Maximum Generations ($G$) | 100 | Sufficient for convergence on standard 8-job benchmarks |
| Crossover Probability ($P_c$) | 0.80 | High exploration of structural combinations |
| Mutation Probability ($P_m$) | 0.10 | Moderate perturbation to prevent premature convergence |
| Elite Count ($E$) | 2 | Preserves the best solution found so far |
| Tournament Size ($k$) | 5 | Balanced selection pressure |
| Random Seed | 42 (configurable) | Guarantees exact reproducibility across experimental runs |
