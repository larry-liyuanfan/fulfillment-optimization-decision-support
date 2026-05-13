# Integrated Fulfillment Optimization Decision Support

A personal decision-optimization project for e-commerce fulfillment planning. The project studies whether order wave release and workforce scheduling should be optimized jointly instead of sequentially, then validates the result across baseline generation, scenario analysis, sensitivity checks, and reproducibility auditing.

The repository is packaged as a public portfolio version: all data are synthetic or publicly calibrated, and the code is organized so the full experiment pipeline can be regenerated from the project root.

## Live Demo

- Static project page: [`docs/index.html`](docs/index.html)
- Main result charts: [`results/figures`](results/figures)
- Reproducibility audit: [`reproducibility`](reproducibility)

## Problem

An e-commerce fulfillment department receives orders throughout a 12-period operating day. Orders must be assigned to release waves, then picking and packing capacity must be staffed with regular, temporary, and overtime labor. A common operational shortcut is to first decide wave releases and then staff the workload profile. This project tests an integrated alternative that makes release and staffing decisions in one mixed-integer optimization model.

## Project Scope

| Stage | Focus | Output |
|---|---|---|
| Baseline | Synthetic fulfillment instance generation with calibrated order, period, and shift tables | Reproducible scenario inputs |
| Integrated planning | MIP formulation for order-wave release and workforce allocation | `integrated_exact` model |
| Sequential benchmark | Two-stage exact release-then-staffing benchmark | `sequential_benchmark` model |
| Experiment analysis | Scenario, sensitivity, service robustness, and replication experiments | KPI tables and figures |
| Reproducibility audit | Cross-environment solver diagnostics and validation checks | Validation memo, raw outputs, diagnostic CSVs |

## Method

- **Optimization model:** mixed-integer programming with Gurobi.
- **Decision variables:** order-to-wave assignment, wave activation, regular shift activation, temporary labor, overtime labor, and pick/pack worker allocation.
- **Benchmark:** two-stage exact model that optimizes release first and staffing second.
- **Scenarios:** base, promotion, tight due dates, and labor shortage.
- **Validation:** assignment feasibility, release feasibility, wave capacity, pick/pack capacity, worker balance, and tardiness consistency checks.
- **Reproducibility:** deterministic seeds, exported scenario instances, generated reporting bundle, and a cross-platform solver audit.

## Key Results

| Scenario | Integrated Cost | Sequential Cost | Cost Saving | Saving % | Late Orders |
|---|---:|---:|---:|---:|---:|
| base | 609.40 | 704.92 | 95.52 | 13.55% | 0 |
| promotion | 704.92 | 792.44 | 87.52 | 11.04% | 0 |
| tight_due_dates | 661.16 | 678.64 | 17.48 | 2.58% | 0 |
| labour_shortage | 613.77 | 704.89 | 91.12 | 12.93% | 0 |

Across 40 replicated feasible instances, the integrated model is cheaper in 39 cases and keeps zero late orders in all 40 cases.

| Scenario | Replications | Mean Saving % | Integrated Cheaper Share | Zero-Late Share |
|---|---:|---:|---:|---:|
| base | 10 | 11.45% | 100% | 100% |
| promotion | 10 | 12.56% | 100% | 100% |
| tight_due_dates | 10 | 5.21% | 90% | 100% |
| labour_shortage | 10 | 10.67% | 100% | 100% |

## Repository Map

```text
src/fulfillment_optim/     Core data generation, models, experiments, analysis, validation
results/instances/         Exported scenario inputs
results/tables/            KPI, validation, replication, and sensitivity tables
results/figures/           Generated visual outputs
reproducibility/           Cross-environment solver audit package
report/                    Markdown report and result analysis
tests/                     Pipeline-level unit tests
docs/                      Static frontend page for portfolio display
```

## Run Locally

This project requires Python and a working Gurobi installation/license.

```bash
pip install -r requirements.txt
python run_project.py
python -m unittest discover -s tests
```

`python run_project.py` regenerates the experiment outputs, analysis tables, figures, and reporting bundle under `results/`.

## Portfolio Notes

This project is positioned for data science, business algorithm, and operations-research roles. It demonstrates:

- translating a fulfillment planning problem into an optimization model;
- comparing an integrated algorithmic decision process against a strong benchmark;
- designing reproducible experiments and validation checks;
- packaging analytical work into readable tables, figures, and a lightweight frontend page.
