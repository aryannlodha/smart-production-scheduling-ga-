"""
Experiment runner for reproducible scheduling experiments.

Runs FCFS, SPT, EDD, and GA on the same problem instances,
records metrics, and exports CSV results.
"""

from __future__ import annotations

import csv
import os
import time
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from src.scheduler.models import ProblemInstance, Schedule, ScheduledOperation
from src.scheduler.decoder import decode_chromosome, validate_schedule
from src.genetic_algorithm.ga import GAConfig, GAResult, run_genetic_algorithm
from src.baselines.dispatching import schedule_fcfs, schedule_spt, schedule_edd
from src.metrics.performance import calculate_metrics, ScheduleMetrics
from src.simulation.engine import (
    ProductionSimulator,
    InterruptionPolicy,
    BreakdownEvent,
)


def run_all_methods(
    problem: ProblemInstance,
    ga_config: Optional[GAConfig] = None,
    completed_ops: Optional[Dict[Tuple[str, int], ScheduledOperation]] = None,
    machine_available_times: Optional[Dict[str, float]] = None,
    job_available_times: Optional[Dict[str, float]] = None,
) -> Dict[str, Tuple[Schedule, ScheduleMetrics]]:
    """Run FCFS, SPT, EDD, and GA on the same problem instance.

    Returns a dict mapping method name -> (schedule, metrics).
    """
    if ga_config is None:
        ga_config = GAConfig()

    results = {}

    # FCFS
    sched_fcfs = schedule_fcfs(
        problem, completed_ops, machine_available_times, job_available_times
    )
    metrics_fcfs = calculate_metrics(sched_fcfs, problem)
    results["FCFS"] = (sched_fcfs, metrics_fcfs)

    # SPT
    sched_spt = schedule_spt(
        problem, completed_ops, machine_available_times, job_available_times
    )
    metrics_spt = calculate_metrics(sched_spt, problem)
    results["SPT"] = (sched_spt, metrics_spt)

    # EDD
    sched_edd = schedule_edd(
        problem, completed_ops, machine_available_times, job_available_times
    )
    metrics_edd = calculate_metrics(sched_edd, problem)
    results["EDD"] = (sched_edd, metrics_edd)

    # GA
    ga_result = run_genetic_algorithm(
        problem, ga_config, completed_ops,
        machine_available_times, job_available_times,
    )
    metrics_ga = calculate_metrics(ga_result.best_schedule, problem)
    results["GA"] = (ga_result.best_schedule, metrics_ga)

    return results


def run_ga_multiple_seeds(
    problem: ProblemInstance,
    base_config: GAConfig,
    seeds: List[int],
) -> List[GAResult]:
    """Run GA with multiple random seeds for statistical analysis."""
    results = []
    for seed in seeds:
        config = GAConfig(
            population_size=base_config.population_size,
            max_generations=base_config.max_generations,
            crossover_prob=base_config.crossover_prob,
            mutation_prob=base_config.mutation_prob,
            elite_count=base_config.elite_count,
            tournament_size=base_config.tournament_size,
            random_seed=seed,
        )
        result = run_genetic_algorithm(problem, config)
        results.append(result)
    return results


def run_breakdown_experiment(
    problem: ProblemInstance,
    initial_schedule: Schedule,
    machine_id: str,
    breakdown_time: float,
    repair_duration: float,
    ga_config: Optional[GAConfig] = None,
    interruption_policy: InterruptionPolicy = InterruptionPolicy.RESUME,
) -> Dict:
    """Run a complete breakdown experiment.

    Returns a dict with:
      - original_metrics
      - revised_metrics
      - makespan_change_pct
      - rescheduling_time
      - breakdown_event
      - affected_operations
      - completed_at_breakdown
    """
    sim = ProductionSimulator(
        problem, initial_schedule, interruption_policy
    )

    # Advance to breakdown time
    sim.advance_to(breakdown_time)

    completed_before = sim.get_completed_ops_list()
    running_before = sim.get_running_ops_list()
    waiting_before = sim.get_waiting_ops_list()

    # Trigger breakdown
    event = sim.trigger_breakdown(machine_id, repair_duration, breakdown_time)

    paused = sim.get_paused_ops_list()

    # Reschedule
    t_start = time.perf_counter()
    revised = sim.reschedule(
        method="GA",
        ga_config=ga_config or GAConfig(max_generations=50, population_size=80),
    )
    rescheduling_time = time.perf_counter() - t_start

    original_metrics = sim.state.original_metrics
    revised_metrics = sim.state.revised_metrics

    original_makespan = original_metrics.makespan if original_metrics else 0
    revised_makespan = revised_metrics.makespan if revised_metrics else 0
    change_pct = (
        ((revised_makespan - original_makespan) / original_makespan * 100)
        if original_makespan > 0
        else 0
    )

    return {
        "breakdown_event": event,
        "original_metrics": original_metrics,
        "revised_metrics": revised_metrics,
        "original_makespan": original_makespan,
        "revised_makespan": revised_makespan,
        "makespan_change_pct": change_pct,
        "rescheduling_time": rescheduling_time,
        "completed_at_breakdown": completed_before,
        "running_at_breakdown": running_before,
        "waiting_at_breakdown": waiting_before,
        "paused_operations": paused,
        "original_schedule": sim.state.original_schedule,
        "revised_schedule": revised,
    }


def export_results_csv(
    results: Dict[str, Tuple[Schedule, ScheduleMetrics]],
    output_path: str,
) -> None:
    """Export comparison results to CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    rows = []
    for method, (schedule, metrics) in results.items():
        row = {
            "method": method,
            "makespan": metrics.makespan,
            "total_tardiness": metrics.total_tardiness,
            "avg_tardiness": metrics.avg_tardiness,
            "max_tardiness": metrics.max_tardiness,
            "num_tardy_jobs": metrics.num_tardy_jobs,
            "avg_utilization_pct": metrics.avg_utilization_pct,
            "total_idle_time": metrics.total_idle_time,
            "computation_time_s": metrics.computation_time,
        }
        # Per-machine metrics
        for mid, mm in sorted(metrics.machine_metrics.items()):
            row[f"{mid}_busy"] = mm.busy_time
            row[f"{mid}_idle"] = mm.idle_time
            row[f"{mid}_util_pct"] = mm.utilization_pct

        rows.append(row)

    if rows:
        fieldnames = list(rows[0].keys())
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def export_ga_seeds_csv(
    results: List[GAResult],
    output_path: str,
) -> None:
    """Export multi-seed GA results to CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    rows = []
    for i, r in enumerate(results):
        rows.append({
            "run": i + 1,
            "seed": r.config.random_seed,
            "best_makespan": r.best_fitness,
            "generations": r.generations_run,
            "computation_time_s": r.computation_time,
        })

    if rows:
        fieldnames = list(rows[0].keys())
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def export_breakdown_csv(
    experiments: List[Dict],
    output_path: str,
) -> None:
    """Export breakdown experiment results to CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    rows = []
    for exp in experiments:
        event = exp["breakdown_event"]
        rows.append({
            "machine": event.machine_id,
            "breakdown_time": event.breakdown_time,
            "repair_duration": event.repair_duration,
            "original_makespan": exp["original_makespan"],
            "revised_makespan": exp["revised_makespan"],
            "makespan_change_pct": exp["makespan_change_pct"],
            "rescheduling_time_s": exp["rescheduling_time"],
            "completed_ops_at_breakdown": len(exp["completed_at_breakdown"]),
            "paused_ops": len(exp["paused_operations"]),
        })

    if rows:
        fieldnames = list(rows[0].keys())
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
