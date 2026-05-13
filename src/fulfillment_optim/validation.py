# Validation checks for generated instances and optimisation outputs
from __future__ import annotations
from typing import Any
import pandas as pd
from .data_generation import FulfillmentInstance
from .models import ModelResult

def build_instance_profile(instance: FulfillmentInstance) -> dict[str, Any]:
    # Summarise the scale and load characteristics of one instance
    orders = instance.orders
    periods = instance.periods
    return {
        "scenario": instance.scenario.name,
        "orders": int(len(orders)),
        "avg_items_per_order": round(float(orders["item_count"].mean()), 3),
        "avg_pick_minutes": round(float(orders["pick_minutes"].mean()), 3),
        "avg_pack_minutes": round(float(orders["pack_minutes"].mean()), 3),
        "avg_flow_sla_width": round(float(orders["slack_periods"].mean()), 3),
        "avg_volume_dm3": round(float(orders["total_volume"].mean()), 3),
        "total_workload_minutes": round(float(orders["pick_minutes"].sum() + orders["pack_minutes"].sum()), 3),
        "peak_arrivals_in_period": int(orders["arrival_period"].value_counts().max()),
        "total_wave_volume_capacity": round(float(periods["wave_capacity_volume"].sum()), 3),
        "total_wave_order_capacity": int(periods["wave_order_limit"].sum()),
    }


def validate_result(instance: FulfillmentInstance, result: ModelResult) -> list[dict[str, Any]]:
    # Check assignment, capacity, and tardiness consistency for one result
    rows: list[dict[str, Any]] = []
    if result.assignment.empty:
        rows.append(
            {
                "scenario": instance.scenario.name,
                "model": result.model_name,
                "check": "solution_exists",
                "passed": False,
                "value": None,
            }
        )
        return rows

    assignment = result.assignment.copy()
    staffing = result.staffing.copy().set_index("period")
    periods = instance.periods.set_index("period")
    orders = instance.orders.set_index("order_id")
    assignment_count_gap = abs(len(assignment) - len(orders))
    release_feasibility_gap = float(
        max(
            0.0,
            (
                (assignment["arrival_period"] > assignment["release_period"])
                | (assignment["release_period"] > assignment["order_id"].map(orders["latest_release_period"]))
            ).astype(int).sum(),
        )
    )
    order_uniqueness_gap = float(assignment["order_id"].duplicated().sum())
    wave_volume = assignment.groupby("release_period")["total_volume"].sum()
    wave_count = assignment.groupby("release_period")["order_id"].count()
    max_wave_volume_violation = 0.0
    max_wave_count_violation = 0.0
    for period, total_volume in wave_volume.items():
        max_wave_volume_violation = max(
            max_wave_volume_violation,
            float(total_volume - periods.loc[period, "wave_capacity_volume"]),
        )
    for period, total_count in wave_count.items():
        max_wave_count_violation = max(
            max_wave_count_violation,
            float(total_count - periods.loc[period, "wave_order_limit"]),
        )

    max_pick_capacity_violation = 0.0
    max_pack_capacity_violation = 0.0
    max_worker_balance_violation = 0.0
    for period in staffing.index:
        row = staffing.loc[period]
        max_pick_capacity_violation = max(
            max_pick_capacity_violation,
            float(row["pick_load_minutes"] - instance.scenario.pick_minutes_capacity_per_worker * row["pick_workers"]),
        )
        max_pack_capacity_violation = max(
            max_pack_capacity_violation,
            float(row["pack_load_minutes"] - instance.scenario.pack_minutes_capacity_per_worker * row["pack_workers"]),
        )
        max_worker_balance_violation = max(
            max_worker_balance_violation,
            float(row["direct_workers"] - row["total_available_workers"]),
        )
    tardiness_gap = float(
        (
            (
                assignment["tardiness_periods"]
                - (assignment["completion_period"] - assignment["due_period"]).clip(lower=0)
            ).abs().max()
        )
    )

    checks = {
        "assignment_count_gap": assignment_count_gap,
        "release_feasibility_gap": release_feasibility_gap,
        "order_uniqueness_gap": order_uniqueness_gap,
        "max_wave_volume_violation": max_wave_volume_violation,
        "max_wave_count_violation": max_wave_count_violation,
        "max_pick_capacity_violation": max_pick_capacity_violation,
        "max_pack_capacity_violation": max_pack_capacity_violation,
        "max_worker_balance_violation": max_worker_balance_violation,
        "tardiness_definition_gap": tardiness_gap,
    }
    for check_name, value in checks.items():
        rows.append(
            {
                "scenario": instance.scenario.name,
                "model": result.model_name,
                "check": check_name,
                "passed": bool(abs(value) <= 1e-6),
                "value": round(float(value), 8),
            }
        )
    return rows
