# Experiment runner and plotting helpers for the main scenario suite
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from .config import SCENARIOS
from .data_generation import export_instance, generate_instance
from .models import ModelResult, ObjectiveWeights, solve_integrated_model, solve_sequential_benchmark
from .validation import build_instance_profile, validate_result

MODEL_ORDER = ["integrated_exact", "sequential_benchmark"]
KPI_METRICS = [
    "labour_cost",
    "weighted_flow_time",
    "mean_flow_time_periods",
    "regular_worker_hours",
    "temp_worker_hours",
    "balance_deviation",
]
KPI_TITLES = {
    "labour_cost": "labour_cost",
    "weighted_flow_time": "weighted_flow_time",
    "mean_flow_time_periods": "mean_flow_time_periods",
    "regular_worker_hours": "regular_worker_hours",
    "temp_worker_hours": "temp_worker_hours",
    "balance_deviation": "balance_deviation",
}


@dataclass
class ExperimentSuiteResult:
    # Bundle the exported tables and raw model results from one run
    summary: pd.DataFrame
    comparison: pd.DataFrame
    profiles: pd.DataFrame
    validation: pd.DataFrame
    results: list[ModelResult]

def _ensure_output_dirs(output_dir: str | Path) -> dict[str, Path]:
    # Create the standard output directory structure
    base_path = Path(output_dir)
    directories = {
        "root": base_path,
        "instances": base_path / "instances",
        "tables": base_path / "tables",
        "figures": base_path / "figures",
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    return directories

def _save_result_tables(result: ModelResult, output_dir: Path) -> None:
    # Write per-model assignment and staffing tables to disk
    result.assignment.to_csv(output_dir / f"{result.scenario_name}_{result.model_name}_assignments.csv", index=False)
    result.staffing.to_csv(output_dir / f"{result.scenario_name}_{result.model_name}_staffing.csv", index=False)

def _build_staffing_plot(scenario_name: str, results: list[ModelResult], figure_path: Path) -> None:
    # Plot workload and staffing profiles for one scenario
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    for result in results:
        data = result.staffing.copy()
        axes[0].plot(data["period"], data["total_load_minutes"], marker="o", linewidth=2, label=f"{result.model_name} workload")
        axes[0].plot(
            data["period"],
            data["direct_workers"] * 30,
            marker="s",
            linewidth=2,
            linestyle="--",
            label=f"{result.model_name} direct staff x30",
        )
        axes[1].plot(
            data["period"],
            data["total_available_workers"],
            marker="o",
            linewidth=2,
            label=f"{result.model_name} available",
        )
        axes[1].plot(
            data["period"],
            data["unused_capacity_workers"],
            marker="s",
            linewidth=2,
            linestyle="--",
            label=f"{result.model_name} unused",
        )
    axes[0].set_title(f"{scenario_name}: workload and direct staffing by period")
    axes[0].set_ylabel("Minutes / scaled workers")
    axes[1].set_title(f"{scenario_name}: available vs unused capacity")
    axes[1].set_ylabel("Workers")
    axes[1].set_xlabel("Period")
    for axis in axes:
        axis.grid(alpha=0.2)
        axis.legend()
    fig.tight_layout()
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

def _build_kpi_plot(summary: pd.DataFrame, figure_path: Path) -> None:
    # Build the report-ready KPI comparison grid
    # The KPI grid is meant for report-ready comparison, so we keep the plotted metric list explicit and stable across reruns
    # Service-guarantee metrics such as late_orders stay in the tables, but degenerate metrics are excluded from the main chart when they carry no comparative information.
    plot_data = summary.melt(
        id_vars=["scenario", "model"],
        value_vars=KPI_METRICS,
        var_name="metric",
        value_name="value",
    )
    palette = dict(zip(MODEL_ORDER, sns.color_palette(n_colors=len(MODEL_ORDER))))
    g = sns.catplot(
        data=plot_data,
        x="scenario",
        y="value",
        hue="model",
        hue_order=MODEL_ORDER,
        col="metric",
        kind="bar",
        col_wrap=3,
        sharey=False,
        height=3.2,
        aspect=1.2,
        palette=palette,
    )
    for metric, axis in zip(KPI_METRICS, g.axes.flat):
        metric_data = plot_data.loc[plot_data["metric"] == metric].copy()
        axis.set_title(KPI_TITLES[metric])
        axis.tick_params(axis="x", rotation=20)
        axis.grid(alpha=0.2)

        # Bar plots disappear visually when every value is exactly zero. 
        # In that case we overlay zero-valued markers and an explicit note instead of drawing a misleading pseudo-bar.
        if float(metric_data["value"].abs().max()) <= 1e-9:
            sns.stripplot(
                data=metric_data,
                x="scenario",
                y="value",
                hue="model",
                hue_order=MODEL_ORDER,
                dodge=True,
                jitter=False,
                marker="o",
                size=6,
                palette=palette,
                ax=axis,
            )
            legend = axis.get_legend()
            if legend is not None:
                legend.remove()
            axis.axhline(0.0, color="0.35", linewidth=1.0)
            axis.set_ylim(-0.5, 0.5)
            axis.text(0.03, 0.92, "All scenarios = 0", transform=axis.transAxes, fontsize=9, color="dimgray")
    g.fig.tight_layout()
    g.fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    plt.close(g.fig)

def _build_comparison_table(summary: pd.DataFrame) -> pd.DataFrame:
    """Derive the integrated-versus-sequential comparison table."""
    integrated = summary[summary["model"] == "integrated_exact"].set_index("scenario")
    sequential = summary[summary["model"] == "sequential_benchmark"].set_index("scenario")
    comparison = pd.DataFrame(
        {
            "integrated_labour_cost": integrated["labour_cost"],
            "sequential_labour_cost": sequential["labour_cost"],
            "cost_saving": sequential["labour_cost"] - integrated["labour_cost"],
            "cost_saving_pct": 100.0 * (sequential["labour_cost"] - integrated["labour_cost"]) / sequential["labour_cost"],
            "integrated_weighted_flow_time": integrated["weighted_flow_time"],
            "sequential_weighted_flow_time": sequential["weighted_flow_time"],
            "weighted_flow_time_change_pct": 100.0
            * (integrated["weighted_flow_time"] - sequential["weighted_flow_time"])
            / sequential["weighted_flow_time"],
            "integrated_mean_flow_time_periods": integrated["mean_flow_time_periods"],
            "sequential_mean_flow_time_periods": sequential["mean_flow_time_periods"],
            "mean_flow_time_change_pct": 100.0
            * (integrated["mean_flow_time_periods"] - sequential["mean_flow_time_periods"])
            / sequential["mean_flow_time_periods"],
            "integrated_regular_hours": integrated["regular_worker_hours"],
            "sequential_regular_hours": sequential["regular_worker_hours"],
            "regular_hour_saving": sequential["regular_worker_hours"] - integrated["regular_worker_hours"],
            "integrated_temp_hours": integrated["temp_worker_hours"],
            "sequential_temp_hours": sequential["temp_worker_hours"],
            "temp_hour_change": sequential["temp_worker_hours"] - integrated["temp_worker_hours"],
            "integrated_balance": integrated["balance_deviation"],
            "sequential_balance": sequential["balance_deviation"],
            "balance_change_pct": 100.0
            * (integrated["balance_deviation"] - sequential["balance_deviation"])
            / sequential["balance_deviation"],
            "integrated_active_waves": integrated["active_waves"],
            "sequential_active_waves": sequential["active_waves"],
        }
    ).reset_index()
    return comparison

def run_experiment_suite(
    output_dir: str | Path,
    objective_weights: ObjectiveWeights | None = None,
) -> ExperimentSuiteResult:
    # Run the deterministic four-scenario experiment suite and export artefacts
    os.environ.setdefault("MPLCONFIGDIR", str(Path(output_dir) / ".mplconfig"))
    directories = _ensure_output_dirs(output_dir)
    results: list[ModelResult] = []
    validation_rows: list[dict[str, object]] = []
    profiles: list[dict[str, object]] = []
    for scenario_name, config in SCENARIOS.items():
        instance = generate_instance(config)
        export_instance(instance, directories["instances"])
        profiles.append(build_instance_profile(instance))
        sequential = solve_sequential_benchmark(instance, objective_weights=objective_weights)
        integrated = solve_integrated_model(instance, warm_start_result=sequential, objective_weights=objective_weights)
        scenario_results = [integrated, sequential]
        for result in scenario_results:
            results.append(result)
            validation_rows.extend(validate_result(instance, result))
            _save_result_tables(result, directories["tables"])
        _build_staffing_plot(
            scenario_name=scenario_name,
            results=scenario_results,
            figure_path=directories["figures"] / f"{scenario_name}_staffing_comparison.png",
        )
    summary = pd.DataFrame([result.summary_row() for result in results])
    profiles_frame = pd.DataFrame(profiles)
    validation = pd.DataFrame(validation_rows)
    comparison = _build_comparison_table(summary)
    summary.to_csv(directories["tables"] / "experiment_summary.csv", index=False)
    profiles_frame.to_csv(directories["tables"] / "instance_profiles.csv", index=False)
    validation.to_csv(directories["tables"] / "validation_summary.csv", index=False)
    comparison.to_csv(directories["tables"] / "model_comparison.csv", index=False)
    _build_kpi_plot(summary, directories["figures"] / "experiment_kpi_comparison.png")
    return ExperimentSuiteResult(
        summary=summary,
        comparison=comparison,
        profiles=profiles_frame,
        validation=validation,
        results=results,
    )
