# Basic regression tests for deterministic generation and model feasibility
from __future__ import annotations
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig-test"))
(ROOT / ".mplconfig-test").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from fulfillment_optim.data_generation import generate_instance
from fulfillment_optim.models import ObjectiveWeights, solve_integrated_model, solve_sequential_benchmark
from fulfillment_optim.validation import validate_result

class PipelineTests(unittest.TestCase):
    # Smoke tests for the core data and optimisation pipeline
    def test_seed_override_is_deterministic(self) -> None:
        # A fixed override seed should reproduce the same instance exactly
        instance_a = generate_instance("base", seed=123456)
        instance_b = generate_instance("base", seed=123456)
        self.assertEqual(instance_a.metadata["seed"], 123456)
        self.assertEqual(instance_b.metadata["seed"], 123456)
        self.assertTrue(instance_a.orders.equals(instance_b.orders))
        self.assertTrue(instance_a.periods.equals(instance_b.periods))
        self.assertTrue(instance_a.shifts.equals(instance_b.shifts))
    def test_base_models_are_feasible_and_on_time(self) -> None:
        # The base scenario should solve exactly and pass validation check
        instance = generate_instance("base")
        weights = ObjectiveWeights()
        sequential = solve_sequential_benchmark(instance, objective_weights=weights)
        integrated = solve_integrated_model(instance, warm_start_result=sequential, objective_weights=weights)
        self.assertEqual(sequential.status, "OPTIMAL")
        self.assertEqual(integrated.status, "OPTIMAL")
        self.assertEqual(sequential.late_orders, 0)
        self.assertEqual(integrated.late_orders, 0)
        for result in (sequential, integrated):
            validation_rows = validate_result(instance, result)
            self.assertTrue(all(bool(row["passed"]) for row in validation_rows))
        self.assertLessEqual(integrated.labour_cost, sequential.labour_cost)


if __name__ == "__main__":
    unittest.main()
