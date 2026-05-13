# Project entry point for regenerating all reproducible artefacts
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
(ROOT / ".mplconfig").mkdir(parents=True, exist_ok=True)

# Keep vendored dependencies and project sources importable from the root script
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from fulfillment_optim.analysis import export_advanced_analysis
from fulfillment_optim.experiments import run_experiment_suite
from fulfillment_optim.models import ObjectiveWeights
from fulfillment_optim.reporting import export_reporting_bundle


def main() -> None:
    # Run the full experiment, analysis, and reporting pipeline
    # One command regenerates every reproducible project artefact from the deterministic scenarios and exact models.
    results_dir = ROOT / "results"
    objective_weights = ObjectiveWeights()
    suite_result = run_experiment_suite(results_dir, objective_weights=objective_weights)
    export_advanced_analysis(results_dir, suite_result=suite_result, objective_weights=objective_weights)
    export_reporting_bundle(project_root=ROOT, results_dir=results_dir)
    display_columns = [
        "scenario",
        "model",
        "status",
        "weighted_tardiness",
        "weighted_flow_time",
        "labour_cost",
        "balance_deviation",
        "late_orders",
        "temp_worker_hours",
        "overtime_worker_hours",
        "solve_time_seconds",
    ]
    print(suite_result.summary[display_columns].to_string(index=False))


if __name__ == "__main__":
    main()
