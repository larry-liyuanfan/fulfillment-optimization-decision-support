# Results Analysis

## Executive Summary

- The integrated model is optimal in all four scenarios and keeps `0` late orders in every case.
- The largest absolute labour-cost saving occurs in `base` at `95.52` cost units.
- The largest percentage labour-cost saving occurs in `base` at `13.55%`.
- The tightest service environment is `tight_due_dates` with average SLA width `2.096` periods.
- Validation passed on `72/72` recorded checks.

## Interpretation

The integrated model is service-feasible first and cost-efficient second. Because tardiness is heavily penalised, every integrated solution stays on time whenever an on-time plan exists. Within that feasible region, the model trades off weighted flow time, labour cost, and workload imbalance.

A small increase in weighted flow time is therefore not a modelling error. It reflects a controlled managerial choice: if all orders are still on time, the model may delay some releases slightly to avoid expensive staffing peaks.

## Scenario Analysis

### base

- Orders: `120`
- Integrated cost: `609.40` vs sequential `704.92`
- Cost saving: `95.52` (`13.55%`)
- Weighted flow-time change: `+9.13%`
- Balance change: `-18.06%`, so the integrated plan improves
- Temporary-labour change: `+4.0` hours from the sequential benchmark perspective
- On-time service rate: `100.0%`

### promotion

- Orders: `145`
- Integrated cost: `704.92` vs sequential `792.44`
- Cost saving: `87.52` (`11.04%`)
- Weighted flow-time change: `+1.71%`
- Balance change: `-0.36%`, so the integrated plan improves
- Temporary-labour change: `+4.0` hours from the sequential benchmark perspective
- On-time service rate: `100.0%`

### tight_due_dates

- Orders: `125`
- Integrated cost: `661.16` vs sequential `678.64`
- Cost saving: `17.48` (`2.58%`)
- Weighted flow-time change: `+1.61%`
- Balance change: `+1.21%`, so the integrated plan slightly worsens
- Temporary-labour change: `-4.0` hours from the sequential benchmark perspective
- On-time service rate: `100.0%`

### labour_shortage

- Orders: `120`
- Integrated cost: `613.77` vs sequential `704.89`
- Cost saving: `91.12` (`12.93%`)
- Weighted flow-time change: `+6.54%`
- Balance change: `-15.62%`, so the integrated plan improves
- Temporary-labour change: `-1.0` hours from the sequential benchmark perspective
- On-time service rate: `100.0%`

## Credibility Checks

- The order scale is explicitly defined at the department level rather than the entire warehouse level.
- Item counts are calibrated around a literature-backed average of about two items per order.
- Wage rates are tied to public BLS data rather than arbitrary constants.
- The validation layer confirms assignment feasibility, capacity feasibility, worker-balance feasibility, and tardiness consistency.
