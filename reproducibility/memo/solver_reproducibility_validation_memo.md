# Solver Reproducibility and Validation Memo

## Purpose

This memo documents whether the optimization pipeline is reproducible, whether solver outputs are trustworthy, whether validation checks pass, and whether solve times are reasonable.

## Executive Summary

The pipeline is internally stable within each tested environment. The only observed cross-environment difference appears in the `labour_shortage` sequential benchmark. The integrated model remains feasible and stable, and both compared outputs pass all validation checks.

The baseline run returns:

```text
labour_shortage sequential benchmark cost = 704.89
```

The Windows official-Gurobi run returns:

```text
labour_shortage sequential benchmark cost = 748.65
```

A Stage-1 objective diagnostic confirms that the two release assignments have the same sequential Stage-1 objective:

```text
Stage-1 objective = 534.8
Difference = 0.0
```

The downstream difference is fully explained by staffing usage. The Windows result uses two additional temporary-worker hours. Since temporary labour costs `21.88` per hour, the cost gap is:

```text
2 * 21.88 = 43.76
748.65 - 704.89 = 43.76
```

This confirms tie-breaking sensitivity in the two-stage sequential benchmark rather than a modelling failure.

## Environments Compared

| Environment | Gurobi Source | Key Result |
|---|---|---|
| Reference run | Vendored Gurobi package | `labour_shortage` sequential cost = `704.89` |
| Windows run | Official installed Gurobi | `labour_shortage` sequential cost = `748.65` |

No optimization model, scenario configuration, or data-generation source code was changed between the compared outputs.

## Solver Settings

| Setting | Observed Value / Status | Interpretation |
|---|---:|---|
| `TimeLimit` | 60 seconds by default | Applied across model stages |
| `MIPGap` | 0.0 | Exact optimality target |
| `Threads` | 1 | Single-thread solving for reproducibility |
| `MIPFocus` | 2 integrated, 1 sequential | Solver search emphasis differs by model stage |
| Explicit solver seed | Not configured | Equivalent optima may still be selected differently across solver builds |

The data-generation layer is deterministic. The remaining sensitivity comes from solver tie-breaking when multiple equivalent release plans exist.

## Three-Run Consistency

The repeated local runs were stable: all KPI values matched across three executions in the Windows official-Gurobi environment.

| Scenario | Integrated Stable? | Sequential Stable? | Zero Late Orders? |
|---|---|---|---|
| base | Yes | Yes | Yes |
| promotion | Yes | Yes | Yes |
| tight_due_dates | Yes | Yes | Yes |
| labour_shortage | Yes | Yes | Yes |

## Validation Audit

The validation framework checks assignment feasibility, release-window consistency, wave capacity, worker capacity, worker-balance feasibility, and tardiness consistency.

| Source | Validation Checks | Max Violation | All Passed? |
|---|---:|---:|---|
| Reference run | 72 | 0 | Yes |
| Windows run | 72 | 0 | Yes |

The `704.89` versus `748.65` difference should not be interpreted as infeasibility or a constraint violation.

## Cross-Environment KPI Difference

The discrepancy is localized to the `labour_shortage` sequential benchmark.

| Scenario | Model | Reference Cost | Windows Cost | Difference |
|---|---|---:|---:|---:|
| base | sequential_benchmark | 704.92 | 704.92 | 0.00 |
| promotion | sequential_benchmark | 792.44 | 792.44 | 0.00 |
| tight_due_dates | sequential_benchmark | 678.64 | 678.64 | 0.00 |
| labour_shortage | sequential_benchmark | 704.89 | 748.65 | 43.76 |

The difference is explained by temporary labour usage.

| Metric | Reference | Windows | Difference |
|---|---:|---:|---:|
| Regular worker hours | 30 | 30 | 0 |
| Temporary worker hours | 3 | 5 | 2 |
| Overtime worker hours | 1 | 1 | 0 |
| Active waves | 11 | 11 | 0 |
| Labour cost | 704.89 | 748.65 | 43.76 |

## Tie-Breaking Diagnosis

The two release assignments have zero weighted tardiness, the same weighted flow time of `223.4`, the same number of active waves, and the same Stage-1 objective value of `534.8`. Because the sequential benchmark fixes release decisions before staffing is optimized, Stage-1-equivalent release plans can still create different downstream staffing profiles.

## Recommendation

For strict cross-machine reproducibility, the sequential benchmark should include deterministic tie-breaking:

| Option | Recommendation |
|---|---|
| 1 | Add a small secondary term that favours smoother workload profiles |
| 2 | Add deterministic ordering rules for equivalent release assignments |
| 3 | Export and compare assignment files whenever benchmark cost changes |
| 4 | Report the sequential benchmark as environment-sensitive when equivalent optima exist |

This does not invalidate the main result. It strengthens the case for integrated optimization because the integrated model internalizes staffing consequences during release planning.
