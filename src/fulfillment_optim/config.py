# Static scenario and cost parameters for the fulfilment study
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ShiftTemplate:
    # Regular-shift template used by the staffing models
    name: str
    start_period: int
    length: int
    max_workers: int
    def coverage(self, n_periods: int) -> tuple[int, ...]:
        # Return the binary period-coverage vector for this shift
        return tuple(
            1 if self.start_period <= period < self.start_period + self.length else 0
            for period in range(n_periods)
        )

@dataclass(frozen=True)
class ScenarioConfig:
    # Scenario-level inputs shared by data generation and optimisation
    name: str
    description: str
    seed: int
    n_periods: int
    n_orders: int
    n_zones: int
    period_minutes: int
    arrival_profile: tuple[float, ...]
    wave_capacity_profile: tuple[float, ...]
    service_mix: tuple[float, float, float]
    due_windows: dict[str, tuple[int, int]]
    pick_minutes_capacity_per_worker: float
    pack_minutes_capacity_per_worker: float
    base_wave_capacity_volume: float
    wave_order_limit: int
    regular_hourly_cost: float
    temp_hourly_cost: float
    overtime_hourly_cost: float
    max_temp_workers_per_period: int
    max_overtime_workers_per_period: int
    wave_opening_cost: float
    shift_templates: tuple[ShiftTemplate, ...]


# A six-hour shift design is a good fit for a one-day tactical planning horizon:
# it creates realistic overlap while still leaving visible consequences for poor release decisions.
BASE_SHIFT_TEMPLATES = (
    ShiftTemplate("Dawn", start_period=0, length=6, max_workers=5),
    ShiftTemplate("Morning", start_period=2, length=6, max_workers=7),
    ShiftTemplate("Midday", start_period=4, length=6, max_workers=7),
    ShiftTemplate("Late", start_period=6, length=6, max_workers=5),
)
SHORTAGE_SHIFT_TEMPLATES = (
    ShiftTemplate("Dawn", start_period=0, length=6, max_workers=4),
    ShiftTemplate("Morning", start_period=2, length=6, max_workers=6),
    ShiftTemplate("Midday", start_period=4, length=6, max_workers=6),
    ShiftTemplate("Late", start_period=6, length=6, max_workers=4),
)

# Wage calibration:
# - regular labour uses the May 2023 BLS median hourly wage for stockers/order fillers
# - temporary labour adds a 25% premium
# - overtime adds a 50% premium
REGULAR_HOURLY_COST = 17.50
TEMP_HOURLY_COST = 21.88
OVERTIME_HOURLY_COST = 26.25

SCENARIOS: dict[str, ScenarioConfig] = {
    # Each scenario changes one operational stressor while preserving the same
    # department structure, which keeps cross-scenario comparisons interpretable.
    "base": ScenarioConfig(
        name="base",
        description="Nominal same-day fulfilment day for one picking-and-packing department.",
        seed=42,
        n_periods=12,
        n_orders=120,
        n_zones=12,
        period_minutes=60,
        arrival_profile=(0.08, 0.09, 0.10, 0.11, 0.11, 0.10, 0.10, 0.11, 0.09, 0.07, 0.04),
        wave_capacity_profile=(0.96, 1.00, 1.02, 1.05, 1.06, 1.02, 1.00, 1.00, 0.98, 0.94, 0.90),
        service_mix=(0.20, 0.58, 0.22),
        due_windows={"economy": (4, 6), "standard": (3, 5), "priority": (2, 4)},
        pick_minutes_capacity_per_worker=50.0,
        pack_minutes_capacity_per_worker=55.0,
        base_wave_capacity_volume=70.0,
        wave_order_limit=14,
        regular_hourly_cost=REGULAR_HOURLY_COST,
        temp_hourly_cost=TEMP_HOURLY_COST,
        overtime_hourly_cost=OVERTIME_HOURLY_COST,
        max_temp_workers_per_period=3,
        max_overtime_workers_per_period=2,
        wave_opening_cost=8.0,
        shift_templates=BASE_SHIFT_TEMPLATES,
    ),
    "promotion": ScenarioConfig(
        name="promotion",
        description="Promotion day with denser arrivals, more urgent orders, and heavier late-day pressure.",
        seed=142,
        n_periods=12,
        n_orders=145,
        n_zones=12,
        period_minutes=60,
        arrival_profile=(0.05, 0.06, 0.08, 0.10, 0.11, 0.11, 0.12, 0.13, 0.12, 0.08, 0.04),
        wave_capacity_profile=(0.95, 0.98, 1.00, 1.04, 1.07, 1.08, 1.08, 1.06, 1.02, 0.96, 0.92),
        service_mix=(0.12, 0.50, 0.38),
        due_windows={"economy": (4, 5), "standard": (3, 4), "priority": (2, 3)},
        pick_minutes_capacity_per_worker=50.0,
        pack_minutes_capacity_per_worker=55.0,
        base_wave_capacity_volume=74.0,
        wave_order_limit=16,
        regular_hourly_cost=REGULAR_HOURLY_COST,
        temp_hourly_cost=TEMP_HOURLY_COST,
        overtime_hourly_cost=OVERTIME_HOURLY_COST,
        max_temp_workers_per_period=4,
        max_overtime_workers_per_period=3,
        wave_opening_cost=8.0,
        shift_templates=BASE_SHIFT_TEMPLATES,
    ),
    "tight_due_dates": ScenarioConfig(
        name="tight_due_dates",
        description="Nominal demand but tighter customer promises, so cycle time matters much more.",
        seed=314,
        n_periods=12,
        n_orders=125,
        n_zones=12,
        period_minutes=60,
        arrival_profile=(0.08, 0.09, 0.10, 0.10, 0.10, 0.10, 0.10, 0.11, 0.10, 0.07, 0.05),
        wave_capacity_profile=(0.96, 1.00, 1.02, 1.04, 1.05, 1.02, 1.00, 0.99, 0.97, 0.94, 0.90),
        service_mix=(0.10, 0.52, 0.38),
        due_windows={"economy": (3, 4), "standard": (2, 3), "priority": (1, 2)},
        pick_minutes_capacity_per_worker=49.0,
        pack_minutes_capacity_per_worker=54.0,
        base_wave_capacity_volume=68.0,
        wave_order_limit=13,
        regular_hourly_cost=REGULAR_HOURLY_COST,
        temp_hourly_cost=TEMP_HOURLY_COST,
        overtime_hourly_cost=OVERTIME_HOURLY_COST,
        max_temp_workers_per_period=2,
        max_overtime_workers_per_period=2,
        wave_opening_cost=8.0,
        shift_templates=BASE_SHIFT_TEMPLATES,
    ),
    "labour_shortage": ScenarioConfig(
        name="labour_shortage",
        description="Same-day demand with reduced regular staffing and very limited recourse labour.",
        seed=2718,
        n_periods=12,
        n_orders=120,
        n_zones=12,
        period_minutes=60,
        arrival_profile=(0.08, 0.09, 0.10, 0.11, 0.11, 0.10, 0.10, 0.11, 0.09, 0.07, 0.04),
        wave_capacity_profile=(0.96, 1.00, 1.02, 1.05, 1.06, 1.02, 1.00, 1.00, 0.98, 0.94, 0.90),
        service_mix=(0.20, 0.58, 0.22),
        due_windows={"economy": (4, 6), "standard": (3, 5), "priority": (2, 4)},
        pick_minutes_capacity_per_worker=49.0,
        pack_minutes_capacity_per_worker=54.0,
        base_wave_capacity_volume=70.0,
        wave_order_limit=14,
        regular_hourly_cost=REGULAR_HOURLY_COST,
        temp_hourly_cost=TEMP_HOURLY_COST,
        overtime_hourly_cost=OVERTIME_HOURLY_COST,
        max_temp_workers_per_period=1,
        max_overtime_workers_per_period=1,
        wave_opening_cost=8.0,
        shift_templates=SHORTAGE_SHIFT_TEMPLATES,
    ),
}
