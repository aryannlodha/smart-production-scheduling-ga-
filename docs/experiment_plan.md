# Experimental Analysis & Benchmarking Plan

## 1. Experimental Objectives

To fulfill the rigorous Operations Management evaluation criteria, the project conducts three systematic experiments:
1. **Experiment 1 (Static Benchmarking)**: Quantitative comparison of the Genetic Algorithm against classic dispatching heuristics (FCFS, SPT, EDD) on the standard 8-job, 3-machine instance.
2. **Experiment 2 (Stochastic Sensitivity & GA Convergence)**: Evaluation of GA stability, convergence variance, and runtime across 10 distinct random seeds.
3. **Experiment 3 (Dynamic Disturbance & Rescheduling)**: Evaluation of system resilience and rescheduling efficiency across machine failure scenarios ($M_1, M_2, M_3$) at early ($t=5$), mid ($t=10$), and late ($t=15$) production stages.

---

## 2. Automated Experiment Runner

The project includes an automated scriptable experiment pipeline in `src/metrics/experiments.py`:

```python
from src.metrics.experiments import (
    export_breakdown_csv,
    export_ga_seeds_csv,
    export_results_csv,
    run_all_methods,
    run_breakdown_experiment,
    run_ga_multiple_seeds,
)
from src.scheduler.models import load_problem_from_csv

# 1. Load problem
problem = load_problem_from_csv(
    "data/jobs.csv", "data/operations.csv", "data/machines.csv"
)

# 2. Run static benchmark comparison
results = run_all_methods(problem)
export_results_csv(results, "data/benchmark_results.csv")

# 3. Run multi-seed GA stability analysis
ga_runs = run_ga_multiple_seeds(problem, base_config, seeds=list(range(1, 11)))
export_ga_seeds_csv(ga_runs, "data/ga_seed_results.csv")

# 4. Run breakdown scenarios
scenarios = [
    run_breakdown_experiment(
        problem, initial_sched, "M1", breakdown_time=10.0, repair_duration=8.0
    ),
    run_breakdown_experiment(
        problem, initial_sched, "M2", breakdown_time=10.0, repair_duration=8.0
    ),
    run_breakdown_experiment(
        problem, initial_sched, "M3", breakdown_time=10.0, repair_duration=8.0
    ),
]
export_breakdown_csv(scenarios, "data/breakdown_results.csv")
```

---

## 3. Metrics Recorded for Every Scenario

1. **Makespan ($C_{\max}$)**: Time of completion of the final operation in the shop.
2. **Total Tardiness ($T = \sum \max(0, C_i - D_i)$)**: Sum of delivery delays beyond specified due dates.
3. **Average Machine Utilization ($\bar{U}$)**: Percentage of active processing time relative to net available capacity.
4. **Total Machine Idle Time**: Cumulative non-productive idle intervals across all workstations.
5. **Computation Time ($t_{\text{calc}}$)**: Wall-clock CPU time required to solve the schedule or compute the revised schedule.
6. **Recovery Delta ($\Delta C_{\max}$)**: Percentage increase in makespan caused by the breakdown and repair window:
   $$\Delta C_{\max} = \frac{C_{\max}^{\text{revised}} - C_{\max}^{\text{original}}}{C_{\max}^{\text{original}}} \times 100\%$$

---

## 4. Reporting Guidelines for Viva and Presentation

- **No Fabricated Data**: Always report actual numbers output by the algorithms.
- **Objective Trade-off Discussion**:
  - Dispatching rules (SPT, EDD, FCFS) compute instantly ($< 0.005$ seconds) but frequently produce sub-optimal makespans and higher idle time.
  - Genetic Algorithm explores a broader solution space, typically achieving tighter makespan and higher machine utilization, requiring a small computational investment (~0.2 to 1.5 seconds).
  - In dynamic environments, reactive GA rescheduling balances plan quality with prompt recovery.
