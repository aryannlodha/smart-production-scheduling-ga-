"""
Genetic Algorithm for Job Shop Scheduling Problem (JSSP).

This module implements a complete GA with:
  - Operation-based chromosome representation.
  - Precedence-preserving crossover (POX — Precedence Operation Crossover).
  - Swap mutation.
  - Tournament selection.
  - Elitism.
  - Configurable parameters with sensible defaults.

Chromosome representation
-------------------------
A chromosome is a list of job IDs where each job appears exactly as
many times as it has operations.  For example, with 3 jobs having
3, 2, and 2 operations respectively, a chromosome has length 7 and
contains J1 three times, J2 twice, J3 twice.

When decoding, the n-th occurrence of job J is mapped to J's n-th
operation.  This ensures job-precedence is always satisfied.

The GA is a *metaheuristic* — it searches for good (near-optimal)
solutions but does not guarantee finding the global optimum.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from src.scheduler.decoder import decode_chromosome, validate_schedule
from src.scheduler.models import (
    ProblemInstance,
    Schedule,
    ScheduledOperation,
)


# ---------------------------------------------------------------------------
# GA Configuration
# ---------------------------------------------------------------------------

@dataclass
class GAConfig:
    """Configuration parameters for the Genetic Algorithm.

    Attributes:
        population_size: Number of chromosomes per generation.
        max_generations: Maximum number of generations to evolve.
        crossover_prob: Probability of applying crossover to a pair.
        mutation_prob: Probability of applying mutation to a chromosome.
        elite_count: Number of top individuals preserved unchanged.
        tournament_size: Number of candidates in tournament selection.
        random_seed: Optional seed for reproducibility.  None = random.
    """
    population_size: int = 100
    max_generations: int = 100
    crossover_prob: float = 0.8
    mutation_prob: float = 0.1
    elite_count: int = 2
    tournament_size: int = 5
    random_seed: Optional[int] = None


@dataclass
class GAResult:
    """Results of a GA run.

    Attributes:
        best_schedule: The best schedule found.
        best_fitness: Best (lowest) makespan found.
        best_chromosome: The chromosome that produced the best schedule.
        convergence_history: List of (generation, best_fitness, avg_fitness).
        computation_time: Total GA computation time in seconds.
        generations_run: Actual number of generations completed.
        config: The GA configuration used.
    """
    best_schedule: Schedule
    best_fitness: float
    best_chromosome: List[str]
    convergence_history: List[Tuple[int, float, float]] = field(
        default_factory=list
    )
    computation_time: float = 0.0
    generations_run: int = 0
    config: GAConfig = field(default_factory=GAConfig)


# ---------------------------------------------------------------------------
# Fitness evaluation
# ---------------------------------------------------------------------------

def calculate_makespan(schedule: Schedule) -> float:
    """Calculate makespan = max completion time across all operations."""
    if not schedule.operations:
        return 0.0
    return max(op.completion_time for op in schedule.operations)


def fitness_function(
    chromosome: List[str],
    problem: ProblemInstance,
    completed_ops: Optional[Dict[Tuple[str, int], ScheduledOperation]] = None,
    machine_available_times: Optional[Dict[str, float]] = None,
    job_available_times: Optional[Dict[str, float]] = None,
) -> float:
    """Evaluate fitness of a chromosome.  Lower = better (minimising makespan)."""
    schedule = decode_chromosome(
        chromosome, problem, completed_ops,
        machine_available_times, job_available_times,
    )
    return calculate_makespan(schedule)


# ---------------------------------------------------------------------------
# Population initialisation
# ---------------------------------------------------------------------------

def create_random_chromosome(
    problem: ProblemInstance,
    rng: random.Random,
    completed_ops: Optional[Dict[Tuple[str, int], ScheduledOperation]] = None,
) -> List[str]:
    """Create a random valid chromosome for the problem.

    Each job J appears exactly (num_operations - completed_for_J) times.
    """
    if completed_ops is None:
        completed_ops = {}

    chromosome: List[str] = []
    for job in problem.jobs.values():
        remaining = sum(
            1 for op in job.operations
            if (op.job_id, op.operation_no) not in completed_ops
        )
        chromosome.extend([job.job_id] * remaining)

    rng.shuffle(chromosome)
    return chromosome


def initialise_population(
    problem: ProblemInstance,
    config: GAConfig,
    rng: random.Random,
    completed_ops: Optional[Dict[Tuple[str, int], ScheduledOperation]] = None,
) -> List[List[str]]:
    """Create initial population of random chromosomes."""
    return [
        create_random_chromosome(problem, rng, completed_ops)
        for _ in range(config.population_size)
    ]


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def tournament_selection(
    population: List[List[str]],
    fitness_values: List[float],
    tournament_size: int,
    rng: random.Random,
) -> List[str]:
    """Select one individual via tournament selection.

    Randomly pick `tournament_size` individuals and return the one with
    the best (lowest) fitness.
    """
    indices = rng.sample(range(len(population)), min(tournament_size, len(population)))
    best_idx = min(indices, key=lambda i: fitness_values[i])
    return list(population[best_idx])  # Return a copy


# ---------------------------------------------------------------------------
# Crossover: Precedence Operation Crossover (POX)
# ---------------------------------------------------------------------------

def pox_crossover(
    parent1: List[str],
    parent2: List[str],
    job_ids: List[str],
    rng: random.Random,
) -> Tuple[List[str], List[str]]:
    """Precedence Operation Crossover (POX).

    1. Randomly divide job IDs into two sets: Set1 and Set2.
    2. For child1:
       - Copy positions from parent1 where the job ∈ Set1 (in order).
       - Fill remaining positions with jobs from parent2 where job ∈ Set2
         (in the order they appear in parent2).
    3. For child2: swap the roles of parent1 and parent2.

    This always produces valid chromosomes because:
    - Each job appears the correct number of times.
    - The relative order of operations within each job set is preserved.

    Reference: Operation-based crossover operators for JSSP, adapted from
    Gen & Cheng (1997) and Shi et al. (2006).
    """
    if len(parent1) != len(parent2):
        raise ValueError("Parents must have the same length")

    # Divide jobs into two non-empty sets
    shuffled_jobs = list(job_ids)
    rng.shuffle(shuffled_jobs)
    split = rng.randint(1, max(1, len(shuffled_jobs) - 1))
    set1 = set(shuffled_jobs[:split])
    set2 = set(shuffled_jobs[split:])

    def _make_child(
        primary: List[str], secondary: List[str],
        primary_set: set, secondary_set: set
    ) -> List[str]:
        child = [None] * len(primary)  # type: ignore

        # Place primary set jobs from primary parent in their positions
        for i, gene in enumerate(primary):
            if gene in primary_set:
                child[i] = gene

        # Collect secondary set genes from secondary parent in order
        secondary_genes = [g for g in secondary if g in secondary_set]

        # Fill empty slots with secondary genes
        idx = 0
        for i in range(len(child)):
            if child[i] is None:
                child[i] = secondary_genes[idx]
                idx += 1

        return child  # type: ignore

    child1 = _make_child(parent1, parent2, set1, set2)
    child2 = _make_child(parent2, parent1, set1, set2)

    return child1, child2


# ---------------------------------------------------------------------------
# Mutation: Swap mutation
# ---------------------------------------------------------------------------

def swap_mutation(
    chromosome: List[str], rng: random.Random
) -> List[str]:
    """Swap two random positions in the chromosome.

    This always produces a valid chromosome because swapping does not
    change the count of each job ID.
    """
    if len(chromosome) < 2:
        return list(chromosome)

    mutant = list(chromosome)
    i, j = rng.sample(range(len(mutant)), 2)
    mutant[i], mutant[j] = mutant[j], mutant[i]
    return mutant


# ---------------------------------------------------------------------------
# Main GA loop
# ---------------------------------------------------------------------------

def run_genetic_algorithm(
    problem: ProblemInstance,
    config: Optional[GAConfig] = None,
    completed_ops: Optional[Dict[Tuple[str, int], ScheduledOperation]] = None,
    machine_available_times: Optional[Dict[str, float]] = None,
    job_available_times: Optional[Dict[str, float]] = None,
    progress_callback: Optional[Callable[[int, float, float], None]] = None,
) -> GAResult:
    """Run the Genetic Algorithm to minimise makespan.

    Args:
        problem: The JSSP problem instance.
        config: GA parameters (defaults used if None).
        completed_ops: Already-completed operations (for rescheduling).
        machine_available_times: Override machine availability.
        job_available_times: Override job availability.
        progress_callback: Optional function(gen, best_fitness, avg_fitness)
            called after each generation.

    Returns:
        GAResult with the best schedule, convergence history, etc.
    """
    if config is None:
        config = GAConfig()

    rng = random.Random(config.random_seed)
    t_start = time.perf_counter()

    # Remaining job IDs (those with remaining ops)
    if completed_ops is None:
        completed_ops = {}

    remaining_job_ids = []
    for job in problem.jobs.values():
        remaining = sum(
            1 for op in job.operations
            if (op.job_id, op.operation_no) not in completed_ops
        )
        if remaining > 0:
            remaining_job_ids.append(job.job_id)

    if not remaining_job_ids:
        # Nothing to schedule
        return GAResult(
            best_schedule=Schedule(
                operations=list(completed_ops.values()),
                method="GA",
            ),
            best_fitness=calculate_makespan(
                Schedule(operations=list(completed_ops.values()))
            ),
            best_chromosome=[],
            computation_time=time.perf_counter() - t_start,
            generations_run=0,
            config=config,
        )

    # Initialise population
    population = initialise_population(problem, config, rng, completed_ops)

    # Evaluate initial population
    fitness_values = [
        fitness_function(
            chrom, problem, completed_ops,
            machine_available_times, job_available_times,
        )
        for chrom in population
    ]

    convergence_history: List[Tuple[int, float, float]] = []

    best_overall_fitness = min(fitness_values)
    best_overall_idx = fitness_values.index(best_overall_fitness)
    best_overall_chrom = list(population[best_overall_idx])

    # Record gen 0
    avg_fitness = sum(fitness_values) / len(fitness_values)
    convergence_history.append((0, best_overall_fitness, avg_fitness))

    if progress_callback:
        progress_callback(0, best_overall_fitness, avg_fitness)

    # Evolution loop
    for gen in range(1, config.max_generations + 1):
        new_population: List[List[str]] = []

        # Elitism: carry over the best individuals
        sorted_indices = sorted(
            range(len(population)), key=lambda i: fitness_values[i]
        )
        for i in range(min(config.elite_count, len(population))):
            new_population.append(list(population[sorted_indices[i]]))

        # Fill the rest via selection, crossover, mutation
        while len(new_population) < config.population_size:
            # Selection
            p1 = tournament_selection(
                population, fitness_values, config.tournament_size, rng
            )
            p2 = tournament_selection(
                population, fitness_values, config.tournament_size, rng
            )

            # Crossover
            if rng.random() < config.crossover_prob:
                c1, c2 = pox_crossover(p1, p2, remaining_job_ids, rng)
            else:
                c1, c2 = list(p1), list(p2)

            # Mutation
            if rng.random() < config.mutation_prob:
                c1 = swap_mutation(c1, rng)
            if rng.random() < config.mutation_prob:
                c2 = swap_mutation(c2, rng)

            new_population.append(c1)
            if len(new_population) < config.population_size:
                new_population.append(c2)

        population = new_population

        # Evaluate
        fitness_values = [
            fitness_function(
                chrom, problem, completed_ops,
                machine_available_times, job_available_times,
            )
            for chrom in population
        ]

        gen_best = min(fitness_values)
        gen_avg = sum(fitness_values) / len(fitness_values)

        if gen_best < best_overall_fitness:
            best_overall_fitness = gen_best
            best_idx = fitness_values.index(gen_best)
            best_overall_chrom = list(population[best_idx])

        convergence_history.append((gen, best_overall_fitness, gen_avg))

        if progress_callback:
            progress_callback(gen, best_overall_fitness, gen_avg)

    t_end = time.perf_counter()

    # Decode the best chromosome into the final schedule
    best_schedule = decode_chromosome(
        best_overall_chrom, problem, completed_ops,
        machine_available_times, job_available_times,
    )
    best_schedule.method = "GA"
    best_schedule.computation_time = t_end - t_start

    return GAResult(
        best_schedule=best_schedule,
        best_fitness=best_overall_fitness,
        best_chromosome=best_overall_chrom,
        convergence_history=convergence_history,
        computation_time=t_end - t_start,
        generations_run=config.max_generations,
        config=config,
    )
