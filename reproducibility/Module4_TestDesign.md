# Module 4 Task Design

## Solver Performance, Reproducibility, and Validation

### Owner

Liyuan Fan

### Branch Name(未定)

```text
module4-reproducibility-validation-liyuan
```

## 1. Objective

This module checks whether the optimisation pipeline is reproducible, whether solver performance is reasonable, and whether all generated solutions satisfy the model constraints.

The main focus is to verify:

```text
1. repeated runs produce consistent results;
2. solver settings are clearly reported;
3. all validation checks pass;
4. the labour_shortage sequential benchmark discrepancy is explained;
5. the final report and presentation use consistent numerical results.
```

## 2. Motivation

During local reruns, the `labour_shortage` sequential benchmark produced a different labour cost from the value currently written in some report files.

```text
Existing report value: 704.89
Local rerun value: 748.65
```

The other scenarios were stable. This suggests that the issue may be specific to the two-stage sequential benchmark under labour shortage conditions, rather than a global modelling error.

A likely explanation is that the sequential benchmark first optimises wave release decisions and only optimises staffing afterwards. If Stage 1 has multiple optimal release plans, different solver environments may select different release patterns, which can then lead to different staffing costs in Stage 2.

## 3. Planned Technical Work

### 3.1 Repeated-Run Consistency Check

Run the full project pipeline three times for all four scenarios:

```text
base
promotion
tight_due_dates
labour_shortage
```

For each run, record:

```text
run_id
scenario
model
solver_status
labour_cost
weighted_flow_time
balance_deviation
late_orders
temp_worker_hours
overtime_worker_hours
solve_time_seconds
```

Expected output:

```text
results/tables/module4_rerun_consistency.csv
```

### 3.2 Solver Performance Summary

Aggregate repeated-run results by scenario and model.

Record:

```text
mean_solve_time
max_solve_time
min_solve_time
solve_time_std
all_runs_optimal
hardest_scenario
```

Expected output:

```text
results/tables/module4_solver_performance.csv
```

Expected figure:

```text
results/figures/module4_solve_time_comparison.png
```

### 3.3 Validation Audit

Read:

```text
results/tables/validation_summary.csv
```

Summarise whether all validation checks pass.

Checks include:

```text
assignment feasibility
release-window feasibility
wave volume capacity
wave order-count capacity
picking capacity
packing capacity
worker-balance feasibility
tardiness-definition consistency
```

Expected output:

```text
results/tables/module4_validation_audit.csv
```

### 3.4 Labour Shortage Sequential Diagnostic

Compare the `labour_shortage` sequential benchmark outputs across environments.

Key files:

```text
results/tables/labour_shortage_sequential_benchmark_assignments.csv
results/tables/labour_shortage_sequential_benchmark_staffing.csv
```

Main checks:

```text
1. Are release_period assignments identical?
2. Are picking and packing workloads identical by period?
3. Are temporary labour and overtime usage identical?
4. Does the staffing cost difference come from different workload peaks?
```

Expected output:

```text
results/tables/module4_labour_shortage_diagnostic.csv
```

## 4. Proposed Code Changes

Add a new script:

```text
scripts/module4_reproducibility_check.py
```

The script will:

```text
1. run or load the four-scenario experiment outputs;
2. repeat the baseline solve three times;
3. export rerun consistency results;
4. summarise solver performance;
5. audit validation outputs;
6. generate a solve-time figure;
7. optionally compare labour_shortage sequential assignment and staffing profiles.
```

No core optimisation model will be changed unless deterministic tie-breaking is later approved by the team.

## 5. Expected Deliverables

### CSV outputs

```text
results/tables/module4_rerun_consistency.csv
results/tables/module4_solver_performance.csv
results/tables/module4_validation_audit.csv
results/tables/module4_labour_shortage_diagnostic.csv
```

### PNG output

```text
results/figures/module4_solve_time_comparison.png
```

### Memo

```text
docs/module4_reproducibility_validation_memo.md
```

### Report section

```text
report/module4_report_section.md
```

### Slide summary

```text
slides/module4_slide_summary.md
```

## 6. Report-Ready Contribution

The report section will summarise:

```text
1. repeated-run consistency;
2. solver status and solve time;
3. validation results;
4. the labour_shortage sequential benchmark issue;
5. recommendation on deterministic tie-breaking.
```

Draft report wording:

```text
To assess reproducibility and solution reliability, we conducted repeated-run checks across the four baseline scenarios. For each scenario, the integrated model and sequential benchmark were solved three times, and solver status, labour cost, weighted flow time, workload balance, late orders, and solve time were recorded. The validation outputs were also audited against assignment feasibility, release-window consistency, wave capacity, worker capacity, worker-balance feasibility, and tardiness consistency.

The repeated-run check confirmed that the integrated model remained stable and feasible across the tested scenarios. A reproducibility concern was observed in the labour_shortage sequential benchmark, where different environments may produce different downstream staffing costs. This is likely because the sequential benchmark fixes wave release decisions before solving the staffing problem. If multiple Stage-1 release plans have the same objective value, different solver environments may choose different release patterns, which can induce different staffing peaks in Stage 2. This suggests that deterministic tie-breaking should be added to the sequential benchmark if strict cross-machine reproducibility is required.
```

## 7. Slide Summary

Slide title:

```text
Module 4: Reproducibility and Validation
```

Slide bullets:

```text
- Re-ran four baseline scenarios three times
- Recorded solver status, labour cost, flow time, balance, late orders, and solve time
- Audited validation_summary.csv for feasibility violations
- Found a reproducibility risk in the labour_shortage sequential benchmark
- Recommendation: add deterministic tie-breaking to the sequential Stage-1 model
```

Suggested visual:

```text
module4_solve_time_comparison.png
```

## 8. 30–45 Second Video Script

```text
For Module 4, I focused on solver performance, reproducibility, and validation. I reran the four baseline scenarios three times and recorded solver status, labour cost, weighted flow time, workload balance, late orders, and solve time.

I also audited the validation summary to check that assignment, wave capacity, worker capacity, and tardiness constraints were satisfied. The main finding is that most outputs are stable, but the labour_shortage sequential benchmark may be sensitive across solver environments.

This is likely because the sequential benchmark fixes wave releases before staffing. If multiple release plans are equally good in Stage 1, they can still lead to different staffing peaks in Stage 2. Therefore, I recommend adding deterministic tie-breaking if strict cross-machine reproducibility is required.
```

## 9. Timeline

### 7 May

Confirm Module 4 ownership and branch name.

### 8 May 23:59

Confirm that the baseline project can run locally and that Gurobi is correctly configured.

### 10 May 23:59

Submit this task design and list planned outputs.

### 12 May 23:59

Complete first version of:

```text
scripts/module4_reproducibility_check.py
module4_rerun_consistency.csv
module4_solver_performance.csv
module4_solve_time_comparison.png
```

### 15 May 23:59

Submit final:

```text
CSV tables
PNG figure
memo
report section
slide summary
video script
```

### 16 May

Team review and consistency check.

### 17 May

Freeze final code and results for integration.
