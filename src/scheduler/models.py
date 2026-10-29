"""
Data models and validation for the Job Shop Scheduling Problem.

This module defines the core data structures (Job, Operation, Machine,
ProblemInstance) and provides CSV loading with comprehensive validation.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Operation:
    """A single operation within a job.

    Attributes:
        job_id: Identifier of the parent job (e.g. "J1").
        operation_no: 1-based index of this operation in the job route.
        machine_id: Machine that must process this operation (e.g. "M1").
        processing_time: Time units required to complete this operation.
    """
    job_id: str
    operation_no: int
    machine_id: str
    processing_time: float

    def __post_init__(self):
        if self.processing_time <= 0:
            raise ValueError(
                f"Operation {self.job_id}-Op{self.operation_no}: "
                f"processing_time must be positive, got {self.processing_time}"
            )
        if self.operation_no < 1:
            raise ValueError(
                f"Operation {self.job_id}-Op{self.operation_no}: "
                f"operation_no must be >= 1"
            )


@dataclass
class Job:
    """A production job consisting of a sequence of operations.

    Attributes:
        job_id: Unique job identifier (e.g. "J1").
        release_time: Earliest time the first operation can start.
        due_date: Target completion time for the entire job.
        priority: Optional priority value (lower = higher priority).
        operations: Ordered list of operations forming the job's route.
    """
    job_id: str
    release_time: float = 0.0
    due_date: float = 0.0
    priority: int = 1
    operations: List[Operation] = field(default_factory=list)

    @property
    def num_operations(self) -> int:
        return len(self.operations)


@dataclass
class Machine:
    """A machine that processes operations.

    Attributes:
        machine_id: Unique machine identifier (e.g. "M1").
        machine_name: Human-readable name.
        initial_available_time: Earliest time the machine can start.
    """
    machine_id: str
    machine_name: str = ""
    initial_available_time: float = 0.0


@dataclass
class ScheduledOperation:
    """An operation with assigned start and completion times.

    Attributes:
        job_id: Parent job identifier.
        operation_no: 1-based operation index in the job route.
        machine_id: Machine processing this operation.
        processing_time: Duration of the operation.
        start_time: Assigned start time.
        completion_time: Assigned completion time = start_time + processing_time.
    """
    job_id: str
    operation_no: int
    machine_id: str
    processing_time: float
    start_time: float
    completion_time: float


@dataclass
class Schedule:
    """A complete production schedule.

    Attributes:
        operations: List of all scheduled operations.
        method: Name of the method that produced this schedule.
        computation_time: Seconds taken to compute this schedule.
    """
    operations: List[ScheduledOperation] = field(default_factory=list)
    method: str = ""
    computation_time: float = 0.0

    def get_machine_schedule(self, machine_id: str) -> List[ScheduledOperation]:
        """Return operations assigned to a machine, sorted by start time."""
        return sorted(
            [op for op in self.operations if op.machine_id == machine_id],
            key=lambda op: op.start_time,
        )

    def get_job_schedule(self, job_id: str) -> List[ScheduledOperation]:
        """Return operations of a job, sorted by operation number."""
        return sorted(
            [op for op in self.operations if op.job_id == job_id],
            key=lambda op: op.operation_no,
        )


@dataclass
class BreakdownEvent:
    """A machine breakdown event.

    Attributes:
        machine_id: The machine that fails.
        breakdown_time: Simulated time when the breakdown occurs.
        repair_duration: How long the machine is unavailable.
        repair_end_time: Time at which the machine becomes available again.
    """
    machine_id: str
    breakdown_time: float
    repair_duration: float

    @property
    def repair_end_time(self) -> float:
        return self.breakdown_time + self.repair_duration


@dataclass
class ProblemInstance:
    """A complete Job Shop Scheduling Problem instance.

    Attributes:
        jobs: Dictionary mapping job_id -> Job.
        machines: Dictionary mapping machine_id -> Machine.
        machine_unavailability: List of (machine_id, start, end) intervals.
    """
    jobs: Dict[str, Job] = field(default_factory=dict)
    machines: Dict[str, Machine] = field(default_factory=dict)
    machine_unavailability: List[Tuple[str, float, float]] = field(
        default_factory=list
    )

    @property
    def num_jobs(self) -> int:
        return len(self.jobs)

    @property
    def num_machines(self) -> int:
        return len(self.machines)

    @property
    def total_operations(self) -> int:
        return sum(j.num_operations for j in self.jobs.values())

    @property
    def job_ids(self) -> List[str]:
        return sorted(self.jobs.keys())

    @property
    def machine_ids(self) -> List[str]:
        return sorted(self.machines.keys())

    def get_operations_on_machine(self, machine_id: str) -> List[Operation]:
        """Return all operations that must be processed on a given machine."""
        ops = []
        for job in self.jobs.values():
            for op in job.operations:
                if op.machine_id == machine_id:
                    ops.append(op)
        return ops

    def add_unavailability(
        self, machine_id: str, start: float, end: float
    ) -> None:
        """Mark a machine as unavailable during [start, end)."""
        if machine_id not in self.machines:
            raise ValueError(f"Unknown machine: {machine_id}")
        self.machine_unavailability.append((machine_id, start, end))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_problem(instance: ProblemInstance) -> List[str]:
    """Validate a problem instance and return a list of error messages.

    Returns an empty list if the instance is valid.
    """
    errors: List[str] = []

    if not instance.jobs:
        errors.append("No jobs defined.")
    if not instance.machines:
        errors.append("No machines defined.")

    seen_ops: set = set()
    for job_id, job in instance.jobs.items():
        if not job.operations:
            errors.append(f"Job {job_id} has no operations.")
            continue

        # Check operation numbering is contiguous starting from 1
        op_numbers = sorted(op.operation_no for op in job.operations)
        expected = list(range(1, len(job.operations) + 1))
        if op_numbers != expected:
            errors.append(
                f"Job {job_id}: operation numbers {op_numbers} are not "
                f"contiguous starting from 1. Expected {expected}."
            )

        for op in job.operations:
            # Check for duplicate operations
            key = (op.job_id, op.operation_no)
            if key in seen_ops:
                errors.append(
                    f"Duplicate operation: {op.job_id}-Op{op.operation_no}"
                )
            seen_ops.add(key)

            # Check machine exists
            if op.machine_id not in instance.machines:
                errors.append(
                    f"Operation {op.job_id}-Op{op.operation_no} references "
                    f"unknown machine {op.machine_id}"
                )

            # Check processing time
            if op.processing_time <= 0:
                errors.append(
                    f"Operation {op.job_id}-Op{op.operation_no}: "
                    f"processing_time must be positive"
                )

        # Check due date
        if job.due_date < 0:
            errors.append(f"Job {job_id}: due_date cannot be negative")

    # Check unavailability intervals
    for mid, start, end in instance.machine_unavailability:
        if mid not in instance.machines:
            errors.append(f"Unavailability references unknown machine {mid}")
        if end <= start:
            errors.append(
                f"Unavailability for {mid}: end ({end}) must be > start ({start})"
            )

    return errors


# ---------------------------------------------------------------------------
# CSV Loading
# ---------------------------------------------------------------------------

def load_problem_from_csv(
    jobs_csv: str,
    operations_csv: str,
    machines_csv: str,
) -> ProblemInstance:
    """Load a ProblemInstance from three CSV files.

    Args:
        jobs_csv: Path to jobs.csv with columns: job_id, release_time,
                  due_date, priority (optional).
        operations_csv: Path to operations.csv with columns: job_id,
                        operation_no, machine_id, processing_time.
        machines_csv: Path to machines.csv with columns: machine_id,
                      machine_name, initial_available_time.

    Returns:
        A validated ProblemInstance.

    Raises:
        FileNotFoundError: If any CSV file is missing.
        ValueError: If validation fails.
    """
    for path, label in [
        (jobs_csv, "jobs"),
        (operations_csv, "operations"),
        (machines_csv, "machines"),
    ]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"{label} CSV not found: {path}")

    instance = ProblemInstance()

    # --- Load machines ---
    with open(machines_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mid = row["machine_id"].strip()
            instance.machines[mid] = Machine(
                machine_id=mid,
                machine_name=row.get("machine_name", mid).strip(),
                initial_available_time=float(
                    row.get("initial_available_time", 0)
                ),
            )

    # --- Load jobs ---
    with open(jobs_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            jid = row["job_id"].strip()
            instance.jobs[jid] = Job(
                job_id=jid,
                release_time=float(row.get("release_time", 0)),
                due_date=float(row.get("due_date", 0)),
                priority=int(row.get("priority", 1)),
            )

    # --- Load operations ---
    with open(operations_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            jid = row["job_id"].strip()
            if jid not in instance.jobs:
                raise ValueError(
                    f"Operation references unknown job_id: {jid}"
                )
            op = Operation(
                job_id=jid,
                operation_no=int(row["operation_no"]),
                machine_id=row["machine_id"].strip(),
                processing_time=float(row["processing_time"]),
            )
            instance.jobs[jid].operations.append(op)

    # Sort each job's operations by operation_no
    for job in instance.jobs.values():
        job.operations.sort(key=lambda op: op.operation_no)

    # Validate
    errors = validate_problem(instance)
    if errors:
        raise ValueError(
            "Problem instance validation failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    return instance


def create_problem_from_dicts(
    jobs_data: List[Dict],
    operations_data: List[Dict],
    machines_data: List[Dict],
) -> ProblemInstance:
    """Create a ProblemInstance from lists of dictionaries.

    Useful for dashboard/programmatic input without CSV files.
    """
    instance = ProblemInstance()

    for m in machines_data:
        mid = str(m["machine_id"]).strip()
        instance.machines[mid] = Machine(
            machine_id=mid,
            machine_name=str(m.get("machine_name", mid)).strip(),
            initial_available_time=float(m.get("initial_available_time", 0)),
        )

    for j in jobs_data:
        jid = str(j["job_id"]).strip()
        instance.jobs[jid] = Job(
            job_id=jid,
            release_time=float(j.get("release_time", 0)),
            due_date=float(j.get("due_date", 0)),
            priority=int(j.get("priority", 1)),
        )

    for o in operations_data:
        jid = str(o["job_id"]).strip()
        if jid not in instance.jobs:
            raise ValueError(f"Operation references unknown job_id: {jid}")
        op = Operation(
            job_id=jid,
            operation_no=int(o["operation_no"]),
            machine_id=str(o["machine_id"]).strip(),
            processing_time=float(o["processing_time"]),
        )
        instance.jobs[jid].operations.append(op)

    for job in instance.jobs.values():
        job.operations.sort(key=lambda op: op.operation_no)

    errors = validate_problem(instance)
    if errors:
        raise ValueError(
            "Problem instance validation failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    return instance
