"""
Schedule decoder: converts a chromosome (operation sequence) into a
feasible Job Shop schedule that respects job-precedence constraints,
machine-capacity constraints, and machine-unavailability intervals.

Chromosome representation
-------------------------
An operation-based chromosome is a permutation of operation tokens.
Each job J with *k* operations appears exactly *k* times in the
chromosome.  The decoder reads the chromosome left to right; the
*n*-th occurrence of job J is decoded as the *n*-th operation of
that job.

Example (3 jobs, J1 has 3 ops, J2 has 2 ops, J3 has 2 ops):
    chromosome = ['J1', 'J2', 'J3', 'J1', 'J3', 'J2', 'J1']
    1st 'J1' → J1-Op1
    1st 'J2' → J2-Op1
    1st 'J3' → J3-Op1
    2nd 'J1' → J1-Op2
    2nd 'J3' → J3-Op2
    1st 'J2' → wait, that was already handled … actually:
    2nd 'J2' → J2-Op2   (this is the 2nd appearance)
    3rd 'J1' → J1-Op3

This guarantees job-precedence because earlier operations of a job
are always decoded before later ones.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.scheduler.models import (
    Operation,
    ProblemInstance,
    Schedule,
    ScheduledOperation,
)


def _earliest_start_respecting_unavailability(
    desired_start: float,
    processing_time: float,
    machine_id: str,
    unavailability: List[Tuple[str, float, float]],
) -> float:
    """Find the earliest start time >= desired_start such that the
    operation [start, start + processing_time) does not overlap any
    unavailability interval for the given machine.
    """
    start = desired_start
    # Filter to this machine's intervals, sorted by start
    intervals = sorted(
        [(s, e) for mid, s, e in unavailability if mid == machine_id],
        key=lambda x: x[0],
    )
    # Iteratively push start past any overlapping interval
    changed = True
    while changed:
        changed = False
        for iv_start, iv_end in intervals:
            op_end = start + processing_time
            # Check overlap: [start, op_end) ∩ [iv_start, iv_end) != ∅
            if start < iv_end and op_end > iv_start:
                # Push start to after the unavailability interval
                start = iv_end
                changed = True
    return start


def decode_chromosome(
    chromosome: List[str],
    problem: ProblemInstance,
    completed_ops: Optional[Dict[Tuple[str, int], ScheduledOperation]] = None,
    machine_available_times: Optional[Dict[str, float]] = None,
    job_available_times: Optional[Dict[str, float]] = None,
) -> Schedule:
    """Decode an operation-based chromosome into a feasible schedule.

    Args:
        chromosome: List of job IDs representing the operation sequence.
            Each job appears as many times as it has operations.
        problem: The JSSP problem instance.
        completed_ops: Operations already completed (used in rescheduling).
            Maps (job_id, operation_no) -> ScheduledOperation.
        machine_available_times: Override for when each machine becomes free.
        job_available_times: Override for when each job's next op can start.

    Returns:
        A Schedule with all operations assigned start/completion times.

    Raises:
        ValueError: If the chromosome has incorrect operation counts.
    """
    if completed_ops is None:
        completed_ops = {}

    # Validate chromosome length
    expected_length = problem.total_operations - len(completed_ops)
    if len(chromosome) != expected_length:
        raise ValueError(
            f"Chromosome length {len(chromosome)} != expected "
            f"{expected_length} (total {problem.total_operations} "
            f"- {len(completed_ops)} completed)"
        )

    # Validate operation counts in chromosome
    expected_counts: Dict[str, int] = {}
    for job in problem.jobs.values():
        remaining = sum(
            1 for op in job.operations
            if (op.job_id, op.operation_no) not in completed_ops
        )
        if remaining > 0:
            expected_counts[job.job_id] = remaining

    actual_counts: Dict[str, int] = {}
    for gene in chromosome:
        actual_counts[gene] = actual_counts.get(gene, 0) + 1

    if actual_counts != expected_counts:
        raise ValueError(
            f"Chromosome operation counts {actual_counts} do not match "
            f"expected {expected_counts}"
        )

    # Initialise tracking structures
    # Track the next operation index to decode for each job
    next_op_index: Dict[str, int] = {}
    for job_id, job in problem.jobs.items():
        # Find the first un-completed operation
        for op in job.operations:
            if (op.job_id, op.operation_no) not in completed_ops:
                next_op_index[job_id] = job.operations.index(op)
                break
        else:
            # All operations completed
            next_op_index[job_id] = job.num_operations

    # Machine available time = max(initial, end of last scheduled op)
    m_avail: Dict[str, float] = {}
    for mid, machine in problem.machines.items():
        if machine_available_times and mid in machine_available_times:
            m_avail[mid] = machine_available_times[mid]
        else:
            m_avail[mid] = machine.initial_available_time

    # Job available time = end of the last completed/decoded op
    j_avail: Dict[str, float] = {}
    for job_id, job in problem.jobs.items():
        if job_available_times and job_id in job_available_times:
            j_avail[job_id] = job_available_times[job_id]
        else:
            # Check completed ops for this job
            completed_for_job = [
                c for (jid, _), c in completed_ops.items() if jid == job_id
            ]
            if completed_for_job:
                j_avail[job_id] = max(c.completion_time for c in completed_for_job)
            else:
                j_avail[job_id] = job.release_time

    scheduled: List[ScheduledOperation] = list(completed_ops.values())

    # Decode chromosome left-to-right
    for gene in chromosome:
        job = problem.jobs[gene]
        idx = next_op_index[gene]
        op = job.operations[idx]
        next_op_index[gene] = idx + 1

        # Earliest start: max(machine available, job precedence)
        desired_start = max(m_avail[op.machine_id], j_avail[gene])

        # Respect unavailability
        start = _earliest_start_respecting_unavailability(
            desired_start,
            op.processing_time,
            op.machine_id,
            problem.machine_unavailability,
        )

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

        # Update availability
        m_avail[op.machine_id] = completion
        j_avail[gene] = completion

    return Schedule(operations=scheduled)


def validate_schedule(
    schedule: Schedule, problem: ProblemInstance
) -> List[str]:
    """Validate a schedule against problem constraints.

    Checks:
    1. All operations are present.
    2. Job precedence: S_{i,j+1} >= C_{i,j}.
    3. Machine non-overlap: no two operations on the same machine overlap.
    4. Completion times: C = S + p.
    5. Machine unavailability: no operation runs during downtime.

    Returns a list of violation messages (empty = valid).
    """
    errors: List[str] = []

    # Build lookup
    sched_ops: Dict[Tuple[str, int], ScheduledOperation] = {}
    for sop in schedule.operations:
        key = (sop.job_id, sop.operation_no)
        if key in sched_ops:
            errors.append(f"Duplicate scheduled operation: {key}")
        sched_ops[key] = sop

    # 1. All operations present
    for job in problem.jobs.values():
        for op in job.operations:
            if (op.job_id, op.operation_no) not in sched_ops:
                errors.append(
                    f"Missing operation: {op.job_id}-Op{op.operation_no}"
                )

    # 2. Completion time = start + processing
    for sop in schedule.operations:
        expected_c = sop.start_time + sop.processing_time
        if abs(sop.completion_time - expected_c) > 1e-9:
            errors.append(
                f"{sop.job_id}-Op{sop.operation_no}: "
                f"C={sop.completion_time} != S({sop.start_time}) + "
                f"p({sop.processing_time}) = {expected_c}"
            )

    # 3. Job precedence
    for job in problem.jobs.values():
        for i in range(len(job.operations) - 1):
            curr_key = (job.job_id, job.operations[i].operation_no)
            next_key = (job.job_id, job.operations[i + 1].operation_no)
            if curr_key in sched_ops and next_key in sched_ops:
                curr = sched_ops[curr_key]
                nxt = sched_ops[next_key]
                if nxt.start_time < curr.completion_time - 1e-9:
                    errors.append(
                        f"Precedence violation: {next_key} starts at "
                        f"{nxt.start_time} before {curr_key} ends at "
                        f"{curr.completion_time}"
                    )

    # 4. Machine non-overlap
    machine_ops: Dict[str, List[ScheduledOperation]] = {}
    for sop in schedule.operations:
        machine_ops.setdefault(sop.machine_id, []).append(sop)

    for mid, ops in machine_ops.items():
        ops_sorted = sorted(ops, key=lambda o: o.start_time)
        for i in range(len(ops_sorted) - 1):
            a = ops_sorted[i]
            b = ops_sorted[i + 1]
            if b.start_time < a.completion_time - 1e-9:
                errors.append(
                    f"Machine {mid} overlap: {a.job_id}-Op{a.operation_no} "
                    f"[{a.start_time},{a.completion_time}) overlaps "
                    f"{b.job_id}-Op{b.operation_no} [{b.start_time},"
                    f"{b.completion_time})"
                )

    # 5. Unavailability
    for sop in schedule.operations:
        for umid, us, ue in problem.machine_unavailability:
            if sop.machine_id == umid:
                # Check overlap
                if sop.start_time < ue and sop.completion_time > us:
                    errors.append(
                        f"{sop.job_id}-Op{sop.operation_no} on {umid} "
                        f"[{sop.start_time},{sop.completion_time}) overlaps "
                        f"unavailability [{us},{ue})"
                    )

    return errors
