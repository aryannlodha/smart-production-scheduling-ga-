"""
Streamlit Dashboard for Smart Production Scheduling System.

Run with: streamlit run app.py

Pages:
  1. Production Inputs
  2. Scheduling
  3. Results
  4. Gantt Chart
  5. Dynamic Rescheduling
  6. Hardware Status
"""

import os
import sys
import time
import json
import pandas as pd
import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scheduler.models import (
    ProblemInstance,
    Schedule,
    load_problem_from_csv,
    create_problem_from_dicts,
    validate_problem,
    BreakdownEvent,
)
from src.scheduler.decoder import decode_chromosome, validate_schedule
from src.genetic_algorithm.ga import (
    GAConfig,
    GAResult,
    run_genetic_algorithm,
    calculate_makespan,
)
from src.baselines.dispatching import schedule_fcfs, schedule_spt, schedule_edd
from src.metrics.performance import (
    calculate_metrics,
    ScheduleMetrics,
    compare_schedules,
    format_comparison_table,
)
from src.metrics.visualization import (
    create_gantt_plotly,
    create_comparison_gantt_plotly,
    create_convergence_plot,
)
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

# ===== Page Config =====
st.set_page_config(
    page_title="Smart Production Scheduling",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Session State Init =====
def init_session_state():
    defaults = {
        "problem": None,
        "schedules": {},          # method -> Schedule
        "metrics": {},            # method -> ScheduleMetrics
        "ga_result": None,
        "simulator": None,
        "esp32_handler": None,
        "data_loaded": False,
        "jobs_df": None,
        "ops_df": None,
        "machines_df": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()


# ===== Sidebar Navigation =====
st.sidebar.title("🏭 Smart Scheduling")
page = st.sidebar.radio(
    "Navigate",
    [
        "📋 Production Inputs",
        "⚙️ Scheduling",
        "📊 Results",
        "📈 Gantt Chart",
        "🔧 Dynamic Rescheduling",
        "🔌 Hardware Status",
    ],
)


# ===== Helper Functions =====

def load_default_data():
    """Load the default CSV data files."""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    jobs_df = pd.read_csv(os.path.join(data_dir, "jobs.csv"))
    ops_df = pd.read_csv(os.path.join(data_dir, "operations.csv"))
    machines_df = pd.read_csv(os.path.join(data_dir, "machines.csv"))
    return jobs_df, ops_df, machines_df


def build_problem_from_dfs(jobs_df, ops_df, machines_df):
    """Build a ProblemInstance from DataFrames."""
    return create_problem_from_dicts(
        jobs_data=jobs_df.to_dict("records"),
        operations_data=ops_df.to_dict("records"),
        machines_data=machines_df.to_dict("records"),
    )


def schedule_to_df(schedule: Schedule) -> pd.DataFrame:
    """Convert a schedule to a DataFrame."""
    rows = []
    for sop in sorted(schedule.operations, key=lambda o: (o.machine_id, o.start_time)):
        rows.append({
            "Job": sop.job_id,
            "Operation": sop.operation_no,
            "Machine": sop.machine_id,
            "Processing Time": sop.processing_time,
            "Start": sop.start_time,
            "End": sop.completion_time,
        })
    return pd.DataFrame(rows)


def metrics_to_df(metrics_dict: dict) -> pd.DataFrame:
    """Convert metrics dictionary to a comparison DataFrame."""
    rows = []
    for method, m in metrics_dict.items():
        rows.append({
            "Method": method,
            "Makespan": m.makespan,
            "Total Tardiness": m.total_tardiness,
            "Avg Utilization (%)": round(m.avg_utilization_pct, 1),
            "Total Idle Time": m.total_idle_time,
            "Computation Time (s)": round(m.computation_time, 4),
        })
    return pd.DataFrame(rows)


# =====================================================================
# Page 1: Production Inputs
# =====================================================================

if page == "📋 Production Inputs":
    st.title("📋 Production Inputs")
    st.markdown("""
    Configure the Job Shop Scheduling Problem (JSSP) instance.
    Edit the tables below or upload your own CSV files.
    """)

    # Load defaults
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📂 Load Default Data", type="primary"):
            jobs_df, ops_df, machines_df = load_default_data()
            st.session_state.jobs_df = jobs_df
            st.session_state.ops_df = ops_df
            st.session_state.machines_df = machines_df
            st.success("Default data loaded!")

    with col2:
        uploaded_jobs = st.file_uploader("Upload jobs.csv", type="csv", key="up_jobs")
        uploaded_ops = st.file_uploader("Upload operations.csv", type="csv", key="up_ops")
        uploaded_machines = st.file_uploader("Upload machines.csv", type="csv", key="up_machines")

        if uploaded_jobs and uploaded_ops and uploaded_machines:
            st.session_state.jobs_df = pd.read_csv(uploaded_jobs)
            st.session_state.ops_df = pd.read_csv(uploaded_ops)
            st.session_state.machines_df = pd.read_csv(uploaded_machines)
            st.success("Custom data uploaded!")

    # Display editable tables
    if st.session_state.jobs_df is not None:
        st.subheader("Jobs")
        st.session_state.jobs_df = st.data_editor(
            st.session_state.jobs_df,
            num_rows="dynamic",
            key="jobs_editor",
        )

        st.subheader("Operations (Job Routes)")
        st.session_state.ops_df = st.data_editor(
            st.session_state.ops_df,
            num_rows="dynamic",
            key="ops_editor",
        )

        st.subheader("Machines")
        st.session_state.machines_df = st.data_editor(
            st.session_state.machines_df,
            num_rows="dynamic",
            key="machines_editor",
        )

        # Build problem
        if st.button("✅ Validate & Build Problem", type="primary"):
            try:
                problem = build_problem_from_dfs(
                    st.session_state.jobs_df,
                    st.session_state.ops_df,
                    st.session_state.machines_df,
                )
                st.session_state.problem = problem
                st.session_state.data_loaded = True
                st.success(
                    f"✅ Problem built: {problem.num_jobs} jobs, "
                    f"{problem.num_machines} machines, "
                    f"{problem.total_operations} operations"
                )

                # Show routes summary
                st.subheader("Job Routes Summary")
                for jid in problem.job_ids:
                    job = problem.jobs[jid]
                    route = " → ".join(
                        f"{op.machine_id}({op.processing_time})"
                        for op in job.operations
                    )
                    st.write(f"**{jid}**: {route}  |  Due: {job.due_date}")

            except Exception as e:
                st.error(f"❌ Validation Error: {e}")

        # Download buttons
        if st.session_state.jobs_df is not None:
            st.subheader("Download Data")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    "📥 jobs.csv",
                    st.session_state.jobs_df.to_csv(index=False),
                    "jobs.csv",
                )
            with col2:
                st.download_button(
                    "📥 operations.csv",
                    st.session_state.ops_df.to_csv(index=False),
                    "operations.csv",
                )
            with col3:
                st.download_button(
                    "📥 machines.csv",
                    st.session_state.machines_df.to_csv(index=False),
                    "machines.csv",
                )
    else:
        st.info("👆 Click 'Load Default Data' or upload your own CSV files to begin.")


# =====================================================================
# Page 2: Scheduling
# =====================================================================

elif page == "⚙️ Scheduling":
    st.title("⚙️ Run Scheduling Algorithms")

    if not st.session_state.data_loaded:
        st.warning("⚠️ Please load and validate data on the Production Inputs page first.")
        st.stop()

    problem = st.session_state.problem

    st.subheader("GA Configuration")
    col1, col2, col3 = st.columns(3)
    with col1:
        pop_size = st.number_input("Population Size", 10, 500, 100)
        max_gen = st.number_input("Max Generations", 10, 1000, 100)
    with col2:
        cx_prob = st.slider("Crossover Probability", 0.0, 1.0, 0.8)
        mut_prob = st.slider("Mutation Probability", 0.0, 1.0, 0.1)
    with col3:
        elite = st.number_input("Elitism", 1, 10, 2)
        seed = st.number_input("Random Seed (0=random)", 0, 99999, 42)

    ga_config = GAConfig(
        population_size=pop_size,
        max_generations=max_gen,
        crossover_prob=cx_prob,
        mutation_prob=mut_prob,
        elite_count=elite,
        tournament_size=5,
        random_seed=seed if seed > 0 else None,
    )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Run FCFS", type="secondary"):
            sched = schedule_fcfs(problem)
            m = calculate_metrics(sched, problem)
            st.session_state.schedules["FCFS"] = sched
            st.session_state.metrics["FCFS"] = m
            st.success(f"FCFS: Makespan = {m.makespan}, Time = {m.computation_time:.4f}s")

    with col2:
        if st.button("Run SPT", type="secondary"):
            sched = schedule_spt(problem)
            m = calculate_metrics(sched, problem)
            st.session_state.schedules["SPT"] = sched
            st.session_state.metrics["SPT"] = m
            st.success(f"SPT: Makespan = {m.makespan}, Time = {m.computation_time:.4f}s")

    with col3:
        if st.button("Run EDD", type="secondary"):
            sched = schedule_edd(problem)
            m = calculate_metrics(sched, problem)
            st.session_state.schedules["EDD"] = sched
            st.session_state.metrics["EDD"] = m
            st.success(f"EDD: Makespan = {m.makespan}, Time = {m.computation_time:.4f}s")

    with col4:
        if st.button("🧬 Run GA", type="primary"):
            with st.spinner("Running Genetic Algorithm..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_cb(gen, best, avg):
                    pct = min(gen / max_gen, 1.0)
                    progress_bar.progress(pct)
                    status_text.text(
                        f"Gen {gen}/{max_gen} — Best: {best:.1f}, Avg: {avg:.1f}"
                    )

                result = run_genetic_algorithm(
                    problem, ga_config, progress_callback=progress_cb
                )
                progress_bar.progress(1.0)

            m = calculate_metrics(result.best_schedule, problem)
            st.session_state.schedules["GA"] = result.best_schedule
            st.session_state.metrics["GA"] = m
            st.session_state.ga_result = result
            st.success(
                f"🧬 GA: Makespan = {m.makespan}, "
                f"Time = {result.computation_time:.4f}s"
            )

    # Run all button
    st.divider()
    if st.button("🚀 Run All Methods", type="primary"):
        with st.spinner("Running all scheduling methods..."):
            for name, fn in [("FCFS", schedule_fcfs), ("SPT", schedule_spt), ("EDD", schedule_edd)]:
                sched = fn(problem)
                m = calculate_metrics(sched, problem)
                st.session_state.schedules[name] = sched
                st.session_state.metrics[name] = m

            result = run_genetic_algorithm(problem, ga_config)
            m = calculate_metrics(result.best_schedule, problem)
            st.session_state.schedules["GA"] = result.best_schedule
            st.session_state.metrics["GA"] = m
            st.session_state.ga_result = result

        st.success("✅ All methods completed!")

    # Show current results if available
    if st.session_state.schedules:
        st.subheader("Completed Runs")
        for method in st.session_state.schedules:
            m = st.session_state.metrics.get(method)
            if m:
                st.write(f"**{method}**: Makespan = {m.makespan}")


# =====================================================================
# Page 3: Results
# =====================================================================

elif page == "📊 Results":
    st.title("📊 Results Comparison")

    if not st.session_state.metrics:
        st.warning("⚠️ Run scheduling algorithms first on the Scheduling page.")
        st.stop()

    problem = st.session_state.problem
    metrics = st.session_state.metrics

    # Comparison table
    st.subheader("Performance Comparison")
    df = metrics_to_df(metrics)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Highlight best
    if len(df) > 1:
        best_method = df.loc[df["Makespan"].idxmin(), "Method"]
        st.success(f"🏆 Best makespan: **{best_method}** with {df['Makespan'].min()}")

    # Per-machine utilization
    st.subheader("Machine Utilization")
    util_rows = []
    for method, m in metrics.items():
        for mid, mm in sorted(m.machine_metrics.items()):
            util_rows.append({
                "Method": method,
                "Machine": mid,
                "Busy Time": mm.busy_time,
                "Idle Time": mm.idle_time,
                "Utilization (%)": round(mm.utilization_pct, 1),
                "Operations": mm.num_operations,
            })
    if util_rows:
        st.dataframe(pd.DataFrame(util_rows), use_container_width=True, hide_index=True)

    # Per-job tardiness
    st.subheader("Job Tardiness")
    tard_rows = []
    for method, m in metrics.items():
        for jid, jm in sorted(m.job_metrics.items()):
            tard_rows.append({
                "Method": method,
                "Job": jid,
                "Completion": jm.completion_time,
                "Due Date": jm.due_date,
                "Tardiness": jm.tardiness,
            })
    if tard_rows:
        st.dataframe(pd.DataFrame(tard_rows), use_container_width=True, hide_index=True)

    # GA convergence
    if st.session_state.ga_result:
        st.subheader("GA Convergence")
        fig = create_convergence_plot(st.session_state.ga_result.convergence_history)
        st.plotly_chart(fig, use_container_width=True)

    # Download results
    st.subheader("Export Results")
    csv_data = df.to_csv(index=False)
    st.download_button("📥 Download comparison.csv", csv_data, "comparison.csv")


# =====================================================================
# Page 4: Gantt Chart
# =====================================================================

elif page == "📈 Gantt Chart":
    st.title("📈 Gantt Chart")

    if not st.session_state.schedules:
        st.warning("⚠️ Run scheduling algorithms first.")
        st.stop()

    problem = st.session_state.problem
    schedules = st.session_state.schedules

    selected = st.selectbox("Select Method", list(schedules.keys()))

    if selected:
        schedule = schedules[selected]
        fig = create_gantt_plotly(schedule, problem, f"{selected} Schedule")
        st.plotly_chart(fig, use_container_width=True)

        # Show schedule table
        with st.expander("📋 Schedule Details"):
            st.dataframe(schedule_to_df(schedule), use_container_width=True, hide_index=True)

    # Compare two methods
    if len(schedules) >= 2:
        st.subheader("Compare Two Schedules")
        col1, col2 = st.columns(2)
        methods = list(schedules.keys())
        with col1:
            m1 = st.selectbox("Method 1", methods, index=0, key="cmp1")
        with col2:
            m2 = st.selectbox("Method 2", methods, index=min(1, len(methods) - 1), key="cmp2")

        if m1 and m2:
            col1, col2 = st.columns(2)
            with col1:
                fig1 = create_gantt_plotly(schedules[m1], problem, m1)
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = create_gantt_plotly(schedules[m2], problem, m2)
                st.plotly_chart(fig2, use_container_width=True)


# =====================================================================
# Page 5: Dynamic Rescheduling
# =====================================================================

elif page == "🔧 Dynamic Rescheduling":
    st.title("🔧 Dynamic Rescheduling Simulation")

    if not st.session_state.data_loaded:
        st.warning("⚠️ Please load data and run scheduling first.")
        st.stop()

    problem = st.session_state.problem

    # Pick initial schedule
    if st.session_state.schedules:
        base_method = st.selectbox(
            "Base Schedule",
            list(st.session_state.schedules.keys()),
            index=list(st.session_state.schedules.keys()).index("GA")
            if "GA" in st.session_state.schedules else 0,
        )
        base_schedule = st.session_state.schedules[base_method]
    else:
        st.info("Run a scheduling algorithm first, or use FCFS as default.")
        base_schedule = schedule_fcfs(problem)
        base_method = "FCFS"

    # Simulation controls
    st.subheader("Simulation Setup")
    col1, col2, col3 = st.columns(3)
    with col1:
        breakdown_machine = st.selectbox("Machine to Fail", problem.machine_ids)
    with col2:
        breakdown_time = st.number_input(
            "Breakdown Time", 0.0, 200.0, 10.0, step=1.0
        )
    with col3:
        repair_duration = st.number_input(
            "Repair Duration", 1.0, 50.0, 8.0, step=1.0
        )

    policy = st.selectbox(
        "Interruption Policy",
        ["RESUME (continue with remaining time)", "RESTART (restart operation)"],
    )
    int_policy = (
        InterruptionPolicy.RESUME if "RESUME" in policy
        else InterruptionPolicy.RESTART
    )

    reschedule_method = st.selectbox(
        "Rescheduling Method", ["GA", "FCFS", "SPT", "EDD"]
    )

    st.divider()

    # Run simulation
    if st.button("🚀 Run Breakdown Simulation", type="primary"):
        with st.spinner("Simulating breakdown and rescheduling..."):
            # Create fresh simulator
            sim = ProductionSimulator(problem, base_schedule, int_policy)

            # Advance to breakdown
            sim.advance_to(breakdown_time)

            completed_before = sim.get_completed_ops_list()
            running_before = sim.get_running_ops_list()

            # Show state at breakdown
            st.subheader(f"State at t = {breakdown_time}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Completed Ops", len(completed_before))
            with col2:
                st.metric("Running Ops", len(running_before))
            with col3:
                st.metric("Waiting Ops", len(sim.get_waiting_ops_list()))

            # Trigger breakdown
            event = sim.trigger_breakdown(
                breakdown_machine, repair_duration, breakdown_time
            )

            st.error(
                f"💥 **BREAKDOWN**: {breakdown_machine} failed at t={breakdown_time}. "
                f"Repair ends at t={event.repair_end_time}"
            )

            paused = sim.get_paused_ops_list()
            if paused:
                st.warning(
                    f"⏸️ Paused operations: "
                    + ", ".join(f"{j}-Op{o}" for j, o in paused)
                )

            # Reschedule
            ga_cfg = GAConfig(
                population_size=80, max_generations=50,
                random_seed=42
            )
            revised = sim.reschedule(
                method=reschedule_method,
                ga_config=ga_cfg,
            )

            st.success("✅ Rescheduling complete!")

            # Show metrics comparison
            st.subheader("KPI Comparison")
            orig_m = sim.state.original_metrics
            rev_m = sim.state.revised_metrics

            if orig_m and rev_m:
                kpi_df = pd.DataFrame([
                    {
                        "Metric": "Makespan",
                        "Original": orig_m.makespan,
                        "Revised": rev_m.makespan,
                        "Change": f"{(rev_m.makespan - orig_m.makespan) / orig_m.makespan * 100:+.1f}%"
                        if orig_m.makespan > 0 else "N/A",
                    },
                    {
                        "Metric": "Total Tardiness",
                        "Original": orig_m.total_tardiness,
                        "Revised": rev_m.total_tardiness,
                        "Change": f"{rev_m.total_tardiness - orig_m.total_tardiness:+.1f}",
                    },
                    {
                        "Metric": "Avg Utilization (%)",
                        "Original": round(orig_m.avg_utilization_pct, 1),
                        "Revised": round(rev_m.avg_utilization_pct, 1),
                        "Change": f"{rev_m.avg_utilization_pct - orig_m.avg_utilization_pct:+.1f}%",
                    },
                ])
                st.dataframe(kpi_df, use_container_width=True, hide_index=True)

            # Show Gantt charts
            st.subheader("Original Schedule")
            fig_orig = create_gantt_plotly(
                sim.state.original_schedule, problem, "Original Schedule"
            )
            st.plotly_chart(fig_orig, use_container_width=True)

            st.subheader("Revised Schedule (After Breakdown)")
            fig_rev = create_gantt_plotly(
                revised, sim.problem, "Revised Schedule",
            )
            st.plotly_chart(fig_rev, use_container_width=True)

            st.session_state.simulator = sim


# =====================================================================
# Page 6: Hardware Status
# =====================================================================

elif page == "🔌 Hardware Status":
    st.title("🔌 ESP32 Hardware Status")

    # Initialize handler
    if st.session_state.esp32_handler is None:
        st.session_state.esp32_handler = ESP32Handler()

    handler = st.session_state.esp32_handler

    # Connection controls
    st.subheader("Serial Connection")
    col1, col2, col3 = st.columns(3)

    with col1:
        ports = ESP32Handler.list_ports()
        if ports:
            port = st.selectbox("Serial Port", ports)
        else:
            port = st.text_input("Serial Port", "COM3")

    with col2:
        baud = st.selectbox("Baud Rate", [115200, 9600, 57600], index=0)

    with col3:
        st.write("")  # Spacing
        st.write("")
        if not handler.is_connected:
            if st.button("🔗 Connect"):
                success = handler.connect(port, baud)
                if success:
                    st.success(f"Connected to {port}")
                else:
                    st.error(f"Failed to connect to {port}")
                st.rerun()
        else:
            if st.button("🔌 Disconnect"):
                handler.disconnect()
                st.info("Disconnected")
                st.rerun()

    # Status display
    st.subheader("Connection Status")
    status_color = {
        ConnectionState.CONNECTED: "🟢",
        ConnectionState.DISCONNECTED: "⚪",
        ConnectionState.CONNECTING: "🟡",
        ConnectionState.ERROR: "🔴",
    }

    st.write(
        f"Status: {status_color.get(handler.state, '❓')} **{handler.state.value}**"
    )

    if handler.is_connected:
        st.write(f"Port: **{handler.port}**")

    # Machine status (simulated)
    st.subheader("Machine Status Display")
    if st.session_state.simulator:
        sim = st.session_state.simulator
        for mid in sim.problem.machine_ids:
            ms = sim.state.machines.get(mid)
            if ms:
                icon = {
                    MachineState.IDLE: "🟢",
                    MachineState.BUSY: "🟡",
                    MachineState.DOWN: "🔴",
                }.get(ms.state, "⚪")
                st.write(f"{icon} **{mid}**: {ms.state.value}")
    else:
        st.info("Run a simulation to see machine states.")

    # Manual message sending
    st.subheader("Manual Controls")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📡 Send Status Request"):
            handler.send(SerialMessage(type=MessageType.STATUS_REQUEST))
            st.info("Status request sent")
    with col2:
        if st.button("▶️ Send Start"):
            handler.send(SerialMessage(type=MessageType.START))
            st.info("Start command sent")
    with col3:
        if st.button("🔄 Send Reset"):
            handler.send(SerialMessage(type=MessageType.RESET))
            st.info("Reset command sent")

    # Message log
    st.subheader("Message Log")
    if handler.message_log:
        for msg in reversed(handler.message_log[-20:]):
            st.code(msg.to_json(), language="json")
    else:
        st.info("No messages yet.")

    # Software-only mode note
    if not handler.is_connected:
        st.info(
            "📢 **Software-only mode**: The dashboard functions fully without "
            "hardware. Connect an ESP32 via USB for physical controls."
        )
