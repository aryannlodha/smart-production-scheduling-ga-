"""
Discrete-event simulation engine for dynamic rescheduling.

Manages a virtual clock, tracks operation states, handles machine
breakdowns, and triggers rescheduling.

Operation states:
  - WAITING: Not yet started.
  - RUNNING: Currently being processed.
  - COMPLETED: Finished processing.
  - PAUSED: Interrupted by a breakdown (will resume after repair).

Machine states:
  - IDLE: Available, not processing.
  - BUSY: Processing an operation.
  - DOWN: Failed, under repair.

Interruption policy (configurable):
  - RESUME: The interrupted operation resumes after repair with its
    remaining processing time.  This is the default.
  - RESTART: The interrupted operation restarts from scratch after repair.
"""

from __future__ import annotations

import enum
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from src.scheduler.models import (
    BreakdownEvent,
    ProblemInstance,
    Schedule,
    ScheduledOperation,
)
from src.genetic_algorithm.ga import (
    GAConfig,
    GAResult,
    run_genetic_algorithm,
)
from src.baselines.dispatching import schedule_fcfs
from src.metrics.performance import calculate_metrics, ScheduleMetrics


class OperationState(enum.Enum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"


class MachineState(enum.Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    DOWN = "DOWN"


class InterruptionPolicy(enum.Enum):
    RESUME = "RESUME"      # Continue with remaining time after repair
    RESTART = "RESTART"    # Restart the operation from scratch after repair


@dataclass
class OperationStatus:
    """Runtime status of a single operation during simulation."""
    job_id: str
    operation_no: int
    machine_id: str
    processing_time: float
    state: OperationState = OperationState.WAITING
    start_time: Optional[float] = None
    completion_time: Optional[float] = None
    elapsed_time: float = 0.0  # Time processed so far (for resume)
    remaining_time: Optional[float] = None  # Set when paused

    @property
    def key(self) -> Tuple[str, int]:
        return (self.job_id, self.operation_no)


@dataclass
class MachineStatus:
    """Runtime status of a machine during simulation."""
    machine_id: str
    state: MachineState = MachineState.IDLE
    current_operation: Optional[Tuple[str, int]] = None  # (job_id, op_no)
    down_until: Optional[float] = None


@dataclass
class SimulationState:
    """Complete state of the production simulation at a point in time."""
    current_time: float = 0.0
    operations: Dict[Tuple[str, int], OperationStatus] = field(
        default_factory=dict
    )
    machines: Dict[str, MachineStatus] = field(default_factory=dict)
    original_schedule: Optional[Schedule] = None
    current_schedule: Optional[Schedule] = None
    revised_schedule: Optional[Schedule] = None
    breakdown_events: List[BreakdownEvent] = field(default_factory=list)
    original_metrics: Optional[ScheduleMetrics] = None
    revised_metrics: Optional[ScheduleMetrics] = None
    interruption_policy: InterruptionPolicy = InterruptionPolicy.RESUME
    is_running: bool = False
    is_complete: bool = False


class ProductionSimulator:
    """Manages the production simulation with breakdown and rescheduling.

    Usage:
        sim = ProductionSimulator(problem, schedule)
        sim.advance_to(10.0)            # Advance clock to t=10
        sim.trigger_breakdown("M1", 5)  # M1 breaks, 5 units to repair
        result = sim.reschedule()        # GA reschedules remaining work
        sim.advance_to(50.0)            # Continue simulation
    """

    def __init__(
        self,
        problem: ProblemInstance,
        schedule: Schedule,
        interruption_policy: InterruptionPolicy = InterruptionPolicy.RESUME,
    ):
        self.problem = deepcopy(problem)
        self.state = SimulationState(
            interruption_policy=interruption_policy,
        )
        self.state.original_schedule = deepcopy(schedule)
        self.state.current_schedule = deepcopy(schedule)

        # Initialise operation statuses
        for job in self.problem.jobs.values():
            for op in job.operations:
                self.state.operations[(op.job_id, op.operation_no)] = (
                    OperationStatus(
                        job_id=op.job_id,
                        operation_no=op.operation_no,
                        machine_id=op.machine_id,
                        processing_time=op.processing_time,
                    )
                )

        # Initialise machine statuses
        for mid in self.problem.machine_ids:
            self.state.machines[mid] = MachineStatus(machine_id=mid)

        self.state.is_running = True

    def advance_to(self, target_time: float) -> SimulationState:
        """Advance the simulation clock to target_time.

        Updates operation and machine states based on the current schedule.
        """
        if target_time < self.state.current_time:
            return self.state  # Cannot go backwards

        schedule = self.state.current_schedule
        if schedule is None:
            return self.state

        self.state.current_time = target_time

        # Update operation states based on schedule
        for sop in schedule.operations:
            key = (sop.job_id, sop.operation_no)
            op_status = self.state.operations.get(key)
            if op_status is None:
                continue

            if op_status.state == OperationState.PAUSED:
                continue  # Don't update paused operations from schedule

            if sop.completion_time <= target_time:
                op_status.state = OperationState.COMPLETED
                op_status.start_time = sop.start_time
                op_status.completion_time = sop.completion_time
                op_status.elapsed_time = sop.processing_time
            elif sop.start_time <= target_time < sop.completion_time:
                op_status.state = OperationState.RUNNING
                op_status.start_time = sop.start_time
                op_status.elapsed_time = target_time - sop.start_time
            # else: WAITING

        # Update machine states
        for mid, m_status in self.state.machines.items():
            if m_status.state == MachineState.DOWN:
                if (
                    m_status.down_until is not None
                    and target_time >= m_status.down_until
                ):
                    m_status.state = MachineState.IDLE
                    m_status.current_operation = None
                    m_status.down_until = None
                continue

            # Find if any operation is running on this machine
            running_op = None
            for sop in schedule.operations:
                if (
                    sop.machine_id == mid
                    and sop.start_time <= target_time < sop.completion_time
                ):
                    running_op = (sop.job_id, sop.operation_no)
                    break

            if running_op:
                m_status.state = MachineState.BUSY
                m_status.current_operation = running_op
            else:
                m_status.state = MachineState.IDLE
                m_status.current_operation = None

        # Check if all operations are complete
        all_complete = all(
            op.state == OperationState.COMPLETED
            for op in self.state.operations.values()
        )
        if all_complete:
            self.state.is_complete = True
            self.state.is_running = False

        return self.state

    def trigger_breakdown(
        self,
        machine_id: str,
        repair_duration: float,
        breakdown_time: Optional[float] = None,
    ) -> BreakdownEvent:
        """Trigger a machine breakdown.

        Args:
            machine_id: The machine that fails.
            repair_duration: Duration of the repair.
            breakdown_time: Time of breakdown.  Uses current_time if None.

        Returns:
            The BreakdownEvent created.
        """
        if machine_id not in self.state.machines:
            raise ValueError(f"Unknown machine: {machine_id}")

        if breakdown_time is None:
            breakdown_time = self.state.current_time

        event = BreakdownEvent(
            machine_id=machine_id,
            breakdown_time=breakdown_time,
            repair_duration=repair_duration,
        )
        self.state.breakdown_events.append(event)

        # Update machine state
        m_status = self.state.machines[machine_id]
        m_status.state = MachineState.DOWN
        m_status.down_until = event.repair_end_time

        # Handle operation interrupted on this machine
        if m_status.current_operation:
            op_key = m_status.current_operation
            op_status = self.state.operations.get(op_key)
            if op_status and op_status.state == OperationState.RUNNING:
                op_status.state = OperationState.PAUSED
                start = (
                    op_status.start_time
                    if op_status.start_time is not None
                    else breakdown_time
                )
                op_status.elapsed_time = breakdown_time - start
                if self.state.interruption_policy == InterruptionPolicy.RESUME:
                    op_status.remaining_time = (
                        op_status.processing_time - op_status.elapsed_time
                    )
                else:
                    op_status.remaining_time = op_status.processing_time

        # Add unavailability to problem
        self.problem.add_unavailability(
            machine_id, breakdown_time, event.repair_end_time
        )

        return event

    def get_rescheduling_context(
        self,
    ) -> Tuple[
        Dict[Tuple[str, int], ScheduledOperation],
        Dict[str, float],
        Dict[str, float],
        ProblemInstance,
    ]:
        """Build the context needed for rescheduling.

        Returns:
            - completed_ops: Operations that are fully done.
            - machine_available_times: When each machine becomes free.
            - job_available_times: When each job's next op can start.
            - problem: Updated problem instance with unavailability.
        """
        current_time = self.state.current_time

        completed_ops: Dict[Tuple[str, int], ScheduledOperation] = {}
        machine_available: Dict[str, float] = {}
        job_available: Dict[str, float] = {}

        # Completed operations
        for key, op_status in self.state.operations.items():
            if op_status.state == OperationState.COMPLETED:
                completed_ops[key] = ScheduledOperation(
                    job_id=op_status.job_id,
                    operation_no=op_status.operation_no,
                    machine_id=op_status.machine_id,
                    processing_time=op_status.processing_time,
                    start_time=op_status.start_time or 0,
                    completion_time=op_status.completion_time or 0,
                )

        # Handle running (unaffected) operations — they continue
        for key, op_status in self.state.operations.items():
            if op_status.state == OperationState.RUNNING:
                # This operation is still running on an unaffected machine
                sched = self.state.current_schedule
                if sched:
                    for sop in sched.operations:
                        if (sop.job_id, sop.operation_no) == key:
                            completed_ops[key] = ScheduledOperation(
                                job_id=sop.job_id,
                                operation_no=sop.operation_no,
                                machine_id=sop.machine_id,
                                processing_time=sop.processing_time,
                                start_time=sop.start_time,
                                completion_time=sop.completion_time,
                            )
                            break

        # Handle paused operations — need rescheduling with remaining time
        # We modify the problem's processing times for paused ops
        rescheduling_problem = deepcopy(self.problem)
        for key, op_status in self.state.operations.items():
            if op_status.state == OperationState.PAUSED:
                # Update the processing time to the remaining time
                for job in rescheduling_problem.jobs.values():
                    for op in job.operations:
                        if (op.job_id, op.operation_no) == key:
                            if op_status.remaining_time is not None:
                                op.processing_time = op_status.remaining_time

        # Machine available times
        for mid, m_status in self.state.machines.items():
            if m_status.state == MachineState.DOWN:
                machine_available[mid] = m_status.down_until or current_time
            elif m_status.state == MachineState.BUSY:
                # Find completion time of current operation
                if m_status.current_operation and m_status.current_operation in completed_ops:
                    machine_available[mid] = completed_ops[m_status.current_operation].completion_time
                else:
                    machine_available[mid] = current_time
            else:
                machine_available[mid] = max(
                    current_time,
                    rescheduling_problem.machines[mid].initial_available_time,
                )

        # Job available times
        for jid, job in rescheduling_problem.jobs.items():
            completed_for_job = [
                c for (j, _), c in completed_ops.items() if j == jid
            ]
            if completed_for_job:
                job_available[jid] = max(
                    c.completion_time for c in completed_for_job
                )
            else:
                job_available[jid] = max(current_time, job.release_time)

        return completed_ops, machine_available, job_available, rescheduling_problem

    def reschedule(
        self,
        method: str = "GA",
        ga_config: Optional[GAConfig] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Schedule:
        """Reschedule remaining work after a breakdown.

        Args:
            method: "GA", "FCFS", "SPT", or "EDD".
            ga_config: GA parameters (if method="GA").
            progress_callback: Optional progress callback for GA.

        Returns:
            The revised Schedule.
        """
        (
            completed_ops,
            machine_available,
            job_available,
            rescheduling_problem,
        ) = self.get_rescheduling_context()

        if method == "GA":
            result = run_genetic_algorithm(
                rescheduling_problem,
                ga_config or GAConfig(max_generations=50, population_size=80),
                completed_ops=completed_ops,
                machine_available_times=machine_available,
                job_available_times=job_available,
                progress_callback=progress_callback,
            )
            revised = result.best_schedule
        else:
            from src.baselines.dispatching import (
                schedule_fcfs,
                schedule_spt,
                schedule_edd,
            )
            dispatch_map = {
                "FCFS": schedule_fcfs,
                "SPT": schedule_spt,
                "EDD": schedule_edd,
            }
            fn = dispatch_map.get(method, schedule_fcfs)
            revised = fn(
                rescheduling_problem,
                completed_ops=completed_ops,
                machine_available_times=machine_available,
                job_available_times=job_available,
            )

        revised.method = f"{method} (Rescheduled)"
        self.state.revised_schedule = revised
        self.state.current_schedule = revised

        # Compute metrics
        self.state.original_metrics = calculate_metrics(
            self.state.original_schedule, self.problem  # type: ignore
        )
        self.state.revised_metrics = calculate_metrics(
            revised, rescheduling_problem
        )

        # Update operation states from revised schedule
        for sop in revised.operations:
            key = (sop.job_id, sop.operation_no)
            if key in self.state.operations:
                op_status = self.state.operations[key]
                if op_status.state in (
                    OperationState.WAITING,
                    OperationState.PAUSED,
                ):
                    op_status.state = OperationState.WAITING
                    op_status.start_time = sop.start_time
                    op_status.completion_time = sop.completion_time
                    op_status.remaining_time = None

        return revised

    def get_completed_ops_list(self) -> List[Tuple[str, int]]:
        """Return keys of completed operations."""
        return [
            key
            for key, op in self.state.operations.items()
            if op.state == OperationState.COMPLETED
        ]

    def get_running_ops_list(self) -> List[Tuple[str, int]]:
        """Return keys of currently running operations."""
        return [
            key
            for key, op in self.state.operations.items()
            if op.state == OperationState.RUNNING
        ]

    def get_waiting_ops_list(self) -> List[Tuple[str, int]]:
        """Return keys of waiting operations."""
        return [
            key
            for key, op in self.state.operations.items()
            if op.state == OperationState.WAITING
        ]

    def get_paused_ops_list(self) -> List[Tuple[str, int]]:
        """Return keys of paused operations."""
        return [
            key
            for key, op in self.state.operations.items()
            if op.state == OperationState.PAUSED
        ]

    def reset(self) -> None:
        """Reset the simulation to the initial state."""
        self.__init__(  # type: ignore
            self.problem,
            self.state.original_schedule,  # type: ignore
            self.state.interruption_policy,
        )
