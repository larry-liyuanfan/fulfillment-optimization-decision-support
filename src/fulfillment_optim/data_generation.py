# Deterministic instance generation for the fulfilment-planning study
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from .config import SCENARIOS, ScenarioConfig

SERVICE_CLASSES = ("economy", "standard", "priority")
PRIORITY_WEIGHTS = {"economy": 1.0, "standard": 3.0, "priority": 7.0}
FLOW_TIME_WEIGHTS = {"economy": 1.0, "standard": 1.6, "priority": 2.4}

# Li, Zhang, and Jiang (2022) cite an average of roughly two items per e-commerce order. The distribution below preserves that low-line-count shape while keeping enough variation to create batching decisions.
ITEM_COUNT_VALUES = np.array([1, 2, 3, 4, 5, 6])
ITEM_COUNT_PROBABILITIES = np.array([0.42, 0.30, 0.15, 0.08, 0.03, 0.02], dtype=float)

@dataclass
class FulfillmentInstance:
    # Container for one scenario instance and its derived tables
    scenario: ScenarioConfig
    orders: pd.DataFrame
    periods: pd.DataFrame
    shifts: pd.DataFrame
    metadata: dict[str, Any]
    @property
    def release_periods(self) -> list[int]:
        return self.periods.loc[self.periods["can_release"] == 1, "period"].tolist()
    @property
    def n_periods(self) -> int:
        return self.scenario.n_periods


def _sample_service_class(rng: np.random.Generator, config: ScenarioConfig) -> np.ndarray:
    # Sample service classes from the scenario-specific service mix
    shares = np.array(config.service_mix, dtype=float)
    shares = shares / shares.sum()
    return rng.choice(SERVICE_CLASSES, size=config.n_orders, p=shares)

def _sample_arrivals(rng: np.random.Generator, config: ScenarioConfig) -> np.ndarray:
    # Sample order arrivals over releasable periods
    release_periods = np.arange(config.n_periods - 1)
    weights = np.array(config.arrival_profile, dtype=float)
    weights = weights / weights.sum()
    return rng.choice(release_periods, size=config.n_orders, p=weights)

def _sample_due_periods(
    rng: np.random.Generator,
    config: ScenarioConfig,
    arrivals: np.ndarray,
    service_classes: np.ndarray,
) -> np.ndarray:
    # Sample due periods from scenario-specific service windows
    due_periods = np.zeros(config.n_orders, dtype=int)
    for idx, service_class in enumerate(service_classes):
        lower, upper = config.due_windows[service_class]
        # The due-period logic is scenario-specific: tighter scenarios narrow the sampling window rather than changing the rest of the warehouse physics.
        due_periods[idx] = min(arrivals[idx] + int(rng.integers(lower, upper + 1)), config.n_periods - 1)
    return due_periods


def _build_orders(config: ScenarioConfig, rng: np.random.Generator) -> pd.DataFrame:
    # Build the order table for one scenario instance
    # Order generation is deterministic conditional on the scenario seed, so the entire experiment suite remains fully reproducible across reruns.
    arrivals = _sample_arrivals(rng, config)
    service_classes = _sample_service_class(rng, config)
    due_periods = _sample_due_periods(rng, config, arrivals, service_classes)

    item_counts = rng.choice(
        ITEM_COUNT_VALUES,
        size=config.n_orders,
        replace=True,
        p=ITEM_COUNT_PROBABILITIES,
    )
    item_volume_lists: list[list[float]] = []
    order_volumes = np.zeros(config.n_orders)
    zones_touched = np.zeros(config.n_orders, dtype=int)
    pick_minutes = np.zeros(config.n_orders)
    pack_minutes = np.zeros(config.n_orders)
    for order_idx, item_count in enumerate(item_counts):
        item_volumes = rng.lognormal(mean=0.55, sigma=0.45, size=int(item_count))
        item_volumes = np.maximum(item_volumes, 0.25)
        total_volume = float(item_volumes.sum())
        zone_count = int(min(config.n_zones, 1 + rng.binomial(max(int(item_count) - 1, 0), 0.60)))

        # Picking time is driven by retrieval, travel across zones, and basic handling effort. Packing time is lower, but still depends on item count and carton size.
        pick_time = (
            2.0
            + 1.00 * float(item_count)
            + 1.20 * float(zone_count)
            + 0.12 * total_volume
            + rng.uniform(0.10, 0.50)
        )
        pack_time = (
            1.0
            + 0.55 * float(item_count)
            + 0.25 * float(zone_count)
            + 0.06 * total_volume
            + rng.uniform(0.05, 0.30)
        )
        item_volume_lists.append([round(value, 2) for value in item_volumes.tolist()])
        order_volumes[order_idx] = round(total_volume, 2)
        zones_touched[order_idx] = zone_count
        pick_minutes[order_idx] = round(pick_time, 2)
        pack_minutes[order_idx] = round(pack_time, 2)

    orders = pd.DataFrame(
        {
            "order_id": [f"O{idx + 1:03d}" for idx in range(config.n_orders)],
            "arrival_period": arrivals,
            "due_period": due_periods,
            "service_class": service_classes,
            "priority_weight": [PRIORITY_WEIGHTS[label] for label in service_classes],
            "flow_time_weight": [FLOW_TIME_WEIGHTS[label] for label in service_classes],
            "item_count": item_counts,
            "zones_touched": zones_touched,
            "total_volume": order_volumes,
            "pick_minutes": pick_minutes,
            "pack_minutes": pack_minutes,
            "item_volumes_dm3": item_volume_lists,
        }
    )
    orders["slack_periods"] = orders["due_period"] - orders["arrival_period"]
    orders["minimum_completion_period"] = orders["arrival_period"] + 1
    orders["service_window_width"] = orders["slack_periods"] - 1
    # The exact model allows at most two release periods of lateness. Given the
    # very large tardiness penalty, later releases are dominated in this project
    # and only slow the search without changing the practical policy insights.
    orders["latest_release_period"] = np.minimum(orders["due_period"] + 1, config.n_periods - 2).astype(int)
    orders["feasible_release_count"] = orders["latest_release_period"] - orders["arrival_period"] + 1
    return orders.sort_values(["arrival_period", "due_period", "priority_weight"], ascending=[True, True, False]).reset_index(drop=True)


def _build_periods(config: ScenarioConfig) -> pd.DataFrame:
    # Build the period-capacity table used by both models
    periods = []
    for period in range(config.n_periods):
        can_release = int(period < config.n_periods - 1)
        if can_release:
            # The last period cannot release a new wave because packing is
            # modelled to happen one period after picking.
            wave_capacity = round(config.base_wave_capacity_volume * config.wave_capacity_profile[period], 2)
            wave_order_limit = config.wave_order_limit
        else:
            wave_capacity = 0.0
            wave_order_limit = 0
        periods.append(
            {
                "period": period,
                "label": f"P{period + 1}",
                "can_release": can_release,
                "wave_capacity_volume": wave_capacity,
                "wave_order_limit": wave_order_limit,
                "max_temp_workers": config.max_temp_workers_per_period,
                "max_overtime_workers": config.max_overtime_workers_per_period,
            }
        )
    return pd.DataFrame(periods)

def _build_shifts(config: ScenarioConfig) -> pd.DataFrame:
    # Build the regular-shift template table for one scenario
    rows = []
    for template in config.shift_templates:
        rows.append(
            {
                "shift_name": template.name,
                "start_period": template.start_period,
                "end_period": template.start_period + template.length - 1,
                "length_hours": template.length,
                "max_workers": template.max_workers,
                "cost_per_worker": round(template.length * config.regular_hourly_cost, 2),
                "coverage": list(template.coverage(config.n_periods)),
            }
        )
    return pd.DataFrame(rows)

def generate_instance(config: ScenarioConfig | str, seed: int | None = None) -> FulfillmentInstance:
    """Generate one deterministic department-level fulfilment instance.
    Passing an explicit seed keeps the scenario structure fixed while creating a different order-level realisation for robustness experiments.
    """
    if isinstance(config, str):
        config = SCENARIOS[config]
    active_seed = int(config.seed if seed is None else seed)
    rng = np.random.default_rng(active_seed)
    orders = _build_orders(config, rng)
    periods = _build_periods(config)
    shifts = _build_shifts(config)
    metadata = {
        "scenario_name": config.name,
        "scenario_description": config.description,
        "seed": active_seed,
        "public_sources": [
            "https://www.aboutamazon.com/workplace/facilities",
            "https://www.aboutamazon.com/news/operations/how-do-amazon-packages-get-delivered",
            "https://github.com/zalandoresearch/batching-benchmarks",
            "https://www.mdpi.com/0718-1876/17/4/91",
            "https://www.bls.gov/oes/2023/May/oes537065.htm",
        ],
        "order_count": int(len(orders)),
        "avg_items_per_order": round(float(orders["item_count"].mean()), 3),
        "avg_pick_minutes": round(float(orders["pick_minutes"].mean()), 3),
        "avg_pack_minutes": round(float(orders["pack_minutes"].mean()), 3),
        "avg_total_volume_dm3": round(float(orders["total_volume"].mean()), 3),
        "avg_slack_periods": round(float(orders["slack_periods"].mean()), 3),
        "total_pick_minutes": round(float(orders["pick_minutes"].sum()), 2),
        "total_pack_minutes": round(float(orders["pack_minutes"].sum()), 2),
        "total_volume_dm3": round(float(orders["total_volume"].sum()), 2),
    }
    return FulfillmentInstance(
        scenario=config,
        orders=orders,
        periods=periods,
        shifts=shifts,
        metadata=metadata,
    )


def export_instance(instance: FulfillmentInstance, output_dir: str | Path) -> None:
    # Write the scenario tables to disk for inspection and reuse
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    orders_to_save = instance.orders.copy()
    orders_to_save["item_volumes_dm3"] = orders_to_save["item_volumes_dm3"].apply(
        lambda values: ",".join(f"{value:.2f}" for value in values)
    )

    orders_to_save.to_csv(output_path / f"{instance.scenario.name}_orders.csv", index=False)
    instance.periods.to_csv(output_path / f"{instance.scenario.name}_periods.csv", index=False)
    instance.shifts.to_csv(output_path / f"{instance.scenario.name}_shifts.csv", index=False)
    pd.Series(instance.metadata).to_json(output_path / f"{instance.scenario.name}_metadata.json", indent=2)
