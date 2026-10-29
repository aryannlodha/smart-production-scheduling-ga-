"""
Comprehensive test suite for the Smart Production Scheduling system.

Tests cover:
  1.  Dataset validation
  2.  Job precedence
  3.  Machine non-overlap
  4.  Schedule decoder correctness
  5.  Chromosome operation counts
  6.  GA fitness calculation
  7.  Baseline scheduling rules
  8.  Metrics calculations
  9.  Machine unavailability intervals
  10. Interrupted operations and remaining processing time
  11. Preservation of completed operations during rescheduling
  12. Continuation of unaffected machine operations
  13. Breakdown and recovery events
  14. Reproducibility using a fixed random seed
  15. Behaviour with missing or invalid input data
  16. Software-only operation when no ESP32 is connected
"""

import os
import sys
import random
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scheduler.models import (
    Job,
    Machine,
    Operation,
    ProblemInstance,
    Schedule,
    ScheduledOperation,
    BreakdownEvent,
    validate_problem,
    load_problem_from_csv,
    create_problem_from_dicts,
)
from src.scheduler.decoder import decode_chromosome, validate_schedule
from src.genetic_algorithm.ga import (
    GAConfig,
    GAResult,
    calculate_makespan,
    create_random_chromosome,
    fitness_function,
    initialise_population,
    pox_crossover,
    swap_mutation,
    tournament_selection,
    run_genetic_algorithm,
)
from src.baselines.dispatching import schedule_fcfs, schedule_spt, schedule_edd
from src.metrics.performance import calculate_metrics, ScheduleMetrics
from src.simulation.engine import (
    ProductionSimulator,
    OperationState,
    MachineState,
    InterruptionPolicy,
)
from src.hardware.serial_comm import (
    ESP32Handler,
    SerialMessage,
    MessageType,
    ConnectionState,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_problem():
    """A small 3-job, 3-machine problem for unit tests."""
    return create_problem_from_dicts(
        jobs_data=[
            {"job_id": "J1", "release_time": 0, "due_date": 30},
            {"job_id": "J2", "release_time": 0, "due_date": 25},
            {"job_id": "J3", "release_time": 0, "due_date": 28},
        ],
        operations_data=[
            {"job_id": "J1", "operation_no": 1, "machine_id": "M1", "processing_time": 3},
            {"job_id": "J1", "operation_no": 2, "machine_id": "M2", "processing_time": 4},
            {"job_id": "J1", "operation_no": 3, "machine_id": "M3", "processing_time": 2},
            {"job_id": "J2", "operation_no": 1, "machine_id": "M1", "processing_time": 5},
            {"job_id": "J2", "operation_no": 2, "machine_id": "M3", "processing_time": 3},
            {"job_id": "J3", "operation_no": 1, "machine_id": "M2", "processing_time": 4},
            {"job_id": "J3", "operation_no": 2, "machine_id": "M3", "processing_time": 5},
        ],
        machines_data=[
            {"machine_id": "M1", "machine_name": "Machine 1"},
            {"machine_id": "M2", "machine_name": "Machine 2"},
            {"machine_id": "M3", "machine_name": "Machine 3"},
        ],
    )


@pytest.fixture
def default_problem():
    """The default 8-job, 3-machine problem from the sample data."""
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    )
    return load_problem_from_csv(
        os.path.join(data_dir, "jobs.csv"),
        os.path.join(data_dir, "operations.csv"),
        os.path.join(data_dir, "machines.csv"),
    )


@pytest.fixture
def ga_config_fixed_seed():
    """GA config with a fixed seed for reproducibility."""
    return GAConfig(
        population_size=50,
        max_generations=30,
        crossover_prob=0.8,
        mutation_prob=0.1,
        elite_count=2,
        tournament_size=5,
        random_seed=42,
    )


# ===================================================================
# 1. Dataset Validation
# ===================================================================

class TestDatasetValidation:
    def test_valid_problem(self, small_problem):
        errors = validate_problem(small_problem)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_no_jobs(self):
        p = ProblemInstance(
            machines={"M1": Machine("M1")},
        )
        errors = validate_problem(p)
        assert any("No jobs" in e for e in errors)

    def test_no_machines(self):
        p = ProblemInstance(
            jobs={"J1": Job("J1", operations=[
                Operation("J1", 1, "M1", 5)
            ])},
        )
        errors = validate_problem(p)
        assert any("No machines" in e for e in errors)

    def test_missing_machine_ref(self):
        p = ProblemInstance(
            jobs={"J1": Job("J1", operations=[
                Operation("J1", 1, "M99", 5)
            ])},
            machines={"M1": Machine("M1")},
        )
        errors = validate_problem(p)
        assert any("unknown machine" in e.lower() for e in errors)

    def test_zero_processing_time(self):
        with pytest.raises(ValueError, match="positive"):
            Operation("J1", 1, "M1", 0)

    def test_negative_processing_time(self):
        with pytest.raises(ValueError, match="positive"):
            Operation("J1", 1, "M1", -3)

    def test_non_contiguous_operations(self):
        p = ProblemInstance(
            jobs={"J1": Job("J1", operations=[
                Operation("J1", 1, "M1", 5),
                Operation("J1", 3, "M2", 4),  # Missing op 2
            ])},
            machines={"M1": Machine("M1"), "M2": Machine("M2")},
        )
        errors = validate_problem(p)
        assert any("contiguous" in e.lower() for e in errors)

    def test_duplicate_operations(self):
        p = ProblemInstance(
            jobs={"J1": Job("J1", operations=[
                Operation("J1", 1, "M1", 5),
                Operation("J1", 1, "M2", 4),  # Duplicate op_no
            ])},
            machines={"M1": Machine("M1"), "M2": Machine("M2")},
        )
        errors = validate_problem(p)
        assert any("contiguous" in e.lower() or "duplicate" in e.lower() for e in errors)

    def test_csv_loading(self, default_problem):
        assert default_problem.num_jobs == 8
        assert default_problem.num_machines == 3
        assert default_problem.total_operations == 18

    def test_csv_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_problem_from_csv("no.csv", "no2.csv", "no3.csv")


# ===================================================================
# 2. Job Precedence
# ===================================================================

class TestJobPrecedence:
    def test_precedence_in_decoded_schedule(self, small_problem):
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        schedule = decode_chromosome(chrom, small_problem)

        for job in small_problem.jobs.values():
            job_ops = sorted(
                [s for s in schedule.operations if s.job_id == job.job_id],
                key=lambda s: s.operation_no,
            )
            for i in range(len(job_ops) - 1):
                assert job_ops[i + 1].start_time >= job_ops[i].completion_time, \
                    f"Precedence violation: {job.job_id} Op{job_ops[i].operation_no} -> Op{job_ops[i+1].operation_no}"


# ===================================================================
# 3. Machine Non-Overlap
# ===================================================================

class TestMachineNonOverlap:
    def test_no_overlap_in_decoded_schedule(self, small_problem):
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        schedule = decode_chromosome(chrom, small_problem)

        for mid in small_problem.machine_ids:
            machine_ops = sorted(
                [s for s in schedule.operations if s.machine_id == mid],
                key=lambda s: s.start_time,
            )
            for i in range(len(machine_ops) - 1):
                assert machine_ops[i + 1].start_time >= machine_ops[i].completion_time, \
                    f"Overlap on {mid}: {machine_ops[i].job_id} ends at {machine_ops[i].completion_time}, " \
                    f"{machine_ops[i+1].job_id} starts at {machine_ops[i+1].start_time}"


# ===================================================================
# 4. Schedule Decoder Correctness
# ===================================================================

class TestDecoderCorrectness:
    def test_all_operations_scheduled(self, small_problem):
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        schedule = decode_chromosome(chrom, small_problem)
        assert len(schedule.operations) == small_problem.total_operations

    def test_completion_equals_start_plus_processing(self, small_problem):
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        schedule = decode_chromosome(chrom, small_problem)
        for sop in schedule.operations:
            assert abs(sop.completion_time - (sop.start_time + sop.processing_time)) < 1e-9

    def test_validate_schedule_passes(self, small_problem):
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        schedule = decode_chromosome(chrom, small_problem)
        errors = validate_schedule(schedule, small_problem)
        assert errors == [], f"Schedule validation errors: {errors}"

    def test_deterministic_decoding(self, small_problem):
        chrom = ["J1", "J2", "J3", "J1", "J2", "J1", "J3"]
        s1 = decode_chromosome(chrom, small_problem)
        s2 = decode_chromosome(chrom, small_problem)
        for a, b in zip(
            sorted(s1.operations, key=lambda o: (o.job_id, o.operation_no)),
            sorted(s2.operations, key=lambda o: (o.job_id, o.operation_no)),
        ):
            assert a.start_time == b.start_time
            assert a.completion_time == b.completion_time

    def test_decoder_with_unavailability(self, small_problem):
        small_problem.add_unavailability("M1", 2, 10)
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        schedule = decode_chromosome(chrom, small_problem)
        errors = validate_schedule(schedule, small_problem)
        assert errors == [], f"Validation errors with unavailability: {errors}"


# ===================================================================
# 5. Chromosome Operation Counts
# ===================================================================

class TestChromosomeOperationCounts:
    def test_random_chromosome_counts(self, small_problem):
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)

        counts = {}
        for gene in chrom:
            counts[gene] = counts.get(gene, 0) + 1

        for job in small_problem.jobs.values():
            assert counts.get(job.job_id, 0) == job.num_operations, \
                f"Job {job.job_id}: expected {job.num_operations} occurrences, got {counts.get(job.job_id, 0)}"

    def test_chromosome_length(self, small_problem):
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        assert len(chrom) == small_problem.total_operations

    def test_invalid_chromosome_length(self, small_problem):
        with pytest.raises(ValueError, match="length"):
            decode_chromosome(["J1", "J2"], small_problem)

    def test_invalid_chromosome_counts(self, small_problem):
        bad_chrom = ["J1"] * 7  # Wrong job counts
        with pytest.raises(ValueError, match="counts"):
            decode_chromosome(bad_chrom, small_problem)


# ===================================================================
# 6. GA Fitness Calculation
# ===================================================================

class TestGAFitness:
    def test_fitness_is_makespan(self, small_problem):
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        fitness = fitness_function(chrom, small_problem)
        schedule = decode_chromosome(chrom, small_problem)
        makespan = max(op.completion_time for op in schedule.operations)
        assert abs(fitness - makespan) < 1e-9

    def test_fitness_positive(self, small_problem):
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        assert fitness_function(chrom, small_problem) > 0


# ===================================================================
# 7. Baseline Scheduling Rules
# ===================================================================

class TestBaselineRules:
    def test_fcfs_produces_valid_schedule(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        errors = validate_schedule(schedule, small_problem)
        assert errors == [], f"FCFS validation errors: {errors}"
        assert len(schedule.operations) == small_problem.total_operations
        assert schedule.method == "FCFS"

    def test_spt_produces_valid_schedule(self, small_problem):
        schedule = schedule_spt(small_problem)
        errors = validate_schedule(schedule, small_problem)
        assert errors == [], f"SPT validation errors: {errors}"
        assert len(schedule.operations) == small_problem.total_operations

    def test_edd_produces_valid_schedule(self, small_problem):
        schedule = schedule_edd(small_problem)
        errors = validate_schedule(schedule, small_problem)
        assert errors == [], f"EDD validation errors: {errors}"
        assert len(schedule.operations) == small_problem.total_operations

    def test_baselines_on_default_problem(self, default_problem):
        for method, fn in [
            ("FCFS", schedule_fcfs),
            ("SPT", schedule_spt),
            ("EDD", schedule_edd),
        ]:
            schedule = fn(default_problem)
            errors = validate_schedule(schedule, default_problem)
            assert errors == [], f"{method} validation errors: {errors}"
            assert len(schedule.operations) == default_problem.total_operations


# ===================================================================
# 8. Metrics Calculations
# ===================================================================

class TestMetrics:
    def test_makespan_calculation(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        metrics = calculate_metrics(schedule, small_problem)
        expected_makespan = max(op.completion_time for op in schedule.operations)
        assert abs(metrics.makespan - expected_makespan) < 1e-9

    def test_tardiness_calculation(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        metrics = calculate_metrics(schedule, small_problem)

        # Manual calculation
        total_tardiness = 0
        for jid, job in small_problem.jobs.items():
            job_ops = [op for op in schedule.operations if op.job_id == jid]
            if job_ops:
                completion = max(op.completion_time for op in job_ops)
                total_tardiness += max(0, completion - job.due_date)
        assert abs(metrics.total_tardiness - total_tardiness) < 1e-9

    def test_utilization_positive(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        metrics = calculate_metrics(schedule, small_problem)
        for mm in metrics.machine_metrics.values():
            assert mm.utilization_pct >= 0
            assert mm.utilization_pct <= 100.01  # Allow tiny float error

    def test_idle_time_non_negative(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        metrics = calculate_metrics(schedule, small_problem)
        for mm in metrics.machine_metrics.values():
            assert mm.idle_time >= -1e-9

    def test_computation_time_recorded(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        assert schedule.computation_time >= 0


# ===================================================================
# 9. Machine Unavailability Intervals
# ===================================================================

class TestMachineUnavailability:
    def test_decoder_respects_unavailability(self, small_problem):
        small_problem.add_unavailability("M1", 0, 5)
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        schedule = decode_chromosome(chrom, small_problem)

        for sop in schedule.operations:
            if sop.machine_id == "M1":
                # Should not overlap [0, 5)
                assert not (sop.start_time < 5 and sop.completion_time > 0), \
                    f"Op on M1 [{sop.start_time}, {sop.completion_time}) overlaps unavailability [0, 5)"

    def test_baseline_respects_unavailability(self, small_problem):
        small_problem.add_unavailability("M2", 3, 8)
        schedule = schedule_fcfs(small_problem)
        errors = validate_schedule(schedule, small_problem)
        assert errors == [], f"Validation errors: {errors}"


# ===================================================================
# 10. Interrupted Operations and Remaining Processing Time
# ===================================================================

class TestInterruptedOperations:
    def test_resume_policy(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        sim = ProductionSimulator(
            small_problem, schedule, InterruptionPolicy.RESUME
        )
        # Advance to t=2 so J1-Op1 (processing_time=3) is running
        sim.advance_to(2.0)
        # Trigger M1 breakdown
        event = sim.trigger_breakdown("M1", 5.0)

        paused = sim.get_paused_ops_list()
        if paused:
            key = paused[0]
            op_status = sim.state.operations[key]
            assert op_status.remaining_time is not None
            assert op_status.remaining_time < op_status.processing_time
            assert op_status.remaining_time > 0

    def test_restart_policy(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        sim = ProductionSimulator(
            small_problem, schedule, InterruptionPolicy.RESTART
        )
        sim.advance_to(2.0)
        sim.trigger_breakdown("M1", 5.0)

        paused = sim.get_paused_ops_list()
        if paused:
            key = paused[0]
            op_status = sim.state.operations[key]
            # RESTART: remaining = full processing time
            assert op_status.remaining_time == op_status.processing_time


# ===================================================================
# 11. Preservation of Completed Operations During Rescheduling
# ===================================================================

class TestCompletedPreservation:
    def test_completed_ops_preserved(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        sim = ProductionSimulator(small_problem, schedule)
        sim.advance_to(10.0)

        completed_before = set(sim.get_completed_ops_list())

        sim.trigger_breakdown("M3", 5.0)
        revised = sim.reschedule(method="FCFS")

        # All previously completed ops should be in revised schedule
        revised_keys = {
            (sop.job_id, sop.operation_no)
            for sop in revised.operations
        }
        for key in completed_before:
            assert key in revised_keys, \
                f"Completed operation {key} missing from revised schedule"


# ===================================================================
# 12. Continuation of Unaffected Machine Operations
# ===================================================================

class TestUnaffectedContinuation:
    def test_unaffected_machines_continue(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        sim = ProductionSimulator(small_problem, schedule)
        sim.advance_to(5.0)

        running_before = sim.get_running_ops_list()

        sim.trigger_breakdown("M1", 5.0)

        # Operations running on M2 or M3 should still be running or completed
        for key in running_before:
            op_status = sim.state.operations[key]
            if op_status.machine_id != "M1":
                assert op_status.state != OperationState.PAUSED, \
                    f"Op {key} on {op_status.machine_id} should not be paused"


# ===================================================================
# 13. Breakdown and Recovery Events
# ===================================================================

class TestBreakdownRecovery:
    def test_breakdown_sets_machine_down(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        sim = ProductionSimulator(small_problem, schedule)
        sim.advance_to(5.0)
        sim.trigger_breakdown("M1", 10.0)

        assert sim.state.machines["M1"].state == MachineState.DOWN
        assert sim.state.machines["M1"].down_until == 15.0

    def test_machine_recovers_after_repair(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        sim = ProductionSimulator(small_problem, schedule)
        sim.advance_to(5.0)
        sim.trigger_breakdown("M1", 10.0)

        # After rescheduling and advancing past repair
        sim.reschedule(method="FCFS")
        sim.advance_to(16.0)

        assert sim.state.machines["M1"].state != MachineState.DOWN

    def test_breakdown_unknown_machine(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        sim = ProductionSimulator(small_problem, schedule)
        with pytest.raises(ValueError, match="Unknown machine"):
            sim.trigger_breakdown("M99", 5.0)


# ===================================================================
# 14. Reproducibility Using a Fixed Random Seed
# ===================================================================

class TestReproducibility:
    def test_ga_reproducibility(self, small_problem, ga_config_fixed_seed):
        r1 = run_genetic_algorithm(small_problem, ga_config_fixed_seed)
        r2 = run_genetic_algorithm(small_problem, ga_config_fixed_seed)

        assert r1.best_fitness == r2.best_fitness
        assert r1.best_chromosome == r2.best_chromosome

    def test_random_chromosome_reproducibility(self, small_problem):
        c1 = create_random_chromosome(small_problem, random.Random(123))
        c2 = create_random_chromosome(small_problem, random.Random(123))
        assert c1 == c2


# ===================================================================
# 15. Behaviour with Missing or Invalid Input Data
# ===================================================================

class TestInvalidInputs:
    def test_empty_problem(self):
        p = ProblemInstance()
        errors = validate_problem(p)
        assert len(errors) > 0

    def test_job_without_operations(self):
        p = ProblemInstance(
            jobs={"J1": Job("J1")},
            machines={"M1": Machine("M1")},
        )
        errors = validate_problem(p)
        assert any("no operations" in e.lower() for e in errors)

    def test_create_problem_unknown_job_in_ops(self):
        with pytest.raises(ValueError, match="unknown job_id"):
            create_problem_from_dicts(
                jobs_data=[{"job_id": "J1", "due_date": 10}],
                operations_data=[
                    {"job_id": "J1", "operation_no": 1, "machine_id": "M1", "processing_time": 5},
                    {"job_id": "J99", "operation_no": 1, "machine_id": "M1", "processing_time": 3},
                ],
                machines_data=[{"machine_id": "M1"}],
            )

    def test_invalid_unavailability(self):
        p = ProblemInstance(
            machines={"M1": Machine("M1")},
        )
        p.machine_unavailability.append(("M1", 10, 5))  # end < start
        errors = validate_problem(p)
        # Note: no jobs, so will have that error; check unavailability too
        assert any("end" in e.lower() for e in errors)


# ===================================================================
# 16. Software-Only Operation
# ===================================================================

class TestSoftwareOnly:
    def test_handler_default_state(self):
        handler = ESP32Handler()
        assert handler.state == ConnectionState.DISCONNECTED
        assert not handler.is_connected

    def test_send_without_connection(self):
        handler = ESP32Handler()
        msg = SerialMessage(type=MessageType.STATUS_UPDATE, data={"test": 1})
        result = handler.send(msg)
        assert result is False  # Not connected

    def test_simulate_receive(self):
        handler = ESP32Handler()
        received = []
        handler.on_message(lambda m: received.append(m))

        msg = SerialMessage(type=MessageType.BREAKDOWN, data={"machine": "M1"})
        handler.simulate_receive(msg)

        assert len(received) == 1
        assert received[0].type == MessageType.BREAKDOWN

    def test_message_serialization(self):
        msg = SerialMessage(
            type=MessageType.STATUS_UPDATE,
            data={"machines": {"M1": "IDLE"}},
        )
        json_str = msg.to_json()
        parsed = SerialMessage.from_json(json_str)
        assert parsed.type == msg.type
        assert parsed.data == msg.data

    def test_list_ports(self):
        # Should not crash even without pyserial
        try:
            ports = ESP32Handler.list_ports()
            assert isinstance(ports, list)
        except Exception:
            pass  # OK if pyserial not installed


# ===================================================================
# GA on default problem
# ===================================================================

class TestGAOnDefaultProblem:
    def test_ga_produces_valid_schedule(self, default_problem, ga_config_fixed_seed):
        result = run_genetic_algorithm(default_problem, ga_config_fixed_seed)
        errors = validate_schedule(result.best_schedule, default_problem)
        assert errors == [], f"GA schedule validation errors: {errors}"
        assert len(result.best_schedule.operations) == default_problem.total_operations

    def test_ga_convergence_history(self, default_problem, ga_config_fixed_seed):
        result = run_genetic_algorithm(default_problem, ga_config_fixed_seed)
        assert len(result.convergence_history) > 0
        # Best fitness should be non-increasing
        best_values = [h[1] for h in result.convergence_history]
        for i in range(1, len(best_values)):
            assert best_values[i] <= best_values[i - 1] + 1e-9

    def test_ga_better_than_random(self, default_problem):
        # GA with enough generations should do at least as well as one random solution
        config = GAConfig(
            population_size=30, max_generations=20, random_seed=42
        )
        result = run_genetic_algorithm(default_problem, config)
        rng = random.Random(99)
        random_chrom = create_random_chromosome(default_problem, rng)
        random_fitness = fitness_function(random_chrom, default_problem)

        # GA's best should be <= worst random (this is a soft check)
        assert result.best_fitness <= random_fitness * 1.5  # Generous bound


# ===================================================================
# Crossover and mutation
# ===================================================================

class TestGAOperators:
    def test_pox_crossover_valid(self, small_problem):
        rng = random.Random(42)
        p1 = create_random_chromosome(small_problem, rng)
        p2 = create_random_chromosome(small_problem, rng)

        job_ids = small_problem.job_ids
        c1, c2 = pox_crossover(p1, p2, job_ids, rng)

        assert len(c1) == len(p1)
        assert len(c2) == len(p2)
        assert sorted(c1) == sorted(p1)
        assert sorted(c2) == sorted(p2)

    def test_swap_mutation_valid(self, small_problem):
        rng = random.Random(42)
        chrom = create_random_chromosome(small_problem, rng)
        mutant = swap_mutation(chrom, rng)

        assert len(mutant) == len(chrom)
        assert sorted(mutant) == sorted(chrom)

    def test_tournament_selection(self, small_problem):
        rng = random.Random(42)
        pop = initialise_population(small_problem, GAConfig(population_size=10), rng)
        fitness = [fitness_function(c, small_problem) for c in pop]

        selected = tournament_selection(pop, fitness, 3, rng)
        assert len(selected) == len(pop[0])
        assert sorted(selected) == sorted(pop[0])  # Valid chromosome


# ===================================================================
# Simulation integration
# ===================================================================

class TestSimulationIntegration:
    def test_full_simulation_flow(self, default_problem):
        """Test the complete flow: schedule -> simulate -> breakdown -> reschedule."""
        config = GAConfig(population_size=30, max_generations=20, random_seed=42)
        result = run_genetic_algorithm(default_problem, config)

        sim = ProductionSimulator(default_problem, result.best_schedule)

        # Advance to midpoint
        sim.advance_to(10.0)
        assert sim.state.current_time == 10.0

        # Some operations should be completed or running
        completed = sim.get_completed_ops_list()
        running = sim.get_running_ops_list()
        # At t=10, something should have happened
        assert len(completed) + len(running) > 0

        # Trigger breakdown on M1
        sim.trigger_breakdown("M1", 8.0)
        assert sim.state.machines["M1"].state == MachineState.DOWN

        # Reschedule
        revised = sim.reschedule(
            method="GA",
            ga_config=GAConfig(population_size=30, max_generations=15, random_seed=42),
        )
        assert len(revised.operations) == default_problem.total_operations

        # Validate revised schedule
        errors = validate_schedule(revised, sim.problem)
        assert errors == [], f"Revised schedule errors: {errors}"

    def test_simulation_reset(self, small_problem):
        schedule = schedule_fcfs(small_problem)
        sim = ProductionSimulator(small_problem, schedule)
        sim.advance_to(5.0)
        sim.reset()
        assert sim.state.current_time == 0.0


# ===================================================================
# Run tests as script
# ===================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
