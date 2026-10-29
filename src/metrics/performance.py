"""
Performance metrics for production schedules.

Calculates:
  - Makespan (C_max)
  - Total tardiness
  - Machine utilization (%)
  - Machine idle time
  - Per-job completion times and tardiness
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from src.scheduler.models import ProblemInstance, Schedule, ScheduledOperation


@dataclass
class MachineMetrics:
    """Metrics for a single machine."""
    machine_id: str
    busy_time: float = 0.0
    idle_time: float = 0.0
    unavailable_time: float = 0.0
    utilization_pct: float = 0.0
    num_operations: int = 0


@dataclass
class JobMetrics:
    """Metrics for a single job."""
    job_id: str
    completion_time: float = 0.0
    due_date: float = 0.0
    tardiness: float = 0.0
    flow_time: float = 0.0
    num_operations: int = 0


@dataclass
class ScheduleMetrics:
    """Aggregate metrics for a complete schedule."""
    method: str = ""
    makespan: float = 0.0
    total_tardiness: float = 0.0
    avg_tardiness: float = 0.0
    max_tardiness: float = 0.0
    num_tardy_jobs: int = 0
    avg_utilization_pct: float = 0.0
    total_idle_time: float = 0.0
    computation_time: float = 0.0
    machine_metrics: Dict[str, MachineMetrics] = field(default_factory=dict)
    job_metrics: Dict[str, JobMetrics] = field(default_factory=dict)


def calculate_metrics(
    schedule: Schedule,
    problem: ProblemInstance,
) -> ScheduleMetrics:
    """Calculate all performance metrics for a schedule.

    Machine Utilization formula:
        utilization = busy_time / available_time * 100
    where available_time = makespan - unavailable_time_within_makespan

    Machine Idle Time:
        idle_time = available_time - busy_time

    Total Tardiness:
        T = sum_i max(0, C_i - D_i)
    where C_i = completion time of job i's last operation,
          D_i = due date of job i.
    """
    metrics = ScheduleMetrics(
        method=schedule.method,
        computation_time=schedule.computation_time,
    )

    if not schedule.operations:
        return metrics

    # --- Makespan ---
    metrics.makespan = max(op.completion_time for op in schedule.operations)

    # --- Job metrics ---
    for job_id, job in problem.jobs.items():
        job_ops = schedule.get_job_schedule(job_id)
        if not job_ops:
            continue
        completion = max(op.completion_time for op in job_ops)
        tardiness = max(0.0, completion - job.due_date)

        jm = JobMetrics(
            job_id=job_id,
            completion_time=completion,
            due_date=job.due_date,
            tardiness=tardiness,
            flow_time=completion - job.release_time,
            num_operations=len(job_ops),
        )
        metrics.job_metrics[job_id] = jm

    metrics.total_tardiness = sum(
        jm.tardiness for jm in metrics.job_metrics.values()
    )
    n_jobs = len(metrics.job_metrics)
    metrics.avg_tardiness = (
        metrics.total_tardiness / n_jobs if n_jobs > 0 else 0.0
    )
    metrics.max_tardiness = (
        max(jm.tardiness for jm in metrics.job_metrics.values())
        if metrics.job_metrics else 0.0
    )
    metrics.num_tardy_jobs = sum(
        1 for jm in metrics.job_metrics.values() if jm.tardiness > 0
    )

    # --- Machine metrics ---
    for mid in problem.machine_ids:
        machine_ops = schedule.get_machine_schedule(mid)
        busy_time = sum(op.processing_time for op in machine_ops)

        # Calculate unavailable time within the makespan
        unavail_time = 0.0
        for umid, us, ue in problem.machine_unavailability:
            if umid == mid:
                # Clip to [0, makespan]
                clipped_start = max(0.0, us)
                clipped_end = min(metrics.makespan, ue)
                if clipped_end > clipped_start:
                    unavail_time += clipped_end - clipped_start

        available_time = metrics.makespan - unavail_time
        idle_time = max(0.0, available_time - busy_time)
        utilization = (
            (busy_time / available_time * 100.0) if available_time > 0 else 0.0
        )

        mm = MachineMetrics(
            machine_id=mid,
            busy_time=busy_time,
            idle_time=idle_time,
            unavailable_time=unavail_time,
            utilization_pct=utilization,
            num_operations=len(machine_ops),
        )
        metrics.machine_metrics[mid] = mm

    # Average utilization
    if metrics.machine_metrics:
        metrics.avg_utilization_pct = sum(
            mm.utilization_pct for mm in metrics.machine_metrics.values()
        ) / len(metrics.machine_metrics)
        metrics.total_idle_time = sum(
            mm.idle_time for mm in metrics.machine_metrics.values()
        )

    return metrics


def compare_schedules(
    schedules: List[Schedule],
    problem: ProblemInstance,
) -> List[ScheduleMetrics]:
    """Calculate metrics for multiple schedules and return them for comparison."""
    return [calculate_metrics(s, problem) for s in schedules]


def format_comparison_table(
    metrics_list: List[ScheduleMetrics],
) -> str:
    """Format a comparison table as a readable string."""
    if not metrics_list:
        return "No schedules to compare."

    header = (
        f"{'Method':<10} {'Makespan':>10} {'Tardiness':>10} "
        f"{'Avg Util%':>10} {'Idle Time':>10} {'Comp Time':>12}"
    )
    sep = "-" * len(header)
    lines = [header, sep]

    for m in metrics_list:
        lines.append(
            f"{m.method:<10} {m.makespan:>10.1f} {m.total_tardiness:>10.1f} "
            f"{m.avg_utilization_pct:>9.1f}% {m.total_idle_time:>10.1f} "
            f"{m.computation_time:>11.4f}s"
        )

    return "\n".join(lines)
