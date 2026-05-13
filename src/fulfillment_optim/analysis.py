"""Post-solve analysis, sensitivity, and replication-study utilities."""
from __future__ import annotations
from math import comb
from pathlib import Path
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .config import SCENARIOS, ScenarioConfig
from .data_generation import generate_instance
from .experiments import ExperimentSuiteResult
from .models import ObjectiveWeights, solve_integrated_model, solve_sequential_benchmark

def _pct_change(new_value: float, base_value: float) -> float:
    # Compute percentage change while guarding against zero denominators
    if abs(base_value) <= 1e-9:
        return 0.0
    return 100.0 * (new_value - base_value) / base_value

def _bootstrap_mean_ci(values: np.ndarray, seed: int = 20260424, n_resamples: int = 5000) -> tuple[float, float]:
    # Estimate a bootstrap confidence interval for the sample mean
    if len(values) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(n_resamples, len(values)), replace=True).mean(axis=1)
    lower, upper = np.quantile(draws, [0.025, 0.975])
    return float(lower), float(upper)

def _sign_test_pvalue(successes: int, trials: int) -> float:
    # Return the one-sided sign-test p-value for positive improvements."""
    if trials <= 0:
        return float("nan")
    return sum(comb(trials, value) for value in range(successes, trials + 1)) / (2**trials)

def _build_service_robustness_frame(results: list) -> pd.DataFrame:
    # Summarise delivery-buffer behaviour beyond the late-order count
    rows: list[dict[str, object]] = []
    for result in results:
        assignment = result.assignment.copy()
        assignment["residual_slack_periods"] = assignment["due_period"] - assignment["completion_period"]
        rows.append(
            {"scenario": result.scenario_name, "model": result.model_name,
             "mean_residual_slack_periods": round(float(assignment["residual_slack_periods"].mean()), 6),
             "min_residual_slack_periods": round(float(assignment["residual_slack_periods"].min()), 6),
             "share_orders_with_slack_le_1": round(float((assignment["residual_slack_periods"] <= 1).mean()), 6),
             "share_orders_exactly_on_due_date": round(float((assignment["residual_slack_periods"] == 0).mean()), 6),
             "share_orders_with_slack_ge_2": round(float((assignment["residual_slack_periods"] >= 2).mean()), 6),
            })
    return pd.DataFrame(rows)

def _build_operational_diagnostics_frame(results: list[object]) -> pd.DataFrame:
    # Summarise wave utilisation and staffing-shape diagnostics
    rows: list[dict[str, object]] = []
    for result in results:
        instance = generate_instance(result.scenario_name)
        periods = instance.periods.set_index("period")
        wave_orders = result.assignment.groupby("release_period")["order_id"].count()
        wave_volume = result.assignment.groupby("release_period")["total_volume"].sum()
        order_utilisation = []
        volume_utilisation = []
        for period in wave_orders.index:
            order_utilisation.append(float(wave_orders.loc[period]) / float(periods.loc[period, "wave_order_limit"]))
            volume_utilisation.append(float(wave_volume.loc[period]) / float(periods.loc[period, "wave_capacity_volume"]))
        staffing = result.staffing.copy()
        rows.append(
            {"scenario": result.scenario_name,
             "model": result.model_name,
             "active_waves": result.active_waves,
             "regular_worker_hours": result.regular_worker_hours,
             "temp_worker_hours": result.temp_worker_hours,
             "overtime_worker_hours": result.overtime_worker_hours,
             "total_direct_worker_hours": round(float(staffing["direct_workers"].sum()), 6),
             "peak_total_load_minutes": round(float(staffing["total_load_minutes"].max()), 6),
             "mean_total_load_minutes": round(float(staffing["total_load_minutes"].mean()), 6),
             "mean_wave_order_util": round(float(np.mean(order_utilisation)), 6),
             "mean_wave_volume_util": round(float(np.mean(volume_utilisation)), 6),
             "peak_wave_order_util": round(float(np.max(order_utilisation)), 6),
             "peak_wave_volume_util": round(float(np.max(volume_utilisation)), 6),
            })
    return pd.DataFrame(rows)

def _build_balance_weight_sensitivity(
    tables_dir: Path, figures_dir: Path, balance_weights: tuple[float, ...], objective_weights: ObjectiveWeights,
) -> pd.DataFrame:
    # Evaluate how the balance weight changes the integrated solution

    rows: list[dict[str, object]] = []
    for balance_weight in balance_weights:
        weights = ObjectiveWeights(
            tardiness=objective_weights.tardiness, flow_time=objective_weights.flow_time, balance=balance_weight,
        )
        for config in SCENARIOS.values():
            instance = generate_instance(config)
            sequential = solve_sequential_benchmark(instance, objective_weights=weights)
            integrated = solve_integrated_model(instance, warm_start_result=sequential, objective_weights=weights)
            rows.append(
                {"balance_weight": balance_weight,
                 "scenario": config.name,
                 "integrated_status": integrated.status,
                 "sequential_status": sequential.status,
                 "integrated_labour_cost": integrated.labour_cost,
                 "sequential_labour_cost": sequential.labour_cost,
                 "cost_saving_pct": round(
                     100.0 * (sequential.labour_cost - integrated.labour_cost) / sequential.labour_cost, 6,
                    ),
                    "weighted_flow_time_change_pct": round(
                        _pct_change(integrated.weighted_flow_time, sequential.weighted_flow_time), 6,
                    ),
                    "balance_change_pct": round(
                        _pct_change(integrated.balance_deviation, sequential.balance_deviation), 6,
                    ),
                }
            )

    frame = pd.DataFrame(rows)
    frame.to_csv(tables_dir / "balance_weight_sensitivity.csv", index=False)
    plot_frame = frame.melt(
        id_vars=["balance_weight", "scenario"],
        value_vars=["cost_saving_pct", "weighted_flow_time_change_pct", "balance_change_pct"],
        var_name="metric",
        value_name="value",
    )
    g = sns.relplot(
        data=plot_frame,
        x="balance_weight",
        y="value",
        hue="scenario",
        col="metric",
        kind="line",
        marker="o",
        facet_kws={"sharey": False},
        height=3.5,
        aspect=1.1,
    )
    for axis in g.axes.flat:
        axis.grid(alpha=0.2)
    g.fig.tight_layout()
    g.fig.savefig(figures_dir / "balance_weight_sensitivity.png", dpi=200, bbox_inches="tight")
    plt.close(g.fig)
    return frame


def _replication_seed(config: ScenarioConfig, replication_id: int) -> int:
    # Map each replication id to a deterministic scenario seed
    return int(config.seed + 1000 * replication_id + 37 * replication_id)

def _solve_feasibility_screened_replication(
    config: ScenarioConfig,
    replication_id: int,
    objective_weights: ObjectiveWeights,
    max_attempts: int = 25,
):
    """Generate a deterministic but feasibility-screened replication.
    Some random draws in the tight-due-date family can create instances that are structurally infeasible under the fixed department capacities. For the replication study we therefore retain the first seed in a deterministic seed sequence that yields a feasible exact benchmark.
    """
    base_seed = _replication_seed(config, replication_id)
    last_error: ValueError | None = None
    for attempt in range(max_attempts):
        seed = base_seed + attempt
        instance = generate_instance(config, seed=seed)
        try:
            sequential = solve_sequential_benchmark(instance, objective_weights=objective_weights)
            integrated = solve_integrated_model(instance, warm_start_result=sequential, objective_weights=objective_weights)
            return instance, sequential, integrated, seed, attempt
        except ValueError as error:
            last_error = error
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Replication generation failed unexpectedly for scenario {config.name}.")

def _build_replication_study(
    tables_dir: Path,
    figures_dir: Path,
    objective_weights: ObjectiveWeights,
    replications_per_scenario: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Run the multi-instance replication study and export summary tables
    raw_rows: list[dict[str, object]] = []
    for config in SCENARIOS.values():
        for replication_id in range(1, replications_per_scenario + 1):
            instance, sequential, integrated, seed, resample_attempts = _solve_feasibility_screened_replication(
                config=config,
                replication_id=replication_id,
                objective_weights=objective_weights,
            )
            raw_rows.append(
                {
                    "scenario": config.name,
                    "replication_id": replication_id,
                    "seed": seed,
                    "feasibility_resamples": resample_attempts,
                    "orders": len(instance.orders),
                    "avg_items_per_order": round(float(instance.orders["item_count"].mean()), 6),
                    "avg_slack_periods": round(float(instance.orders["slack_periods"].mean()), 6),
                    "total_workload_minutes": round(float(instance.orders["pick_minutes"].sum() + instance.orders["pack_minutes"].sum()), 6),
                    "integrated_status": integrated.status,
                    "sequential_status": sequential.status,
                    "integrated_labour_cost": integrated.labour_cost,
                    "sequential_labour_cost": sequential.labour_cost,
                    "cost_saving_pct": round(
                        100.0 * (sequential.labour_cost - integrated.labour_cost) / sequential.labour_cost, 6,
                    ),
                    "weighted_flow_time_change_pct": round(
                        _pct_change(integrated.weighted_flow_time, sequential.weighted_flow_time), 6,
                    ),
                    "balance_change_pct": round(
                        _pct_change(integrated.balance_deviation, sequential.balance_deviation), 6,
                    ),
                    "integrated_late_orders": integrated.late_orders,
                    "sequential_late_orders": sequential.late_orders,
                    "integrated_solve_time_seconds": integrated.solve_time_seconds,
                    "sequential_solve_time_seconds": sequential.solve_time_seconds,
                }
            )

    raw_frame = pd.DataFrame(raw_rows)
    raw_frame.to_csv(tables_dir / "replication_raw.csv", index=False)
    summary_rows: list[dict[str, object]] = []
    for scenario, scenario_frame in raw_frame.groupby("scenario", sort=False):
        cost_values = scenario_frame["cost_saving_pct"].to_numpy(dtype=float)
        flow_values = scenario_frame["weighted_flow_time_change_pct"].to_numpy(dtype=float)
        balance_values = scenario_frame["balance_change_pct"].to_numpy(dtype=float)
        cost_lower, cost_upper = _bootstrap_mean_ci(cost_values, seed=20260424 + len(summary_rows))
        flow_lower, flow_upper = _bootstrap_mean_ci(flow_values, seed=20260524 + len(summary_rows))
        balance_lower, balance_upper = _bootstrap_mean_ci(balance_values, seed=20260624 + len(summary_rows))
        cheaper_count = int((cost_values > 0).sum())
        summary_rows.append(
            {
                "scenario": scenario,
                "replications": int(len(scenario_frame)),
                "mean_cost_saving_pct": round(float(cost_values.mean()), 6),
                "std_cost_saving_pct": round(float(cost_values.std(ddof=1)), 6),
                "min_cost_saving_pct": round(float(cost_values.min()), 6),
                "max_cost_saving_pct": round(float(cost_values.max()), 6),
                "cost_saving_ci_low": round(cost_lower, 6),
                "cost_saving_ci_high": round(cost_upper, 6),
                "share_integrated_cheaper": round(float((cost_values > 0).mean()), 6),
                "sign_test_pvalue_cost_saving": round(_sign_test_pvalue(cheaper_count, len(scenario_frame)), 6),
                "mean_weighted_flow_time_change_pct": round(float(flow_values.mean()), 6),
                "flow_time_ci_low": round(flow_lower, 6),
                "flow_time_ci_high": round(flow_upper, 6),
                "mean_balance_change_pct": round(float(balance_values.mean()), 6),
                "balance_ci_low": round(balance_lower, 6),
                "balance_ci_high": round(balance_upper, 6),
                "share_balance_improved": round(float((balance_values < 0).mean()), 6),
                "share_zero_late_integrated": round(float((scenario_frame["integrated_late_orders"] == 0).mean()), 6),
                "mean_feasibility_resamples": round(float(scenario_frame["feasibility_resamples"].mean()), 6),
                "mean_integrated_solve_time_seconds": round(float(scenario_frame["integrated_solve_time_seconds"].mean()), 6),
            }
        )

    summary_frame = pd.DataFrame(summary_rows)
    summary_frame.to_csv(tables_dir / "replication_summary.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    sns.boxplot(data=raw_frame, x="scenario", y="cost_saving_pct", ax=axes[0], color="#9ecae1")
    sns.stripplot(data=raw_frame, x="scenario", y="cost_saving_pct", ax=axes[0], color="#08519c", alpha=0.7)
    axes[0].axhline(0.0, color="0.35", linewidth=1.0)
    axes[0].set_title("Replication cost-saving distribution")
    axes[0].tick_params(axis="x", rotation=20)
    axes[0].grid(alpha=0.2)
    sns.boxplot(data=raw_frame, x="scenario", y="weighted_flow_time_change_pct", ax=axes[1], color="#fdd0a2")
    sns.stripplot(data=raw_frame, x="scenario", y="weighted_flow_time_change_pct", ax=axes[1], color="#a63603", alpha=0.7)
    axes[1].axhline(0.0, color="0.35", linewidth=1.0)
    axes[1].set_title("Replication flow-time trade-off")
    axes[1].tick_params(axis="x", rotation=20)
    axes[1].grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(figures_dir / "replication_study.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return raw_frame, summary_frame


def export_advanced_analysis(
    output_dir: str | Path,
    suite_result: ExperimentSuiteResult,
    objective_weights: ObjectiveWeights | None = None,
    balance_weights: tuple[float, ...] = (0.1, 0.3, 0.5, 1.0),
    replications_per_scenario: int = 10,
) -> dict[str, Path]:
    # Export reproducible post-solve analysis tables and robustness studies
    objective_weights = objective_weights or ObjectiveWeights()
    output_dir = Path(output_dir)
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    service_robustness = _build_service_robustness_frame(suite_result.results)
    service_robustness.to_csv(tables_dir / "service_robustness_summary.csv", index=False)
    operational_diagnostics = _build_operational_diagnostics_frame(suite_result.results)
    operational_diagnostics.to_csv(tables_dir / "operational_diagnostics.csv", index=False)
    _build_balance_weight_sensitivity(
        tables_dir=tables_dir,
        figures_dir=figures_dir,
        balance_weights=balance_weights,
        objective_weights=objective_weights,
    )
    _build_replication_study(
        tables_dir=tables_dir,
        figures_dir=figures_dir,
        objective_weights=objective_weights,
        replications_per_scenario=replications_per_scenario,
    )
    return {
        "service_robustness": tables_dir / "service_robustness_summary.csv",
        "operational_diagnostics": tables_dir / "operational_diagnostics.csv",
        "balance_weight_sensitivity": tables_dir / "balance_weight_sensitivity.csv",
        "replication_raw": tables_dir / "replication_raw.csv",
        "replication_summary": tables_dir / "replication_summary.csv",
        "balance_weight_figure": figures_dir / "balance_weight_sensitivity.png",
        "replication_figure": figures_dir / "replication_study.png",
    }
