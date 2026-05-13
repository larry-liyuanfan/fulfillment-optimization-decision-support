from pathlib import Path
import re

import pandas as pd
import matplotlib.pyplot as plt


# =============================================================================
# Module 4 — Solver Performance, Reproducibility, and Validation
# Owner: Liyuan Fan
#
# This script post-processes raw Mac/vendor and Windows/official outputs.
# It generates cleaned CSV tables and PNG figures for Module 4 deliverables.
# =============================================================================


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "raw_outputs"
CSV_DIR = BASE_DIR / "csv"
FIG_DIR = BASE_DIR / "figures"

CSV_DIR.mkdir(exist_ok=True)
FIG_DIR.mkdir(exist_ok=True)


# =============================================================================
# Helpers
# =============================================================================

def read_csv(name: str) -> pd.DataFrame:
    """Read a CSV from raw_outputs/ with a clear error if missing."""
    path = RAW_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return pd.read_csv(path)


def find_source_file(filename: str) -> Path | None:
    """
    Search source files in several likely locations.

    Recommended placement:
        Module4_LiyuanFan/raw_outputs/models.py
        Module4_LiyuanFan/raw_outputs/experiments.py

    Also supports:
        Module4_LiyuanFan/source_files/models.py
        Module4_LiyuanFan/../90014_v2/src/fulfillment_optim/models.py
        Module4_LiyuanFan/../90014/src/fulfillment_optim/models.py
    """
    candidates = [
        RAW_DIR / filename,
        BASE_DIR / "source_files" / filename,
        BASE_DIR / filename,
        BASE_DIR.parent / "90014_v2" / "src" / "fulfillment_optim" / filename,
        BASE_DIR.parent / "90014" / "src" / "fulfillment_optim" / filename,
    ]

    for path in candidates:
        if path.exists():
            return path
    return None


def clean_float(value, digits: int = 6):
    """Convert to a rounded float where possible."""
    try:
        return round(float(value), digits)
    except Exception:
        return value


def safe_numeric(series: pd.Series) -> pd.Series:
    """Convert a Series to numeric values where possible."""
    return pd.to_numeric(series, errors="coerce")


# =============================================================================
# 1. Environment comparison
# =============================================================================

def generate_environment_comparison() -> None:
    """Summarise the tested environments and the observed key benchmark result."""
    df = pd.DataFrame(
        [
            {
                "environment": "Windows venv",
                "gurobi_source": "official installed Gurobi",
                "vendor_status": "failed: missing gurobipy._batch",
                "labour_shortage_sequential_benchmark_cost": 748.65,
                "interpretation": "Windows official-Gurobi result; internally stable",
            },
            {
                "environment": "Windows Anaconda",
                "gurobi_source": "official installed Gurobi",
                "vendor_status": "failed: missing gurobipy._batch",
                "labour_shortage_sequential_benchmark_cost": 748.65,
                "interpretation": "Windows official-Gurobi result; internally stable",
            },
            {
                "environment": "macOS venv",
                "gurobi_source": "vendored Gurobi",
                "vendor_status": "works after macOS security handling",
                "labour_shortage_sequential_benchmark_cost": 704.89,
                "interpretation": "matches report baseline",
            },
        ]
    )

    df.to_csv(CSV_DIR / "module4_environment_comparison.csv", index=False)


# =============================================================================
# 2. Three-run consistency and solve-time summary
# =============================================================================

def generate_three_run_consistency() -> None:
    """
    Generate repeated-run consistency table from three Windows Anaconda /
    official-Gurobi runs.
    """
    rows = []

    # Format:
    # (labour_cost, weighted_flow_time, balance_deviation, late_orders, solve_time_seconds)
    run_data = {
        1: {
            ("base", "integrated_exact"): (609.40, 227.2, 371.746667, 0, 1.749),
            ("base", "sequential_benchmark"): (704.92, 208.2, 453.666667, 0, 0.014),
            ("promotion", "integrated_exact"): (704.92, 333.8, 428.380000, 0, 7.192),
            ("promotion", "sequential_benchmark"): (792.44, 328.2, 429.920000, 0, 0.012),
            ("tight_due_dates", "integrated_exact"): (661.16, 278.4, 276.980000, 0, 0.426),
            ("tight_due_dates", "sequential_benchmark"): (678.64, 274.0, 274.980000, 0, 0.013),
            ("labour_shortage", "integrated_exact"): (613.77, 238.0, 290.608333, 0, 3.464),
            ("labour_shortage", "sequential_benchmark"): (748.65, 223.4, 340.986667, 0, 0.012),
        },
        2: {
            ("base", "integrated_exact"): (609.40, 227.2, 371.746667, 0, 1.838),
            ("base", "sequential_benchmark"): (704.92, 208.2, 453.666667, 0, 0.014),
            ("promotion", "integrated_exact"): (704.92, 333.8, 428.380000, 0, 7.487),
            ("promotion", "sequential_benchmark"): (792.44, 328.2, 429.920000, 0, 0.012),
            ("tight_due_dates", "integrated_exact"): (661.16, 278.4, 276.980000, 0, 0.412),
            ("tight_due_dates", "sequential_benchmark"): (678.64, 274.0, 274.980000, 0, 0.012),
            ("labour_shortage", "integrated_exact"): (613.77, 238.0, 290.608333, 0, 3.664),
            ("labour_shortage", "sequential_benchmark"): (748.65, 223.4, 340.986667, 0, 0.011),
        },
        3: {
            ("base", "integrated_exact"): (609.40, 227.2, 371.746667, 0, 1.756),
            ("base", "sequential_benchmark"): (704.92, 208.2, 453.666667, 0, 0.013),
            ("promotion", "integrated_exact"): (704.92, 333.8, 428.380000, 0, 6.955),
            ("promotion", "sequential_benchmark"): (792.44, 328.2, 429.920000, 0, 0.012),
            ("tight_due_dates", "integrated_exact"): (661.16, 278.4, 276.980000, 0, 0.382),
            ("tight_due_dates", "sequential_benchmark"): (678.64, 274.0, 274.980000, 0, 0.009),
            ("labour_shortage", "integrated_exact"): (613.77, 238.0, 290.608333, 0, 3.355),
            ("labour_shortage", "sequential_benchmark"): (748.65, 223.4, 340.986667, 0, 0.012),
        },
    }

    for run_id, entries in run_data.items():
        for (scenario, model), values in entries.items():
            labour_cost, weighted_flow_time, balance_deviation, late_orders, solve_time = values
            rows.append(
                {
                    "run_id": run_id,
                    "scenario": scenario,
                    "model": model,
                    "status": "OPTIMAL",
                    "labour_cost": labour_cost,
                    "weighted_flow_time": weighted_flow_time,
                    "balance_deviation": balance_deviation,
                    "late_orders": late_orders,
                    "solve_time_seconds": solve_time,
                }
            )

    df = pd.DataFrame(rows)
    df.to_csv(CSV_DIR / "module4_three_run_consistency.csv", index=False)

    summary = (
        df.groupby(["scenario", "model"])
        .agg(
            mean_solve_time_seconds=("solve_time_seconds", "mean"),
            min_solve_time_seconds=("solve_time_seconds", "min"),
            max_solve_time_seconds=("solve_time_seconds", "max"),
            labour_cost_unique_count=("labour_cost", "nunique"),
            weighted_flow_time_unique_count=("weighted_flow_time", "nunique"),
            balance_deviation_unique_count=("balance_deviation", "nunique"),
            late_orders_unique_count=("late_orders", "nunique"),
        )
        .reset_index()
    )

    summary["labour_cost_stable"] = summary["labour_cost_unique_count"] == 1
    summary["weighted_flow_time_stable"] = summary["weighted_flow_time_unique_count"] == 1
    summary["balance_deviation_stable"] = summary["balance_deviation_unique_count"] == 1
    summary["late_orders_stable"] = summary["late_orders_unique_count"] == 1

    summary.to_csv(CSV_DIR / "module4_solve_time_summary.csv", index=False)


# =============================================================================
# 3. Mac/vendor vs Windows/official KPI comparison
# =============================================================================

def generate_mac_vs_windows_kpi_comparison() -> None:
    """Compare labour_shortage summary KPIs between Mac/vendor and Windows/official."""
    mac = read_csv("mac_vendor_model_comparison.csv")
    win = read_csv("win_official_model_comparison.csv")

    mac_ls = mac[mac["scenario"] == "labour_shortage"].iloc[0]
    win_ls = win[win["scenario"] == "labour_shortage"].iloc[0]

    rows = [
        {
            "metric": "sequential_labour_cost",
            "mac_vendor": mac_ls["sequential_labour_cost"],
            "windows_official": win_ls["sequential_labour_cost"],
            "difference": win_ls["sequential_labour_cost"] - mac_ls["sequential_labour_cost"],
        },
        {
            "metric": "sequential_temp_hours",
            "mac_vendor": mac_ls["sequential_temp_hours"],
            "windows_official": win_ls["sequential_temp_hours"],
            "difference": win_ls["sequential_temp_hours"] - mac_ls["sequential_temp_hours"],
        },
        {
            "metric": "sequential_regular_hours",
            "mac_vendor": mac_ls["sequential_regular_hours"],
            "windows_official": win_ls["sequential_regular_hours"],
            "difference": win_ls["sequential_regular_hours"] - mac_ls["sequential_regular_hours"],
        },
        {
            "metric": "sequential_active_waves",
            "mac_vendor": mac_ls["sequential_active_waves"],
            "windows_official": win_ls["sequential_active_waves"],
            "difference": win_ls["sequential_active_waves"] - mac_ls["sequential_active_waves"],
        },
        {
            "metric": "cost_saving_pct",
            "mac_vendor": mac_ls["cost_saving_pct"],
            "windows_official": win_ls["cost_saving_pct"],
            "difference": win_ls["cost_saving_pct"] - mac_ls["cost_saving_pct"],
        },
    ]

    df = pd.DataFrame(rows)
    df.to_csv(CSV_DIR / "module4_mac_vs_windows_kpi_comparison.csv", index=False)


# =============================================================================
# 4. Assignment and staffing differences
# =============================================================================

def generate_assignment_difference() -> None:
    """Compare order release periods between Mac/vendor and Windows/official."""
    mac = read_csv("mac_vendor_labour_shortage_sequential_benchmark_assignments.csv")
    win = read_csv("win_official_labour_shortage_sequential_benchmark_assignments.csv")

    order_col = "order_id"
    release_col = "release_period"

    if order_col not in mac.columns:
        order_col = mac.columns[0]

    if release_col not in mac.columns:
        possible = [c for c in mac.columns if "release" in c.lower()]
        if not possible:
            raise ValueError(f"Cannot identify release column. Columns are: {list(mac.columns)}")
        release_col = possible[0]

    merged = mac[[order_col, release_col]].merge(
        win[[order_col, release_col]],
        on=order_col,
        suffixes=("_mac_vendor", "_windows_official"),
    )

    merged["release_difference"] = (
        merged[f"{release_col}_windows_official"] - merged[f"{release_col}_mac_vendor"]
    )

    changed = merged[merged["release_difference"] != 0].copy()
    changed.to_csv(CSV_DIR / "module4_assignment_difference.csv", index=False)

    mac_counts = (
        mac.groupby(release_col)
        .size()
        .reset_index(name="mac_vendor_order_count")
        .rename(columns={release_col: "release_period"})
    )

    win_counts = (
        win.groupby(release_col)
        .size()
        .reset_index(name="windows_official_order_count")
        .rename(columns={release_col: "release_period"})
    )

    release_counts = mac_counts.merge(win_counts, on="release_period", how="outer").fillna(0)
    release_counts["difference"] = (
        release_counts["windows_official_order_count"] - release_counts["mac_vendor_order_count"]
    )

    release_counts.to_csv(CSV_DIR / "module4_assignment_release_count_check.csv", index=False)


def generate_staffing_difference() -> None:
    """Compare staffing profiles between Mac/vendor and Windows/official."""
    mac = read_csv("mac_vendor_labour_shortage_sequential_benchmark_staffing.csv")
    win = read_csv("win_official_labour_shortage_sequential_benchmark_staffing.csv")

    key = "period"
    if key not in mac.columns:
        key = mac.columns[0]

    cols = [
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
    cols = [c for c in cols if c in mac.columns and c in win.columns]

    merged = mac[[key] + cols].merge(
        win[[key] + cols],
        on=key,
        suffixes=("_mac_vendor", "_windows_official"),
    )

    for c in cols:
        merged[f"{c}_difference"] = (
            merged[f"{c}_windows_official"] - merged[f"{c}_mac_vendor"]
        )

    merged.to_csv(CSV_DIR / "module4_staffing_difference.csv", index=False)


# =============================================================================
# 5. Stage-1 objective diagnostic
# =============================================================================

def generate_stage1_objective_diagnostic() -> None:
    """
    Recompute the sequential Stage-1 objective for the Mac/vendor and
    Windows/official release assignments.

    Sequential Stage 1 objective:
        10000 * weighted_tardiness
        + 2 * weighted_flow_time
        + wave_opening_cost

    It does NOT include staffing cost or balance.
    """
    mac = read_csv("mac_vendor_labour_shortage_sequential_benchmark_assignments.csv")
    win = read_csv("win_official_labour_shortage_sequential_benchmark_assignments.csv")

    tardiness_weight = 10000.0
    flow_time_weight = 2.0
    wave_opening_cost_per_wave = 8.0

    required_cols = [
        "priority_weight",
        "tardiness_periods",
        "flow_time_weight",
        "flow_time_periods",
        "release_period",
    ]

    for label, df in [("mac_vendor", mac), ("windows_official", win)]:
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"{label} assignment file is missing columns: {missing}")

    def compute(df: pd.DataFrame, source: str) -> dict:
        weighted_tardiness = float((df["priority_weight"] * df["tardiness_periods"]).sum())
        weighted_flow_time = float((df["flow_time_weight"] * df["flow_time_periods"]).sum())
        active_waves = int(df["release_period"].nunique())
        wave_opening_cost = float(active_waves * wave_opening_cost_per_wave)

        stage1_objective = (
            tardiness_weight * weighted_tardiness
            + flow_time_weight * weighted_flow_time
            + wave_opening_cost
        )

        return {
            "source": source,
            "weighted_tardiness": clean_float(weighted_tardiness),
            "weighted_flow_time": clean_float(weighted_flow_time),
            "active_waves": active_waves,
            "wave_opening_cost": clean_float(wave_opening_cost),
            "stage1_objective": clean_float(stage1_objective),
        }

    mac_row = compute(mac, "mac_vendor")
    win_row = compute(win, "windows_official")

    diff_row = {
        "source": "difference_windows_minus_mac",
        "weighted_tardiness": clean_float(
            win_row["weighted_tardiness"] - mac_row["weighted_tardiness"]
        ),
        "weighted_flow_time": clean_float(
            win_row["weighted_flow_time"] - mac_row["weighted_flow_time"]
        ),
        "active_waves": win_row["active_waves"] - mac_row["active_waves"],
        "wave_opening_cost": clean_float(
            win_row["wave_opening_cost"] - mac_row["wave_opening_cost"]
        ),
        "stage1_objective": clean_float(
            win_row["stage1_objective"] - mac_row["stage1_objective"]
        ),
    }

    df = pd.DataFrame([mac_row, win_row, diff_row])
    df.to_csv(CSV_DIR / "module4_stage1_objective_diagnostic.csv", index=False)


# =============================================================================
# 6. Validation audit
# =============================================================================

def audit_one_validation_file(environment: str, file_name: str) -> dict:
    """Audit one validation_summary.csv file."""
    df = read_csv(file_name)

    required_cols = {"scenario", "model", "check", "passed", "value"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"{file_name} missing columns: {missing}")

    passed = df["passed"].astype(bool)
    numeric_values = safe_numeric(df["value"])

    total_checks = int(len(df))
    passed_checks = int(passed.sum())
    failed_checks = int(total_checks - passed_checks)
    max_abs_value = float(numeric_values.abs().max()) if numeric_values.notna().any() else 0.0

    failed_names = "; ".join(
        df.loc[~passed, "check"].astype(str).dropna().unique().tolist()
    )

    return {
        "environment": environment,
        "source_file": file_name,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "max_abs_validation_value": clean_float(max_abs_value),
        "all_passed": failed_checks == 0 and abs(max_abs_value) <= 1e-9,
        "failed_check_names": failed_names if failed_names else "",
    }


def generate_validation_audit() -> None:
    """Generate validation audit summary for Mac/vendor and Windows/official runs."""
    rows = []

    validation_inputs = [
        ("macOS vendored Gurobi", "mac_validation_summary.csv"),
        ("Windows official Gurobi", "win_validation_summary.csv"),
    ]

    for environment, file_name in validation_inputs:
        if (RAW_DIR / file_name).exists():
            rows.append(audit_one_validation_file(environment, file_name))

    if not rows:
        raise FileNotFoundError(
            "No validation files found. Expected raw_outputs/mac_validation_summary.csv "
            "and/or raw_outputs/win_validation_summary.csv"
        )

    pd.DataFrame(rows).to_csv(CSV_DIR / "module4_validation_audit.csv", index=False)


# =============================================================================
# 7. Solver settings summary
# =============================================================================

def extract_setting_patterns(text: str) -> list[dict]:
    """Extract common Gurobi parameter settings from source code text."""
    patterns = {
        "TimeLimit": r"model\.Params\.TimeLimit\s*=\s*([^\n#]+)",
        "MIPGap": r"model\.Params\.MIPGap\s*=\s*([^\n#]+)",
        "Threads": r"model\.Params\.Threads\s*=\s*([^\n#]+)",
        "MIPFocus": r"model\.Params\.MIPFocus\s*=\s*([^\n#]+)",
        "Heuristics": r"model\.Params\.Heuristics\s*=\s*([^\n#]+)",
        "Seed": r"model\.Params\.Seed\s*=\s*([^\n#]+)",
        "OutputFlag": r"model\.Params\.OutputFlag\s*=\s*([^\n#]+)",
    }

    rows = []
    for setting, pattern in patterns.items():
        matches = re.findall(pattern, text)

        if matches:
            for value in sorted(set(match.strip() for match in matches)):
                rows.append(
                    {
                        "setting": setting,
                        "value_found": value,
                        "explicitly_set": True,
                    }
                )
        else:
            rows.append(
                {
                    "setting": setting,
                    "value_found": "",
                    "explicitly_set": False,
                }
            )

    return rows


def generate_solver_settings_summary() -> None:
    """Generate summary of solver settings found in models.py / experiments.py."""
    models_path = find_source_file("models.py")
    experiments_path = find_source_file("experiments.py")

    if models_path is None:
        raise FileNotFoundError(
            "Could not find models.py. Put models.py in raw_outputs/ or source_files/."
        )

    model_text = models_path.read_text(encoding="utf-8")
    rows = extract_setting_patterns(model_text)

    # Extract default time_limit values from function signatures.
    default_time_limit_matches = re.findall(
        r"def\s+("
        r"solve_integrated_model|"
        r"_solve_staffing_subproblem|"
        r"_solve_sequential_wave_assignment|"
        r"solve_sequential_benchmark"
        r")\s*\([^\)]*?time_limit:\s*int\s*=\s*([0-9]+)",
        model_text,
        flags=re.DOTALL,
    )

    for function_name, default_value in default_time_limit_matches:
        rows.append(
            {
                "setting": f"default_time_limit_argument:{function_name}",
                "value_found": default_value,
                "explicitly_set": True,
            }
        )

    # Check whether experiments.py exports validation_summary.csv through validate_result.
    validation_export_found = False
    if experiments_path is not None:
        exp_text = experiments_path.read_text(encoding="utf-8")
        validation_export_found = (
            "validation_summary.csv" in exp_text
            and "validate_result" in exp_text
        )

    rows.append(
        {
            "setting": "validation_export",
            "value_found": (
                "validation_summary.csv via validate_result"
                if validation_export_found else ""
            ),
            "explicitly_set": validation_export_found,
        }
    )

    settings = pd.DataFrame(rows)

    def status_for(setting_name: str) -> str:
        subset = settings[settings["setting"] == setting_name]
        return "explicit" if bool(subset["explicitly_set"].any()) else "not found"

    settings = pd.concat(
        [
            settings,
            pd.DataFrame(
                [
                    {
                        "setting": "summary_interpretation",
                        "value_found": (
                            f"TimeLimit={status_for('TimeLimit')}; "
                            f"MIPGap={status_for('MIPGap')}; "
                            f"Threads={status_for('Threads')}; "
                            f"Seed={status_for('Seed')}"
                        ),
                        "explicitly_set": True,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    settings.to_csv(CSV_DIR / "module4_solver_settings_summary.csv", index=False)


# =============================================================================
# 8. Figures
# =============================================================================

def generate_figures() -> None:
    """Generate PNG figures for Module 4."""
    # Figure 1: labour_shortage sequential cost comparison
    kpi = pd.read_csv(CSV_DIR / "module4_mac_vs_windows_kpi_comparison.csv")
    cost_row = kpi[kpi["metric"] == "sequential_labour_cost"].iloc[0]

    labels = ["Mac/vendor", "Windows/official"]
    values = [cost_row["mac_vendor"], cost_row["windows_official"]]

    plt.figure(figsize=(6, 4))
    bars = plt.bar(labels, values)
    plt.ylabel("Sequential benchmark labour cost")
    plt.title("Labour Shortage Sequential Benchmark Cost")

    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.savefig(FIG_DIR / "module4_labour_shortage_cost_comparison.png", dpi=200)
    plt.close()

    # Figure 2: solve-time comparison using log scale
    summary = pd.read_csv(CSV_DIR / "module4_solve_time_summary.csv")
    pivot = summary.pivot(
        index="scenario",
        columns="model",
        values="mean_solve_time_seconds",
    )

    scenario_order = ["base", "promotion", "tight_due_dates", "labour_shortage"]
    pivot = pivot.loc[scenario_order]

    ax = pivot.plot(kind="bar", figsize=(8, 4))
    ax.set_yscale("log")
    ax.set_ylabel("Mean solve time (seconds, log scale)")
    ax.set_title("Module 4 Three-Run Mean Solve Time")
    ax.legend(title="Model")

    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "module4_solve_time_comparison.png", dpi=200)
    plt.close()


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    generate_environment_comparison()
    generate_three_run_consistency()
    generate_mac_vs_windows_kpi_comparison()
    generate_assignment_difference()
    generate_staffing_difference()
    generate_stage1_objective_diagnostic()
    generate_validation_audit()
    generate_solver_settings_summary()
    generate_figures()

    print("Module 4 outputs generated successfully.")
    print(f"CSV outputs: {CSV_DIR}")
    print(f"Figure outputs: {FIG_DIR}")


if __name__ == "__main__":
    main()
