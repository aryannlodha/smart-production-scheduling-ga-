"""
Executable script to run all benchmark experiments and generate CSV exports.
"""

import os
import sys

# Ensure root directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scheduler.models import load_problem_from_csv
from src.genetic_algorithm.ga import GAConfig
from src.metrics.experiments import (
    run_all_methods,
    run_ga_multiple_seeds,
    run_breakdown_experiment,
    export_results_csv,
    export_ga_seeds_csv,
    export_breakdown_csv,
)

def main():
    print("=================================================================")
    print("   SMART PRODUCTION SCHEDULING — EXPERIMENTAL BENCHMARK RUNNER   ")
    print("=================================================================")

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    output_dir = os.path.join(data_dir, "experiments")
    os.makedirs(output_dir, exist_ok=True)

    jobs_csv = os.path.join(data_dir, "jobs.csv")
    ops_csv = os.path.join(data_dir, "operations.csv")
    machines_csv = os.path.join(data_dir, "machines.csv")

    print(f"\n[1/3] Loading problem dataset from {data_dir}...")
    problem = load_problem_from_csv(jobs_csv, ops_csv, machines_csv)
    print(f"      Loaded: {problem.num_jobs} jobs, {problem.num_machines} machines, {problem.total_operations} operations.")

    # 1. Run All Methods Comparison
    print("\n[2/3] Running static benchmark comparison (FCFS, SPT, EDD, GA)...")
    ga_config = GAConfig(
        population_size=100,
        max_generations=100,
        crossover_prob=0.8,
        mutation_prob=0.1,
        elite_count=2,
        tournament_size=5,
        random_seed=42,
    )
    results = run_all_methods(problem, ga_config=ga_config)

    print("\n  Summary of Static Results:")
    print(f"  {'Method':<10} | {'Makespan':<10} | {'Tardiness':<10} | {'Avg Util %':<10} | {'Idle Time':<10} | {'CPU Time (s)':<12}")
    print("  " + "-" * 75)
    for method, (sched, metrics) in results.items():
        print(f"  {method:<10} | {metrics.makespan:<10.1f} | {metrics.total_tardiness:<10.1f} | {metrics.avg_utilization_pct:<9.1f}% | {metrics.total_idle_time:<10.1f} | {metrics.computation_time:<12.4f}")

    benchmark_csv = os.path.join(output_dir, "benchmark_comparison.csv")
    export_results_csv(results, benchmark_csv)
    print(f"  -> Exported to: {benchmark_csv}")

    # 2. Run Multi-seed GA
    print("\n[3/3] Running GA across 10 random seeds (Seeds 1 to 10)...")
    seeds = list(range(1, 11))
    ga_seed_results = run_ga_multiple_seeds(problem, ga_config, seeds)
    makespans = [r.best_fitness for r in ga_seed_results]
    mean_makespan = sum(makespans) / len(makespans)
    min_makespan = min(makespans)
    max_makespan = max(makespans)
    print(f"  Multi-seed GA Results (10 runs): Best={min_makespan:.1f}, Worst={max_makespan:.1f}, Mean={mean_makespan:.2f}")

    ga_seeds_csv = os.path.join(output_dir, "ga_seeds_analysis.csv")
    export_ga_seeds_csv(ga_seed_results, ga_seeds_csv)
    print(f"  -> Exported to: {ga_seeds_csv}")

    # 3. Run Breakdown Scenarios
    print("\n[4/4] Running dynamic breakdown scenarios (M1, M2, M3 failure at t=10, repair=8)...")
    best_initial_schedule = results["GA"][0]
    breakdown_experiments = []

    for mid in problem.machine_ids:
        exp = run_breakdown_experiment(
            problem=problem,
            initial_schedule=best_initial_schedule,
            machine_id=mid,
            breakdown_time=10.0,
            repair_duration=8.0,
            ga_config=GAConfig(population_size=80, max_generations=50, random_seed=42),
        )
        breakdown_experiments.append(exp)
        print(f"  Breakdown {mid} at t=10.0 (repair 8.0): Orig Cmax={exp['original_makespan']:.1f} -> Rev Cmax={exp['revised_makespan']:.1f} (+{exp['makespan_change_pct']:.1f}%) [Rescheduled in {exp['rescheduling_time']:.3f}s]")

    breakdown_csv = os.path.join(output_dir, "breakdown_experiments.csv")
    export_breakdown_csv(breakdown_experiments, breakdown_csv)
    print(f"  -> Exported to: {breakdown_csv}")

    print("\n=================================================================")
    print("   ALL EXPERIMENTS COMPLETE & CSV DATASETS PERSISTED TO DISK    ")
    print("=================================================================")

if __name__ == "__main__":
    main()
