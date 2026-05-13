# Optimization Solver Reproducibility

This repository is a sanitized personal portfolio version of an optimisation validation project.

The project investigates why a two-stage sequential optimisation benchmark can produce different downstream labour costs across solver environments, even when repeated runs are internally stable and validation checks pass.

It is positioned as a practical optimisation engineering project for business algorithm, operations research, and data science internship applications.

## Problem

The optimisation pipeline compares multiple fulfilment planning scenarios and model variants.

During cross-environment validation, one scenario showed a discrepancy:

| Benchmark | macOS vendored Gurobi | Windows official Gurobi | Difference |
|---|---:|---:|---:|
| labour shortage sequential benchmark cost | 704.89 | 748.65 | 43.76 |

Other scenarios and integrated model outputs were stable. The goal was to determine whether this was a modelling error, validation failure, solver instability, or deterministic tie-breaking issue.

## Method

The analysis workflow includes:

1. Run repeated consistency checks across scenarios and model variants.
2. Summarise solve-time stability across repeated runs.
3. Audit validation outputs for constraint violations.
4. Compare macOS vendored-Gurobi and Windows official-Gurobi outputs.
5. Diagnose the labour-shortage sequential benchmark discrepancy.
6. Trace the downstream cost gap to staffing decisions and equivalent Stage-1 release plans.

## Key Results

| Check | Result |
|---|---|
| Windows repeated runs | Stable across three runs |
| Validation audit | 72 / 72 checks passed in both environments |
| Stage-1 objective | Same value in both environments: 534.8 |
| Cost difference | 43.76 |
| Source of difference | 2 extra temporary-worker hours |
| Interpretation | Cross-environment tie-breaking sensitivity in a two-stage sequential benchmark |

The cost difference is exactly explained by:

```text
2 temporary-worker hours * 21.88 = 43.76
```

This suggests the environments selected different Stage-1-equivalent release plans, which then led to different Stage-2 staffing costs.

## Portfolio Takeaways

- Built a reproducibility audit for optimisation outputs across solver environments.
- Designed validation summaries for constraint checks and repeated-run stability.
- Diagnosed a cross-environment discrepancy without changing the core optimisation model.
- Produced clean CSV tables, figures, memo text, and report-ready findings.
- Recommended deterministic tie-breaking for strict cross-machine reproducibility.

## Repository Structure

```text
.
├── csv/       # Cleaned validation and comparison tables
├── figures/   # Portfolio-safe visual summaries
├── scripts/   # Output generation and post-processing script
├── docs/      # Memo, report section, and slide summary
└── README.md
```

## Selected Outputs

### Solve-time comparison

![Solve time comparison](figures/module4_solve_time_comparison.png)

### Labour-shortage cost comparison

![Labour shortage cost comparison](figures/module4_labour_shortage_cost_comparison.png)

## How to Reproduce the Clean Outputs

The script is included for transparency:

```bash
python scripts/generate_module4_outputs.py
```

The original raw outputs are not included in this public repository. The checked-in `csv/` and `figures/` folders contain the sanitized outputs used for the portfolio summary.

## Tech Stack

Python, Pandas, Matplotlib, Gurobi-style optimisation output analysis, validation auditing, reproducibility diagnostics.

## Confidentiality Note

This is a sanitized personal project repository. It does not include team meeting files, virtual environments, original raw solver outputs, private course materials, or teammate-owned code.
