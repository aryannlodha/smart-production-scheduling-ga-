"""
Baseline dispatching rules for the Job Shop Scheduling Problem.

Implements FCFS (First Come First Served), SPT (Shortest Processing Time),
and EDD (Earliest Due Date) as feasible multi-machine dispatching policies.

These are *dispatching* policies — at each decision point, the policy
selects which eligible operation to schedule next on a machine.

Implementation approach
-----------------------
We use a time-stepping dispatch simulation:
  1. Maintain a set of eligible operations (whose predecessor is done).
  2. At each step, for each idle machine, pick the best eligible op
     according to the dispatching rule.
  3. Advance time to the next completion event, freeing machines and
     unlocking successor operations.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Tuple

from src.scheduler.models import (
    ProblemInstance,
    Schedule,
    ScheduledOperation,
    Operation,
)


def _dispatching_simulation(
    problem: ProblemInstance,
    priority_key: Callable[
        [Operation, ProblemInstance, float], Tuple
    ],
    method_name: str,
    completed_ops: Optional[Dict[Tuple[str, int], ScheduledOperation]] = None,
    machine_available_times: Optional[Dict[str, float]] = None,
    job_available_times: Optional[Dict[str, float]] = None,
) -> Schedule:
    """Core dispatching simulation engine.

    Args:
        problem: The JSSP problem instance.
        priority_key: A function (operation, problem, current_time) -> tuple
            used to sort eligible operations.  Lower tuple = higher priority.
        method_name: Label for the scheduling method.
        completed_ops: Pre-completed operations (for rescheduling).
        machine_available_times: When each machine becomes free.
        job_available_times: When each job's next op can start.

    Returns:
        A feasible Schedule.
    """
    t_start = time.perf_counter()

    if completed_ops is None:
        completed_ops = {}

    # Track which operations are done
    done: Dict[Tuple[str, int], ScheduledOperation] = dict(completed_ops)

    # Determine next operation index for each job
    next_op_idx: Dict[str, int] = {}
    for jid, job in problem.jobs.items():
        found = False
        for i, op in enumerate(job.operations):
            if (op.job_id, op.operation_no) not in done:
                next_op_idx[jid] = i
                found = True
                break
        if not found:
            next_op_idx[jid] = job.num_operations  # All done

    # Machine available times
    m_avail: Dict[str, float] = {}
    for mid, machine in problem.machines.items():
        if machine_available_times and mid in machine_available_times:
            m_avail[mid] = machine_available_times[mid]
        else:
            m_avail[mid] = machine.initial_available_time

    # Job available times (from completed ops)
    j_avail: Dict[str, float] = {}
    for jid, job in problem.jobs.items():
        if job_available_times and jid in job_available_times:
            j_avail[jid] = job_available_times[jid]
        else:
            completed_for_job = [
                c for (j, _), c in done.items() if j == jid
            ]
            if completed_for_job:
                j_avail[jid] = max(c.completion_time for c in completed_for_job)
            else:
                j_avail[jid] = job.release_time

    # Track which machine is busy until when, and what's running
    m_busy_until: Dict[str, float] = {mid: m_avail[mid] for mid in problem.machines}

    scheduled: List[ScheduledOperation] = list(completed_ops.values())

    total_remaining = problem.total_operations - len(done)

    while len(scheduled) - len(completed_ops) < total_remaining:
        # Find eligible operations
        eligible: List[Operation] = []
        for jid, job in problem.jobs.items():
            idx = next_op_idx.get(jid, job.num_operations)
            if idx < job.num_operations:
                op = job.operations[idx]
                eligible.append(op)

        if not eligible:
            break  # Should not happen if problem is well-formed

        # For each idle machine, find the best eligible op
        # First, find the earliest time something can happen
        current_time = float("inf")
        for op in eligible:
            ready = max(m_busy_until[op.machine_id], j_avail[op.job_id])
            # Respect unavailability
            ready = _adjust_for_unavailability(
                ready, op.processing_time, op.machine_id,
                problem.machine_unavailability
            )
            current_time = min(current_time, ready)

        # Collect ops that can start at or soon after current_time
        # For each machine, pick the best eligible op that targets it
        scheduled_this_step = False
        machines_considered = set()

        for op in sorted(eligible, key=lambda o: priority_key(o, problem, current_time)):
            mid = op.machine_id
            if mid in machines_considered:
                continue

            ready = max(m_busy_until[mid], j_avail[op.job_id])
            ready = _adjust_for_unavailability(
                ready, op.processing_time, mid,
                problem.machine_unavailability
            )

            # Schedule this op
            start = ready
            completion = start + op.processing_time

            sop = ScheduledOperation(
                job_id=op.job_id,
                operation_no=op.operation_no,
                machine_id=op.machine_id,
                processing_time=op.processing_time,
                start_time=start,
                completion_time=completion,
            )
            scheduled.append(sop)
            done[(op.job_id, op.operation_no)] = sop

            m_busy_until[mid] = completion
            j_avail[op.job_id] = completion
            next_op_idx[op.job_id] = next_op_idx[op.job_id] + 1
            machines_considered.add(mid)
            scheduled_this_step = True

        if not scheduled_this_step:
            # Advance time to the next machine completion
            min_free = min(m_busy_until.values())
            for mid in m_busy_until:
                if m_busy_until[mid] <= min_free:
                    m_busy_until[mid] = min_free
            # Safety: prevent infinite loop
            break

    t_end = time.perf_counter()

    return Schedule(
        operations=scheduled,
        method=method_name,
        computation_time=t_end - t_start,
    )


def _adjust_for_unavailability(
    desired_start: float,
    processing_time: float,
    machine_id: str,
    unavailability: List[Tuple[str, float, float]],
) -> float:
    """Shift start time past any machine unavailability intervals."""
    start = desired_start
    intervals = sorted(
        [(s, e) for mid, s, e in unavailability if mid == machine_id],
        key=lambda x: x[0],
    )
    changed = True
    while changed:
        changed = False
        for iv_s, iv_e in intervals:
            if start < iv_e and (start + processing_time) > iv_s:
                start = iv_e
                changed = True
    return start


# ---------------------------------------------------------------------------
# FCFS — First Come, First Served
# ---------------------------------------------------------------------------
# Tie-breaker: job with lower ID (lexicographic) is served first.
# "First come" here means the operation whose job became available earliest
# (based on release time or completion of predecessor).


def _fcfs_key(
    op: Operation, problem: ProblemInstance, current_time: float
) -> Tuple:
    """FCFS priority: job release time, then job_id for tie-breaking."""
    job = problem.jobs[op.job_id]
    return (job.release_time, op.job_id, op.operation_no)


def schedule_fcfs(
    problem: ProblemInstance,
    completed_ops: Optional[Dict[Tuple[str, int], ScheduledOperation]] = None,
    machine_available_times: Optional[Dict[str, float]] = None,
    job_available_times: Optional[Dict[str, float]] = None,
) -> Schedule:
    """Schedule using First Come First Served dispatching."""
    return _dispatching_simulation(
        problem, _fcfs_key, "FCFS",
        completed_ops, machine_available_times, job_available_times,
    )


# ---------------------------------------------------------------------------
# SPT — Shortest Processing Time
# ---------------------------------------------------------------------------


def _spt_key(
    op: Operation, problem: ProblemInstance, current_time: float
) -> Tuple:
    """SPT priority: shortest processing time first, then job_id."""
    return (op.processing_time, op.job_id, op.operation_no)


def schedule_spt(
    problem: ProblemInstance,
    completed_ops: Optional[Dict[Tuple[str, int], ScheduledOperation]] = None,
    machine_available_times: Optional[Dict[str, float]] = None,
    job_available_times: Optional[Dict[str, float]] = None,
) -> Schedule:
    """Schedule using Shortest Processing Time dispatching."""
    return _dispatching_simulation(
        problem, _spt_key, "SPT",
        completed_ops, machine_available_times, job_available_times,
    )


# ---------------------------------------------------------------------------
# EDD — Earliest Due Date
# ---------------------------------------------------------------------------


def _edd_key(
    op: Operation, problem: ProblemInstance, current_time: float
) -> Tuple:
    """EDD priority: earliest due date first, then job_id."""
    job = problem.jobs[op.job_id]
    return (job.due_date, op.job_id, op.operation_no)


def schedule_edd(
    problem: ProblemInstance,
    completed_ops: Optional[Dict[Tuple[str, int], ScheduledOperation]] = None,
    machine_available_times: Optional[Dict[str, float]] = None,
    job_available_times: Optional[Dict[str, float]] = None,
) -> Schedule:
    """Schedule using Earliest Due Date dispatching."""
    return _dispatching_simulation(
        problem, _edd_key, "EDD",
        completed_ops, machine_available_times, job_available_times,
    )
