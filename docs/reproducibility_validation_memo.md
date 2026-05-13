# Module 4 Memo  
## Solver Performance, Reproducibility, and Validation

**Owner:** Liyuan Fan  
**Module:** Module 4 — Solver Performance, Reproducibility, and Validation  
**Purpose:** Check whether the optimisation pipeline is reproducible, whether solver outputs are trustworthy, whether all validation checks pass, and whether solve times are reasonable.

---

## 1. Executive Summary

This module evaluates the reproducibility and reliability of the optimisation pipeline across different local environments. The project is internally stable within each tested environment, but the `labour_shortage` sequential benchmark shows a cross-environment difference.

The macOS vendored-Gurobi run reproduces the report baseline value:

```text
labour_shortage sequential benchmark cost = 704.89
```

In contrast, both Windows venv and Windows Anaconda runs using the officially installed Gurobi package consistently return:

```text
labour_shortage sequential benchmark cost = 748.65
```

A Stage-1 objective diagnostic confirms that the Mac/vendor and Windows/official release assignments have exactly the same sequential Stage-1 objective value:

```text
Mac/vendor Stage-1 objective = 534.8
Windows/official Stage-1 objective = 534.8
Difference = 0.0
```

Therefore, the Windows result is not caused by a worse Stage-1 release-planning objective. Instead, the two environments selected different but Stage-1-equivalent release plans.

The downstream difference is fully explained by staffing usage. The Windows result uses two additional temporary-worker hours compared with the Mac/vendor result. Since temporary labour costs `21.88` per hour, the cost gap is:

```text
2 × 21.88 = 43.76
```

This exactly matches:

```text
748.65 - 704.89 = 43.76
```

Therefore, the discrepancy confirms cross-environment tie-breaking sensitivity in the two-stage sequential benchmark, rather than a general modelling failure.

---

## 2. Environments Tested

| Environment | Gurobi Source | Vendor Status | Key Result |
|:---|:---|:---|:---|
| Windows venv | Official installed Gurobi | Failed with missing `gurobipy._batch` | `labour_shortage` sequential cost = `748.65` |
| Windows Anaconda | Official installed Gurobi | Failed with missing `gurobipy._batch` | `labour_shortage` sequential cost = `748.65` |
| macOS venv | Vendored Gurobi | Worked after macOS security handling | `labour_shortage` sequential cost = `704.89` |

On Windows, the virtual environment was activated using:

```text
.venv\Scripts\activate.bat
```

instead of the Unix-style command:

```text
source .venv/bin/activate
```

This was an operating-system adjustment, not a model change.

The original requirements file specified `numpy==2.3.5`, which was not available in the Windows Python 3.10 environment. Therefore, `numpy==1.26.4` was used as a dependency compatibility workaround. No optimisation model, scenario configuration, or data-generation source code was changed.

---

## 3. Solver Settings Check

The solver implementation was checked for reproducibility-related settings.

| Setting | Observed Value / Status | Interpretation |
|:---|:---|:---|
| `TimeLimit` | `time_limit`, default `60` | Applied in integrated, staffing, and sequential stages |
| `MIPGap` | `0.0` | Exact optimality target in the tested models |
| `Threads` | `1` | Single-thread solving for reproducibility |
| `MIPFocus` | `2` integrated, `1` sequential | Solver search emphasis differs by model stage |
| `Heuristics` | `0.05` integrated | Integrated model uses limited heuristic support |
| Explicit `Seed` | Not found in solver settings | Instance generation is deterministic, but solver tie-breaking can still vary |

The absence of an explicit Gurobi solver seed does not affect deterministic data generation. However, solver-level tie-breaking can still differ across solver builds or platforms when multiple equivalent optimal solutions exist.

---

## 4. Three-Run Consistency Check

The Windows Anaconda environment with official Gurobi was run three times. The main KPIs were identical across all three runs.

| Scenario | Model | Run 1 Labour Cost | Run 2 Labour Cost | Run 3 Labour Cost | Stable? |
|:---|:---|---:|---:|---:|:---|
| base | integrated_exact | 609.40 | 609.40 | 609.40 | Yes |
| base | sequential_benchmark | 704.92 | 704.92 | 704.92 | Yes |
| promotion | integrated_exact | 704.92 | 704.92 | 704.92 | Yes |
| promotion | sequential_benchmark | 792.44 | 792.44 | 792.44 | Yes |
| tight_due_dates | integrated_exact | 661.16 | 661.16 | 661.16 | Yes |
| tight_due_dates | sequential_benchmark | 678.64 | 678.64 | 678.64 | Yes |
| labour_shortage | integrated_exact | 613.77 | 613.77 | 613.77 | Yes |
| labour_shortage | sequential_benchmark | 748.65 | 748.65 | 748.65 | Yes |

All three Windows official-Gurobi runs also preserved zero late orders in every scenario. This means the Windows result is internally reproducible, even though it differs from the Mac/vendor baseline in one benchmark case.

---

## 5. Solver Performance Summary

| Scenario | Hardest Model | Mean Integrated Solve Time (s) | Mean Sequential Solve Time (s) | Interpretation |
|:---|:---|---:|---:|:---|
| base | integrated_exact | 1.781 | 0.014 | Integrated is slower because it jointly optimises release and staffing |
| promotion | integrated_exact | 7.211 | 0.012 | Hardest local case due to higher order volume and denser workload |
| tight_due_dates | integrated_exact | 0.407 | 0.011 | Fastest integrated case in the repeated-run test |
| labour_shortage | integrated_exact | 3.494 | 0.012 | Resource constraints increase difficulty, but solve time remains modest |

The integrated model consistently requires more solve time than the sequential benchmark because it optimises release and staffing decisions jointly. The sequential benchmark solves very quickly because its two subproblems are smaller.

A log-scale solve-time figure is used because the sequential benchmark solves in around `0.01` seconds, while the integrated model takes up to several seconds. Under a normal linear scale, the sequential benchmark bars are visually compressed near the x-axis.

The promotion scenario is the hardest local case, with a mean integrated solve time of approximately `7.211` seconds. Overall, the solve times are reasonable for this project scale.

---

## 6. Validation Audit

The validation framework checks assignment feasibility, release-window consistency, wave capacity, worker capacity, worker-balance feasibility, and tardiness consistency.

| Environment / Source | Validation Checks | Max Violation | All Passed? | Interpretation |
|:---|---:|---:|:---|:---|
| Mac/vendor | 72 | 0 | Yes | Baseline report result is feasible |
| Windows/official | 72 | 0 | Yes | Local Windows result is also feasible |

The validation audit shows that the Mac/vendor and Windows/official outputs both satisfy the model constraints. Therefore, the `704.89` versus `748.65` discrepancy is not caused by infeasibility or constraint violation.

---

## 7. Mac/vendor vs Windows/official KPI Difference

The discrepancy is localised to the `labour_shortage` sequential benchmark.

| Scenario | Model | Mac/vendor Labour Cost | Windows/official Labour Cost | Difference |
|:---|:---|---:|---:|---:|
| base | sequential_benchmark | 704.92 | 704.92 | 0.00 |
| promotion | sequential_benchmark | 792.44 | 792.44 | 0.00 |
| tight_due_dates | sequential_benchmark | 678.64 | 678.64 | 0.00 |
| labour_shortage | sequential_benchmark | 704.89 | 748.65 | 43.76 |

The difference is explained by temporary labour usage.

| Metric | Mac/vendor | Windows/official | Difference |
|:---|---:|---:|---:|
| Regular worker hours | 30 | 30 | 0 |
| Temporary worker hours | 3 | 5 | 2 |
| Overtime worker hours | 1 | 1 | 0 |
| Active waves | 11 | 11 | 0 |
| Labour cost | 704.89 | 748.65 | 43.76 |

The difference is exactly:

```text
2 extra temporary-worker hours × 21.88 = 43.76
```

This confirms that the discrepancy is a staffing-profile difference rather than a lateness or feasibility problem.

---

## 8. Assignment and Staffing Diagnostics

The release-period count is identical between the Mac/vendor and Windows/official outputs. However, 9 of the 120 orders receive different release periods.

| Order | Mac Release | Windows Release | Difference |
|:---|---:|---:|---:|
| O032 | 3 | 2 | -1 |
| O079 | 4 | 3 | -1 |
| O007 | 5 | 4 | -1 |
| O058 | 5 | 4 | -1 |
| O047 | 6 | 5 | -1 |
| O001 | 2 | 3 | 1 |
| O006 | 4 | 5 | 1 |
| O051 | 5 | 6 | 1 |
| O010 | 3 | 5 | 2 |

These assignment differences reshape the downstream workload profile. In the Windows/official result, additional temporary labour is required in `P4` and `P11`. In the Mac/vendor result, temporary labour is only used in `P7`, `P8`, and `P9`.

This supports the interpretation that the discrepancy comes from different release-plan choices in the sequential benchmark, not from a global model or data failure.

---

## 9. Confirmed Stage-1 Tie-Breaking Diagnosis

The Stage-1 objective diagnostic confirms that the Mac/vendor and Windows/official release assignments are Stage-1 equivalent. Both assignments have zero weighted tardiness, the same weighted flow time of `223.4`, the same number of active waves, and the same Stage-1 objective value of `534.8`.

| Source | Weighted Tardiness | Weighted Flow Time | Active Waves | Wave Opening Cost | Stage-1 Objective |
|:---|---:|---:|---:|---:|---:|
| Mac/vendor | 0.0 | 223.4 | 11 | 88.0 | 534.8 |
| Windows/official | 0.0 | 223.4 | 11 | 88.0 | 534.8 |
| Difference | 0.0 | 0.0 | 0 | 0.0 | 0.0 |

This means the two environments selected different but Stage-1-equivalent release plans. The Windows result is not worse in the sequential release-planning objective. Instead, the difference comes from deterministic tie-breaking sensitivity: different solver environments select different equivalent release assignments.

Because the sequential benchmark fixes release decisions before staffing is optimised, these equivalent Stage-1 release plans can still generate different downstream staffing profiles. In this case, the Windows/official release plan requires two additional temporary-worker hours in Stage 2, increasing labour cost by exactly `43.76`.

Therefore, deterministic tie-breaking should be added to the sequential Stage-1 release model if strict cross-machine reproducibility is required.

---

## 10. Recommendation

For strict cross-machine reproducibility, the sequential benchmark should include deterministic tie-breaking.

| Option | Recommendation |
|:---|:---|
| 1 | Add a small secondary term that favours smoother workload profiles |
| 2 | Add deterministic ordering rules for equivalent release assignments |
| 3 | Export and compare assignment files whenever benchmark cost changes |
| 4 | Report the `labour_shortage` sequential benchmark as environment-sensitive |

This recommendation does not invalidate the main result. Instead, it strengthens the argument for integrated optimisation because integrated planning directly internalises staffing consequences during release planning.

---

## 11. Final Answers to Module 4 Questions

| Question | Answer |
|:---|:---|
| Is the code reproducible? | Yes within each tested environment. Mac/vendor reproduces the report baseline; Windows/official is internally stable but gives a different `labour_shortage` sequential benchmark result. |
| Are the results trustworthy? | Yes. All models solve to `OPTIMAL`, and validation checks pass. The observed discrepancy is localised and explainable. |
| Are all model constraints satisfied? | Yes. The validation audit reports zero violations for both Mac/vendor and Windows/official outputs. |
| Is solve time reasonable? | Yes. Integrated models take longer than sequential benchmarks, but all baseline solves remain within seconds. The hardest local case is `promotion` integrated with mean solve time around `7.211` seconds. |
| Is deterministic tie-breaking needed? | Yes. The Stage-1 diagnostic confirms that Mac/vendor and Windows/official selected different but Stage-1-equivalent release plans. Strict cross-machine reproducibility of the sequential benchmark therefore requires deterministic tie-breaking. |

---

## 12. Conclusion

The Module 4 checks show that the optimisation pipeline is feasible, validated, and internally stable within each tested environment. The Mac/vendor run reproduces the report baseline value of `704.89` for the `labour_shortage` sequential benchmark, while Windows official-Gurobi runs consistently return `748.65`.

The Stage-1 objective diagnostic confirms that both environments selected release plans with the same Stage-1 objective value of `534.8`. The downstream cost difference is completely explained by two additional temporary-worker hours in the Windows result. Since both outputs pass validation and preserve zero lateness, the discrepancy confirms cross-environment tie-breaking sensitivity in the two-stage sequential benchmark rather than a general modelling failure.

The practical recommendation is to add deterministic tie-breaking to the sequential Stage-1 release model, or explicitly report this benchmark sensitivity in the final submission.
