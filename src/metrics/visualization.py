"""
Visualization module for Gantt charts and convergence plots.

Uses Plotly for interactive charts (used in Streamlit dashboard)
and Matplotlib as a fallback for static images.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.scheduler.models import ProblemInstance, Schedule, ScheduledOperation


# Job colour palette — 12 distinct colours
JOB_COLORS = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # grey
    "#bcbd22",  # olive
    "#17becf",  # cyan
    "#aec7e8",  # light blue
    "#ffbb78",  # light orange
]


def get_job_color(job_id: str, job_ids: List[str]) -> str:
    """Get a consistent colour for a job."""
    if job_id in job_ids:
        idx = job_ids.index(job_id)
    else:
        idx = hash(job_id)
    return JOB_COLORS[idx % len(JOB_COLORS)]


# ---------------------------------------------------------------------------
# Plotly Gantt Chart
# ---------------------------------------------------------------------------

def create_gantt_plotly(
    schedule: Schedule,
    problem: ProblemInstance,
    title: str = "Production Schedule — Gantt Chart",
    breakdown_events: Optional[List] = None,
    show_unavailability: bool = True,
) -> "plotly.graph_objects.Figure":
    """Create an interactive Plotly Gantt chart.

    Each row = a machine.  Each bar = an operation, coloured by job.
    """
    import plotly.graph_objects as go

    job_ids = problem.job_ids
    machine_ids = problem.machine_ids

    fig = go.Figure()

    # Draw unavailability intervals
    if show_unavailability:
        for mid, us, ue in problem.machine_unavailability:
            fig.add_trace(go.Bar(
                y=[mid],
                x=[ue - us],
                base=[us],
                orientation="h",
                marker=dict(
                    color="rgba(255, 0, 0, 0.2)",
                    line=dict(color="red", width=2),
                    pattern=dict(shape="/"),
                ),
                name=f"Downtime {mid}",
                showlegend=False,
                hovertemplate=(
                    f"Machine: {mid}<br>"
                    f"Downtime: {us} – {ue}<br>"
                    f"Duration: {ue - us}<extra></extra>"
                ),
            ))

    # Draw operations
    added_legend = set()
    for sop in sorted(schedule.operations, key=lambda o: (o.machine_id, o.start_time)):
        color = get_job_color(sop.job_id, job_ids)
        show_legend = sop.job_id not in added_legend
        added_legend.add(sop.job_id)

        fig.add_trace(go.Bar(
            y=[sop.machine_id],
            x=[sop.processing_time],
            base=[sop.start_time],
            orientation="h",
            marker=dict(color=color, line=dict(color="black", width=0.5)),
            name=sop.job_id,
            showlegend=show_legend,
            legendgroup=sop.job_id,
            text=f"{sop.job_id}-Op{sop.operation_no}",
            textposition="inside",
            hovertemplate=(
                f"Job: {sop.job_id}<br>"
                f"Operation: {sop.operation_no}<br>"
                f"Machine: {sop.machine_id}<br>"
                f"Start: {sop.start_time}<br>"
                f"End: {sop.completion_time}<br>"
                f"Duration: {sop.processing_time}"
                f"<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Machine",
        yaxis=dict(
            categoryorder="array",
            categoryarray=list(reversed(machine_ids)),
        ),
        barmode="overlay",
        height=max(300, 120 * len(machine_ids)),
        legend_title="Jobs",
    )

    return fig


def create_comparison_gantt_plotly(
    original: Schedule,
    revised: Schedule,
    problem: ProblemInstance,
) -> "plotly.graph_objects.Figure":
    """Create side-by-side Gantt charts for original and revised schedules."""
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Original Schedule", "Revised Schedule"),
        shared_xaxes=True,
        vertical_spacing=0.15,
    )

    job_ids = problem.job_ids
    machine_ids = problem.machine_ids

    for row_idx, (schedule, label) in enumerate(
        [(original, "Original"), (revised, "Revised")], start=1
    ):
        added_legend = set()
        for sop in sorted(
            schedule.operations, key=lambda o: (o.machine_id, o.start_time)
        ):
            color = get_job_color(sop.job_id, job_ids)
            show_legend = (
                sop.job_id not in added_legend and row_idx == 1
            )
            added_legend.add(sop.job_id)

            fig.add_trace(
                go.Bar(
                    y=[sop.machine_id],
                    x=[sop.processing_time],
                    base=[sop.start_time],
                    orientation="h",
                    marker=dict(
                        color=color, line=dict(color="black", width=0.5)
                    ),
                    name=sop.job_id,
                    showlegend=show_legend,
                    legendgroup=sop.job_id,
                    text=f"{sop.job_id}-Op{sop.operation_no}",
                    textposition="inside",
                ),
                row=row_idx,
                col=1,
            )

        # Draw unavailability
        for mid, us, ue in problem.machine_unavailability:
            fig.add_trace(
                go.Bar(
                    y=[mid],
                    x=[ue - us],
                    base=[us],
                    orientation="h",
                    marker=dict(
                        color="rgba(255,0,0,0.2)",
                        pattern=dict(shape="/"),
                    ),
                    showlegend=False,
                ),
                row=row_idx,
                col=1,
            )

    fig.update_layout(
        barmode="overlay",
        height=max(500, 200 * len(machine_ids)),
        legend_title="Jobs",
    )

    for i in range(1, 3):
        fig.update_yaxes(
            categoryorder="array",
            categoryarray=list(reversed(machine_ids)),
            row=i, col=1,
        )

    return fig


# ---------------------------------------------------------------------------
# Convergence Plot
# ---------------------------------------------------------------------------

def create_convergence_plot(
    convergence_history: List[Tuple[int, float, float]],
    title: str = "GA Convergence",
) -> "plotly.graph_objects.Figure":
    """Create a convergence plot showing best and average fitness per generation."""
    import plotly.graph_objects as go

    generations = [h[0] for h in convergence_history]
    best_fitness = [h[1] for h in convergence_history]
    avg_fitness = [h[2] for h in convergence_history]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=generations,
        y=best_fitness,
        mode="lines",
        name="Best Makespan",
        line=dict(color="#1f77b4", width=2),
    ))

    fig.add_trace(go.Scatter(
        x=generations,
        y=avg_fitness,
        mode="lines",
        name="Average Makespan",
        line=dict(color="#ff7f0e", width=1, dash="dash"),
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Generation",
        yaxis_title="Makespan",
        height=400,
    )

    return fig


# ---------------------------------------------------------------------------
# Matplotlib fallback
# ---------------------------------------------------------------------------

def create_gantt_matplotlib(
    schedule: Schedule,
    problem: ProblemInstance,
    title: str = "Production Schedule — Gantt Chart",
    save_path: Optional[str] = None,
):
    """Create a Matplotlib Gantt chart (for non-dashboard use)."""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    job_ids = problem.job_ids
    machine_ids = problem.machine_ids

    fig, ax = plt.subplots(figsize=(14, max(4, 2 * len(machine_ids))))

    y_positions = {mid: i for i, mid in enumerate(machine_ids)}

    for sop in schedule.operations:
        color = get_job_color(sop.job_id, job_ids)
        y = y_positions[sop.machine_id]
        ax.barh(
            y,
            sop.processing_time,
            left=sop.start_time,
            height=0.6,
            color=color,
            edgecolor="black",
            linewidth=0.5,
        )
        ax.text(
            sop.start_time + sop.processing_time / 2,
            y,
            f"{sop.job_id}\nOp{sop.operation_no}",
            ha="center",
            va="center",
            fontsize=7,
        )

    # Draw unavailability
    for mid, us, ue in problem.machine_unavailability:
        if mid in y_positions:
            y = y_positions[mid]
            ax.barh(
                y, ue - us, left=us, height=0.6,
                color="red", alpha=0.2, hatch="//",
            )

    ax.set_yticks(list(y_positions.values()))
    ax.set_yticklabels(list(y_positions.keys()))
    ax.set_xlabel("Time")
    ax.set_ylabel("Machine")
    ax.set_title(title)

    # Legend
    handles = [
        mpatches.Patch(color=get_job_color(jid, job_ids), label=jid)
        for jid in job_ids
    ]
    ax.legend(handles=handles, loc="upper right", fontsize=8)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        plt.close()
    else:
        plt.show()
