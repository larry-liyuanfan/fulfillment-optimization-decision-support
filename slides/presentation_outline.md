# 5-Minute Presentation Outline

## Slide 1. Problem

**Title**
Integrated optimisation of order wave planning and workforce scheduling

**Key points**

- We study one e-commerce fulfilment department over one day.
- Orders arrive dynamically and must be assigned to release waves.
- Picking and packing labour must be scheduled at the same time.
- The practical question is whether joint planning beats sequential planning.

## Slide 2. Data

**Title**
Publicly calibrated and reproducible data

**Key points**

- Public sources: Amazon facilities/process pages, Zalando batching benchmark, BLS wage data, and warehouse literature.
- Order-level data is synthetic but transparent and fixed-seed.
- Scenario scale is department-level, not whole-warehouse level.
- Four scenarios: `base`, `promotion`, `tight_due_dates`, `labour_shortage`.

**Speaker cue**

State clearly that order-level demand is synthetic, while warehouse scale, process context, and labour-cost calibration come from public sources.

## Slide 3. Models

**Title**
Integrated model vs exact two-stage benchmark

**Key points**

- `integrated_exact`: jointly chooses wave releases, regular shifts, temp/overtime, and pick/pack staffing.
- `sequential_benchmark`: first solves wave assignment exactly, then staffs that plan exactly.
- Both models use `gurobipy`.

**Speaker cue**

Emphasise that the benchmark is strong and fair. The advantage of the integrated model comes from better coordination, not from comparing against a weak heuristic.

## Slide 4. Formulation

**Title**
Service-first mixed-integer program

**Key points**

- Decision variables: `x_it`, `y_t`, shift workers, temp/overtime, pick/pack workers.
- Constraints: assignment, wave volume/order limits, labour capacity, tardiness definition, workload balance.
- Objective: heavily penalise tardiness, then minimise weighted flow time, labour cost, and imbalance.

**Speaker cue**

Mention that once the benchmark proves zero tardiness is feasible, the integrated model only searches on-time releases, which speeds up proof of optimality.

## Slide 5. Results

**Title**
Integrated planning reduces labour cost in every scenario

**Key points**

- `base`: `13.55%` labour-cost saving, `18.06%` better balance
- `promotion`: `11.04%` labour-cost saving, almost identical service and balance
- `tight_due_dates`: `2.58%` labour-cost saving, still zero lateness
- `labour_shortage`: `12.93%` labour-cost saving, `15.62%` better balance
- All integrated models solved to `OPTIMAL`

## Slide 6. Insight

**Title**
What the integrated model is doing

**Key points**

- It protects service first: all scenarios keep `0` late orders.
- It accepts a small flow-time increase when that avoids expensive staffing peaks.
- It is especially valuable in promotion periods and labour shortages.
- Tight due dates reduce room for smoothing, so gains are smaller there.

## Slide 7. Recommendation

**Title**
Recommendation to the stakeholder

**Key points**

- Use the integrated model as the default daily planning tool.
- Keep the sequential model as a benchmark or fallback.
- Priority extension for future work: multi-day staffing or zone-level routing.
