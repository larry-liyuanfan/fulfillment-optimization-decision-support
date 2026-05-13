# Exact optimisation models for integrated and sequential planning
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from .data_generation import FulfillmentInstance

@dataclass(frozen=True)
class ObjectiveWeights:
    """Scalarisation weights used by the exact models.
    The project keeps a very large tardiness weight so that service failures are dominated whenever a zero-tardiness solution exists. 
    Flow-time and balance weights are then used to shape the on-time feasible region.
    """
    tardiness: float = 10000.0
    flow_time: float = 2.0
    balance: float = 0.30

DEFAULT_OBJECTIVE_WEIGHTS = ObjectiveWeights()

@dataclass
class ModelResult:
    # Structured solve output for one model and one scenario
    scenario_name: str
    model_name: str
    status: str
    objective_value: float | None
    weighted_tardiness: float
    weighted_flow_time: float
    labour_cost: float
    balance_deviation: float
    active_waves: int
    late_orders: int
    total_tardiness_periods: float
    mean_flow_time_periods: float
    regular_worker_hours: float
    temp_worker_hours: float
    overtime_worker_hours: float
    solve_time_seconds: float
    mip_gap: float | None
    assignment: pd.DataFrame
    staffing: pd.DataFrame
    period_summary: pd.DataFrame
    order_summary: pd.DataFrame
    extra_metrics: dict[str, Any]
    def summary_row(self) -> dict[str, Any]:
        # Return the scalar KPIs used by the experiment summary table
        return {
            "scenario": self.scenario_name,
            "model": self.model_name,
            "status": self.status,
            "objective_value": self.objective_value,
            "weighted_tardiness": self.weighted_tardiness,
            "weighted_flow_time": self.weighted_flow_time,
            "labour_cost": self.labour_cost,
            "balance_deviation": self.balance_deviation,
            "active_waves": self.active_waves,
            "late_orders": self.late_orders,
            "total_tardiness_periods": self.total_tardiness_periods,
            "mean_flow_time_periods": self.mean_flow_time_periods,
            "regular_worker_hours": self.regular_worker_hours,
            "temp_worker_hours": self.temp_worker_hours,
            "overtime_worker_hours": self.overtime_worker_hours,
            "solve_time_seconds": self.solve_time_seconds,
            "mip_gap": self.mip_gap,
        }

def _resolve_objective_weights(weights: ObjectiveWeights | None) -> ObjectiveWeights:
    # Fall back to the default scalarisation weights when needed
    return weights if weights is not None else DEFAULT_OBJECTIVE_WEIGHTS

def _extract_shift_coverage(instance: FulfillmentInstance) -> dict[str, list[int]]:
    # Convert shift coverage vectors into a dictionary keyed by shift name
    return {row.shift_name: list(row.coverage) for row in instance.shifts.itertuples(index=False)}

def _make_model_name(status_code: int) -> str:
    # Map a Gurobi status code to a readable label
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
    }.get(status_code, f"STATUS_{status_code}")

def _safe_float_attribute(model: gp.Model, attribute_name: str) -> float | None:
    # Read an optional Gurobi float attribute without raising
    try:
        return float(model.getAttr(attribute_name))
    except AttributeError:
        return None

def _clean_value(value: float, digits: int = 6) -> float:
    # Round numeric output and squash negative-zero artefacts
    rounded = round(float(value), digits)
    return 0.0 if abs(rounded) < 10 ** (-digits) else rounded

def _empty_assignment_frame() -> pd.DataFrame:
    # Create the empty assignment schema used by failed solves
    return pd.DataFrame(
        columns=[
            "order_id",
            "release_period",
            "completion_period",
            "arrival_period",
            "due_period",
            "service_class",
            "priority_weight",
            "flow_time_weight",
            "item_count",
            "pick_minutes",
            "pack_minutes",
            "total_volume",
            "flow_time_periods",
            "tardiness_periods",
        ]
    )

def _empty_staffing_frame() -> pd.DataFrame:
    # Create the empty staffing schema used by failed solves
    return pd.DataFrame(
        columns=[
            "period",
            "label",
            "regular_available",
            "temp_workers",
            "overtime_workers",
            "total_available_workers",
            "pick_workers",
            "pack_workers",
            "direct_workers",
            "unused_capacity_workers",
            "pick_load_minutes",
            "pack_load_minutes",
            "total_load_minutes",
            "pick_utilisation",
            "pack_utilisation",
        ]
    )

def _build_staffing_output(
    instance: FulfillmentInstance,
    regular_available: dict[int, gp.LinExpr],
    pick_workers: dict[int, gp.Var],
    pack_workers: dict[int, gp.Var],
    temp_workers: dict[int, gp.Var],
    overtime_workers: dict[int, gp.Var],
    pick_load: dict[int, float | gp.LinExpr],
    pack_load: dict[int, float | gp.LinExpr],
) -> pd.DataFrame:
    # Convert the raw Gurobi decision variables into a tidy period-by-period operational table that can be inspected in the report and notebook.
    rows = []
    for period in range(instance.n_periods):
        regular_workers = _clean_value(regular_available[period].getValue())
        temp = _clean_value(temp_workers[period].X)
        overtime = _clean_value(overtime_workers[period].X)
        pick = _clean_value(pick_workers[period].X)
        pack = _clean_value(pack_workers[period].X)
        total_available = _clean_value(regular_workers + temp + overtime)
        direct_workers = _clean_value(pick + pack)
        unused_capacity = _clean_value(max(total_available - direct_workers, 0.0))
        pick_load_value = _clean_value(
            pick_load[period].getValue() if hasattr(pick_load[period], "getValue") else float(pick_load[period])
        )
        pack_load_value = _clean_value(
            pack_load[period].getValue() if hasattr(pack_load[period], "getValue") else float(pack_load[period])
        )
        if pick > 0:
            pick_utilisation = _clean_value(pick_load_value / (instance.scenario.pick_minutes_capacity_per_worker * pick))
        else:
            pick_utilisation = 0.0
        if pack > 0:
            pack_utilisation = _clean_value(pack_load_value / (instance.scenario.pack_minutes_capacity_per_worker * pack))
        else:
            pack_utilisation = 0.0
        rows.append(
            {
                "period": period,
                "label": f"P{period + 1}",
                "regular_available": regular_workers,
                "temp_workers": temp,
                "overtime_workers": overtime,
                "total_available_workers": total_available,
                "pick_workers": pick,
                "pack_workers": pack,
                "direct_workers": direct_workers,
                "unused_capacity_workers": unused_capacity,
                "pick_load_minutes": pick_load_value,
                "pack_load_minutes": pack_load_value,
                "total_load_minutes": _clean_value(pick_load_value + pack_load_value),
                "pick_utilisation": pick_utilisation,
                "pack_utilisation": pack_utilisation,
            }
        )
    return pd.DataFrame(rows)

def _assignment_frame_from_solution(
    instance: FulfillmentInstance,
    orders: pd.DataFrame,
    x: dict[tuple[str, int], gp.Var],
) -> pd.DataFrame:
    # Recover the chosen release decision for each order
    rows = []
    for (order_id, release_period), variable in x.items():
        if variable.X > 0.5:
            order_row = orders.loc[order_id]
            completion_period = int(release_period + 1)
            flow_time = completion_period - int(order_row["arrival_period"])
            tardiness = max(0.0, completion_period - float(order_row["due_period"]))
            rows.append(
                {
                    "order_id": order_id,
                    "release_period": int(release_period),
                    "completion_period": completion_period,
                    "arrival_period": int(order_row["arrival_period"]),
                    "due_period": int(order_row["due_period"]),
                    "service_class": order_row["service_class"],
                    "priority_weight": float(order_row["priority_weight"]),
                    "flow_time_weight": float(order_row["flow_time_weight"]),
                    "item_count": int(order_row["item_count"]),
                    "pick_minutes": float(order_row["pick_minutes"]),
                    "pack_minutes": float(order_row["pack_minutes"]),
                    "total_volume": float(order_row["total_volume"]),
                    "flow_time_periods": float(flow_time),
                    "tardiness_periods": float(tardiness),
                }
            )
    assignment = pd.DataFrame(rows)
    if assignment.empty:
        return _empty_assignment_frame()
    return assignment.sort_values(["release_period", "due_period", "order_id"]).reset_index(drop=True)

def _build_common_model_parts(
    instance: FulfillmentInstance,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, list[int]], list[int]]:
    # Collect shared tables and sets used by both formulations
    orders = instance.orders.set_index("order_id")
    periods = instance.periods.set_index("period")
    shift_coverage = _extract_shift_coverage(instance)
    release_periods = instance.release_periods
    return orders, periods, shift_coverage, release_periods

def _candidate_release_periods(
    order: pd.Series | Any,
    release_periods: list[int],
    latest_release_override: int | None = None,
) -> list[int]:
    # Return feasible release periods for one order
    if hasattr(order, "latest_release_period"):
        latest_release = int(order.latest_release_period)
        arrival_period = int(order.arrival_period)
    else:
        latest_release = int(order["latest_release_period"])
        arrival_period = int(order["arrival_period"])
    if latest_release_override is not None:
        latest_release = min(latest_release, int(latest_release_override))
    # Candidate filtering is a major speed lever: 
    # we never need to consider releases before arrival, and once zero tardiness is already proven we can safely drop tardy releases from the exact search.
    return [period for period in release_periods if arrival_period <= period <= latest_release]

def solve_integrated_model(
    instance: FulfillmentInstance,
    time_limit: int = 60,
    warm_start_result: ModelResult | None = None,
    objective_weights: ObjectiveWeights | None = None,
) -> ModelResult:
    # Solve the integrated release-and-staffing MIP for one instance
    objective_weights = _resolve_objective_weights(objective_weights)
    orders, periods, shift_coverage, release_periods = _build_common_model_parts(instance)
    # If the benchmark already proves that every order can be completed on time,
    # then tardy release candidates are dominated because tardiness carries an overwhelming objective penalty.
    zero_tardiness_proven = (
        warm_start_result is not None
        and warm_start_result.late_orders == 0
        and abs(warm_start_result.weighted_tardiness) <= 1e-6
    )
    model = gp.Model(f"integrated_{instance.scenario.name}")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = time_limit
    model.Params.MIPGap = 0.0
    model.Params.MIPFocus = 2
    model.Params.Heuristics = 0.05
    model.Params.Threads = 1
    x: dict[tuple[str, int], gp.Var] = {}
    for order in orders.itertuples():
        latest_release_override = int(order.due_period) - 1 if zero_tardiness_proven else None
        for release_period in _candidate_release_periods(order, release_periods, latest_release_override):
            x[(order.Index, release_period)] = model.addVar(vtype=GRB.BINARY, name=f"x_{order.Index}_{release_period}")
    y = {period: model.addVar(vtype=GRB.BINARY, name=f"y_{period}") for period in release_periods}
    regular_shift = {
        row.shift_name: model.addVar(vtype=GRB.INTEGER, lb=0, ub=int(row.max_workers), name=f"regular_{row.shift_name}")
        for row in instance.shifts.itertuples(index=False)
    }
    pick_workers = {period: model.addVar(vtype=GRB.INTEGER, lb=0, name=f"pick_workers_{period}") for period in range(instance.n_periods)}
    pack_workers = {period: model.addVar(vtype=GRB.INTEGER, lb=0, name=f"pack_workers_{period}") for period in range(instance.n_periods)}
    temp_workers = {
        period: model.addVar(vtype=GRB.INTEGER, lb=0, ub=int(periods.loc[period, "max_temp_workers"]), name=f"temp_{period}")
        for period in range(instance.n_periods)
    }
    overtime_workers = {
        period: model.addVar(
            vtype=GRB.INTEGER,
            lb=0,
            ub=int(periods.loc[period, "max_overtime_workers"]),
            name=f"overtime_{period}",
        )
        for period in range(instance.n_periods)
    }
    tardiness = {order_id: model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"tardiness_{order_id}") for order_id in orders.index}
    imbalance_plus = {period: model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"imbalance_plus_{period}") for period in range(instance.n_periods)}
    imbalance_minus = {period: model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"imbalance_minus_{period}") for period in range(instance.n_periods)}
    if warm_start_result is not None and not warm_start_result.assignment.empty:
        release_lookup = warm_start_result.assignment.set_index("order_id")["release_period"].to_dict()
        active_release_periods = set(warm_start_result.assignment["release_period"].tolist())
        staffing_lookup = warm_start_result.staffing.set_index("period").to_dict("index") if not warm_start_result.staffing.empty else {}
        regular_lookup = warm_start_result.extra_metrics.get("regular_shift_workers", {})
        for (order_id, release_period), variable in x.items():
            variable.Start = 1.0 if release_lookup.get(order_id) == release_period else 0.0
        for period, variable in y.items():
            variable.Start = 1.0 if period in active_release_periods else 0.0
        for shift_name, variable in regular_shift.items():
            variable.Start = float(regular_lookup.get(shift_name, 0.0))
        for period in range(instance.n_periods):
            if period in staffing_lookup:
                pick_workers[period].Start = float(staffing_lookup[period]["pick_workers"])
                pack_workers[period].Start = float(staffing_lookup[period]["pack_workers"])
                temp_workers[period].Start = float(staffing_lookup[period]["temp_workers"])
                overtime_workers[period].Start = float(staffing_lookup[period]["overtime_workers"])
    for order in orders.itertuples():
        latest_release_override = int(order.due_period) - 1 if zero_tardiness_proven else None
        feasible_periods = _candidate_release_periods(order, release_periods, latest_release_override)
        model.addConstr(
            gp.quicksum(x[(order.Index, period)] for period in feasible_periods) == 1,
            name=f"assign_{order.Index}",
        )
    for period in release_periods:
        feasible_orders = [order_id for order_id in orders.index if (order_id, period) in x]
        model.addConstr(
            gp.quicksum(orders.loc[order_id, "total_volume"] * x[(order_id, period)] for order_id in feasible_orders)
            <= float(periods.loc[period, "wave_capacity_volume"]) * y[period],
            name=f"wave_volume_{period}",
        )
        model.addConstr(
            gp.quicksum(x[(order_id, period)] for order_id in feasible_orders)
            <= int(periods.loc[period, "wave_order_limit"]) * y[period],
            name=f"wave_orders_{period}",
        )
    pick_load: dict[int, gp.LinExpr] = {}
    pack_load: dict[int, gp.LinExpr] = {}
    for period in range(instance.n_periods):
        pick_load[period] = gp.quicksum(
            orders.loc[order_id, "pick_minutes"] * variable
            for (order_id, release_period), variable in x.items()
            if release_period == period
        )
        if period == 0:
            pack_load[period] = gp.LinExpr(0.0)
        else:
            pack_load[period] = gp.quicksum(
                orders.loc[order_id, "pack_minutes"] * variable
                for (order_id, release_period), variable in x.items()
                if release_period == period - 1
            )
    regular_available = {
        period: gp.quicksum(shift_coverage[shift_name][period] * regular_shift[shift_name] for shift_name in regular_shift)
        for period in range(instance.n_periods)
    }
    average_workload = float((orders["pick_minutes"].sum() + orders["pack_minutes"].sum()) / instance.n_periods)
    for period in range(instance.n_periods):
        model.addConstr(
            pick_load[period] <= instance.scenario.pick_minutes_capacity_per_worker * pick_workers[period],
            name=f"pick_capacity_{period}",
        )
        model.addConstr(
            pack_load[period] <= instance.scenario.pack_minutes_capacity_per_worker * pack_workers[period],
            name=f"pack_capacity_{period}",
        )
        model.addConstr(
            pick_workers[period] + pack_workers[period]
            <= regular_available[period] + temp_workers[period] + overtime_workers[period],
            name=f"worker_balance_{period}",
        )
        model.addConstr(
            pick_load[period] + pack_load[period] - average_workload
            == imbalance_plus[period] - imbalance_minus[period],
            name=f"imbalance_{period}",
        )
    weighted_flow_time = gp.quicksum(
        orders.loc[order_id, "flow_time_weight"] * ((release_period + 1) - int(orders.loc[order_id, "arrival_period"])) * variable
        for (order_id, release_period), variable in x.items()
    )
    for order in orders.itertuples():
        latest_release_override = int(order.due_period) - 1 if zero_tardiness_proven else None
        completion_expression = gp.quicksum(
            (release_period + 1) * x[(order.Index, release_period)]
            for release_period in _candidate_release_periods(order, release_periods, latest_release_override)
        )
        model.addConstr(
            tardiness[order.Index] >= completion_expression - int(order.due_period),
            name=f"tardiness_def_{order.Index}",
        )
    weighted_tardiness = gp.quicksum(orders.loc[order_id, "priority_weight"] * tardiness[order_id] for order_id in orders.index)
    labour_cost = (
        gp.quicksum(float(row.cost_per_worker) * regular_shift[row.shift_name] for row in instance.shifts.itertuples(index=False))
        + gp.quicksum(instance.scenario.temp_hourly_cost * temp_workers[period] for period in range(instance.n_periods))
        + gp.quicksum(instance.scenario.overtime_hourly_cost * overtime_workers[period] for period in range(instance.n_periods))
        + gp.quicksum(instance.scenario.wave_opening_cost * y[period] for period in release_periods)
    )
    balance_deviation = gp.quicksum(imbalance_plus[period] + imbalance_minus[period] for period in range(instance.n_periods))

    model.ModelSense = GRB.MINIMIZE
    # Objective priority:
    # 1. weighted tardiness dominates everything else
    # 2. weighted flow time discourages unnecessarily late on-time releases
    # 3. labour and balance terms choose the cheapest stable plan among those service-feasible release decisions
    model.setObjective(
        objective_weights.tardiness * weighted_tardiness
        + objective_weights.flow_time * weighted_flow_time
        + labour_cost
        + objective_weights.balance * balance_deviation
    )
    model.optimize()

    status = _make_model_name(model.Status)
    if not model.SolCount:
        empty_assignment = _empty_assignment_frame()
        empty_staffing = _empty_staffing_frame()
        return ModelResult(
            scenario_name=instance.scenario.name,
            model_name="integrated_exact",
            status=status,
            objective_value=None,
            weighted_tardiness=float("nan"),
            weighted_flow_time=float("nan"),
            labour_cost=float("nan"),
            balance_deviation=float("nan"),
            active_waves=0,
            late_orders=0,
            total_tardiness_periods=0.0,
            mean_flow_time_periods=float("nan"),
            regular_worker_hours=0.0,
            temp_worker_hours=0.0,
            overtime_worker_hours=0.0,
            solve_time_seconds=float(model.Runtime),
            mip_gap=None,
            assignment=empty_assignment,
            staffing=empty_staffing,
            period_summary=empty_staffing.copy(),
            order_summary=empty_assignment.copy(),
            extra_metrics={"solver_status_code": model.Status},
        )

    assignment = _assignment_frame_from_solution(instance, orders, x)
    staffing = _build_staffing_output(
        instance=instance,
        regular_available=regular_available,
        pick_workers=pick_workers,
        pack_workers=pack_workers,
        temp_workers=temp_workers,
        overtime_workers=overtime_workers,
        pick_load=pick_load,
        pack_load=pack_load,
    )

    regular_worker_hours = _clean_value(
        sum(float(row.length_hours) * regular_shift[row.shift_name].X for row in instance.shifts.itertuples(index=False))
    )
    temp_worker_hours = _clean_value(sum(variable.X for variable in temp_workers.values()))
    overtime_worker_hours = _clean_value(sum(variable.X for variable in overtime_workers.values()))

    return ModelResult(
        scenario_name=instance.scenario.name,
        model_name="integrated_exact",
        status=status,
        objective_value=_clean_value(model.ObjVal),
        weighted_tardiness=_clean_value(weighted_tardiness.getValue()),
        weighted_flow_time=_clean_value(weighted_flow_time.getValue()),
        labour_cost=_clean_value(labour_cost.getValue()),
        balance_deviation=_clean_value(balance_deviation.getValue()),
        active_waves=int(round(sum(y[period].X for period in release_periods))),
        late_orders=int((assignment["tardiness_periods"] > 0).sum()),
        total_tardiness_periods=_clean_value(assignment["tardiness_periods"].sum()),
        mean_flow_time_periods=_clean_value(assignment["flow_time_periods"].mean()),
        regular_worker_hours=regular_worker_hours,
        temp_worker_hours=temp_worker_hours,
        overtime_worker_hours=overtime_worker_hours,
        solve_time_seconds=_clean_value(model.Runtime),
        mip_gap=_safe_float_attribute(model, "MIPGap") if model.IsMIP else None,
        assignment=assignment,
        staffing=staffing,
        period_summary=staffing.copy(),
        order_summary=assignment.copy(),
        extra_metrics={
            "regular_shift_workers": {shift_name: _clean_value(variable.X) for shift_name, variable in regular_shift.items()},
            "solver_status_code": model.Status,
            "zero_tardiness_proven_by_warm_start": zero_tardiness_proven,
            "objective_weights": {
                "tardiness": objective_weights.tardiness,
                "flow_time": objective_weights.flow_time,
                "balance": objective_weights.balance,
            },
        },
    )


def _solve_staffing_subproblem(
    instance: FulfillmentInstance,
    assignment: pd.DataFrame,
    model_name: str,
    time_limit: int = 60,
    objective_weights: ObjectiveWeights | None = None,
) -> ModelResult:
    # Solve the staffing model for a fixed wave-assignment plan
    objective_weights = _resolve_objective_weights(objective_weights)
    periods = instance.periods.set_index("period")
    shift_coverage = _extract_shift_coverage(instance)

    # In the sequential benchmark, assignment is already fixed. 
    # This model only chooses the cheapest staffing plan that can execute that workload profile.
    pick_load_by_period = assignment.groupby("release_period")["pick_minutes"].sum().to_dict()
    pack_load_by_period = assignment.groupby("completion_period")["pack_minutes"].sum().to_dict()
    model = gp.Model(f"staffing_{instance.scenario.name}_{model_name}")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = time_limit
    model.Params.MIPGap = 0.0
    model.Params.Threads = 1
    regular_shift = {
        row.shift_name: model.addVar(vtype=GRB.INTEGER, lb=0, ub=int(row.max_workers), name=f"regular_{row.shift_name}")
        for row in instance.shifts.itertuples(index=False)
    }
    pick_workers = {period: model.addVar(vtype=GRB.INTEGER, lb=0, name=f"pick_workers_{period}") for period in range(instance.n_periods)}
    pack_workers = {period: model.addVar(vtype=GRB.INTEGER, lb=0, name=f"pack_workers_{period}") for period in range(instance.n_periods)}
    temp_workers = {
        period: model.addVar(vtype=GRB.INTEGER, lb=0, ub=int(periods.loc[period, "max_temp_workers"]), name=f"temp_{period}")
        for period in range(instance.n_periods)
    }
    overtime_workers = {
        period: model.addVar(
            vtype=GRB.INTEGER,
            lb=0,
            ub=int(periods.loc[period, "max_overtime_workers"]),
            name=f"overtime_{period}",
        )
        for period in range(instance.n_periods)
    }
    imbalance_plus = {period: model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"imbalance_plus_{period}") for period in range(instance.n_periods)}
    imbalance_minus = {period: model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"imbalance_minus_{period}") for period in range(instance.n_periods)}
    regular_available = {
        period: gp.quicksum(shift_coverage[shift_name][period] * regular_shift[shift_name] for shift_name in regular_shift)
        for period in range(instance.n_periods)
    }

    total_workload = float(assignment["pick_minutes"].sum() + assignment["pack_minutes"].sum())
    average_workload = total_workload / instance.n_periods
    pick_load: dict[int, float] = {}
    pack_load: dict[int, float] = {}
    for period in range(instance.n_periods):
        pick_load[period] = float(pick_load_by_period.get(period, 0.0))
        pack_load[period] = float(pack_load_by_period.get(period, 0.0))

        model.addConstr(
            pick_load[period] <= instance.scenario.pick_minutes_capacity_per_worker * pick_workers[period],
            name=f"pick_capacity_{period}",
        )
        model.addConstr(
            pack_load[period] <= instance.scenario.pack_minutes_capacity_per_worker * pack_workers[period],
            name=f"pack_capacity_{period}",
        )
        model.addConstr(
            pick_workers[period] + pack_workers[period]
            <= regular_available[period] + temp_workers[period] + overtime_workers[period],
            name=f"worker_balance_{period}",
        )
        model.addConstr(
            pick_load[period] + pack_load[period] - average_workload
            == imbalance_plus[period] - imbalance_minus[period],
            name=f"imbalance_{period}",
        )

    labour_cost = (
        gp.quicksum(float(row.cost_per_worker) * regular_shift[row.shift_name] for row in instance.shifts.itertuples(index=False))
        + gp.quicksum(instance.scenario.temp_hourly_cost * temp_workers[period] for period in range(instance.n_periods))
        + gp.quicksum(instance.scenario.overtime_hourly_cost * overtime_workers[period] for period in range(instance.n_periods))
        + instance.scenario.wave_opening_cost * assignment["release_period"].nunique()
    )
    balance_deviation = gp.quicksum(imbalance_plus[period] + imbalance_minus[period] for period in range(instance.n_periods))
    model.ModelSense = GRB.MINIMIZE
    model.setObjective(labour_cost + objective_weights.balance * balance_deviation)
    model.optimize()

    staffing = _build_staffing_output(
        instance=instance,
        regular_available=regular_available,
        pick_workers=pick_workers,
        pack_workers=pack_workers,
        temp_workers=temp_workers,
        overtime_workers=overtime_workers,
        pick_load=pick_load,
        pack_load=pack_load,
    )
    regular_worker_hours = _clean_value(
        sum(float(row.length_hours) * regular_shift[row.shift_name].X for row in instance.shifts.itertuples(index=False))
    )
    temp_worker_hours = _clean_value(sum(variable.X for variable in temp_workers.values()))
    overtime_worker_hours = _clean_value(sum(variable.X for variable in overtime_workers.values()))

    return ModelResult(
        scenario_name=instance.scenario.name,
        model_name=model_name,
        status=_make_model_name(model.Status),
        objective_value=_clean_value(model.ObjVal) if model.SolCount else None,
        weighted_tardiness=_clean_value((assignment["priority_weight"] * assignment["tardiness_periods"]).sum()),
        weighted_flow_time=_clean_value((assignment["flow_time_weight"] * assignment["flow_time_periods"]).sum()),
        labour_cost=_clean_value(labour_cost.getValue()) if model.SolCount else float("nan"),
        balance_deviation=_clean_value(balance_deviation.getValue()) if model.SolCount else float("nan"),
        active_waves=int(assignment["release_period"].nunique()),
        late_orders=int((assignment["tardiness_periods"] > 0).sum()),
        total_tardiness_periods=_clean_value(assignment["tardiness_periods"].sum()),
        mean_flow_time_periods=_clean_value(assignment["flow_time_periods"].mean()),
        regular_worker_hours=regular_worker_hours,
        temp_worker_hours=temp_worker_hours,
        overtime_worker_hours=overtime_worker_hours,
        solve_time_seconds=_clean_value(model.Runtime),
        mip_gap=_safe_float_attribute(model, "MIPGap") if model.IsMIP else None,
        assignment=assignment.copy(),
        staffing=staffing,
        period_summary=staffing.copy(),
        order_summary=assignment.copy(),
        extra_metrics={
            "regular_shift_workers": {shift_name: _clean_value(variable.X) for shift_name, variable in regular_shift.items()},
            "solver_status_code": model.Status,
            "objective_weights": {
                "tardiness": objective_weights.tardiness,
                "flow_time": objective_weights.flow_time,
                "balance": objective_weights.balance,
            },
        },
    )

def _solve_sequential_wave_assignment(
    instance: FulfillmentInstance,
    time_limit: int = 60,
    objective_weights: ObjectiveWeights | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    # Solve the release-only stage of the sequential benchmark
    objective_weights = _resolve_objective_weights(objective_weights)
    orders, periods, _, release_periods = _build_common_model_parts(instance)
    model = gp.Model(f"sequential_wave_assignment_{instance.scenario.name}")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = time_limit
    model.Params.MIPGap = 0.0
    model.Params.MIPFocus = 1
    model.Params.Threads = 1
    x: dict[tuple[str, int], gp.Var] = {}
    for order in orders.itertuples():
        for release_period in _candidate_release_periods(order, release_periods):
            x[(order.Index, release_period)] = model.addVar(vtype=GRB.BINARY, name=f"x_{order.Index}_{release_period}")
    y = {period: model.addVar(vtype=GRB.BINARY, name=f"y_{period}") for period in release_periods}
    tardiness = {order_id: model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"tardiness_{order_id}") for order_id in orders.index}
    for order in orders.itertuples():
        feasible_periods = _candidate_release_periods(order, release_periods)
        model.addConstr(
            gp.quicksum(x[(order.Index, period)] for period in feasible_periods) == 1,
            name=f"assign_{order.Index}",
        )
    for period in release_periods:
        feasible_orders = [order_id for order_id in orders.index if (order_id, period) in x]
        model.addConstr(
            gp.quicksum(orders.loc[order_id, "total_volume"] * x[(order_id, period)] for order_id in feasible_orders)
            <= float(periods.loc[period, "wave_capacity_volume"]) * y[period],
            name=f"wave_volume_{period}",
        )
        model.addConstr(
            gp.quicksum(x[(order_id, period)] for order_id in feasible_orders)
            <= int(periods.loc[period, "wave_order_limit"]) * y[period],
            name=f"wave_orders_{period}",
        )
    weighted_flow_time = gp.quicksum(
        orders.loc[order_id, "flow_time_weight"] * ((release_period + 1) - int(orders.loc[order_id, "arrival_period"])) * variable
        for (order_id, release_period), variable in x.items()
    )
    for order in orders.itertuples():
        completion_expression = gp.quicksum(
            (release_period + 1) * x[(order.Index, release_period)]
            for release_period in _candidate_release_periods(order, release_periods)
        )
        model.addConstr(
            tardiness[order.Index] >= completion_expression - int(order.due_period),
            name=f"tardiness_def_{order.Index}",
        )
    weighted_tardiness = gp.quicksum(orders.loc[order_id, "priority_weight"] * tardiness[order_id] for order_id in orders.index)
    wave_opening_cost = gp.quicksum(instance.scenario.wave_opening_cost * y[period] for period in release_periods)

    model.ModelSense = GRB.MINIMIZE
    # Stage 1 of the sequential benchmark ignores staffing. 
    # It therefore optimises service timing and wave usage only, which is exactly the modelling limitation we want to benchmark against.
    model.setObjective(
        objective_weights.tardiness * weighted_tardiness
        + objective_weights.flow_time * weighted_flow_time
        + wave_opening_cost
    )
    model.optimize()
    if not model.SolCount:
        raise ValueError(f"Sequential benchmark could not find a feasible wave plan for scenario {instance.scenario.name}.")
    assignment = _assignment_frame_from_solution(instance, orders, x)
    assignment_info = {
        "status": _make_model_name(model.Status),
        "runtime": _clean_value(model.Runtime),
        "mip_gap": _safe_float_attribute(model, "MIPGap") if model.IsMIP else None,
        "objective_value": _clean_value(model.ObjVal),
        "wave_opening_cost": _clean_value(wave_opening_cost.getValue()),
        "objective_weights": {
            "tardiness": objective_weights.tardiness,
            "flow_time": objective_weights.flow_time,
            "balance": objective_weights.balance,
        },
    }
    return assignment, assignment_info

def solve_sequential_benchmark(
    instance: FulfillmentInstance,
    time_limit: int = 60,
    objective_weights: ObjectiveWeights | None = None,
) -> ModelResult:
    # Solve the two-stage exact benchmark for one instance
    # The benchmark is a true two-stage exact policy: release planning first, labour planning second.
    objective_weights = _resolve_objective_weights(objective_weights)
    assignment, assignment_info = _solve_sequential_wave_assignment(
        instance=instance,
        time_limit=time_limit,
        objective_weights=objective_weights,
    )
    result = _solve_staffing_subproblem(
        instance=instance,
        assignment=assignment,
        model_name="sequential_benchmark",
        time_limit=time_limit,
        objective_weights=objective_weights,
    )
    result.status = assignment_info["status"] if assignment_info["status"] != "OPTIMAL" else result.status
    result.solve_time_seconds = _clean_value(result.solve_time_seconds + float(assignment_info["runtime"]))
    result.mip_gap = assignment_info["mip_gap"] if assignment_info["status"] != "OPTIMAL" else result.mip_gap
    result.extra_metrics.update(
        {
            "assignment_stage_status": assignment_info["status"],
            "assignment_stage_runtime": assignment_info["runtime"],
            "assignment_stage_mip_gap": assignment_info["mip_gap"],
            "assignment_stage_objective_value": assignment_info["objective_value"],
            "assignment_stage_wave_opening_cost": assignment_info["wave_opening_cost"],
            "objective_weights": assignment_info["objective_weights"],
        }
    )
    return result
