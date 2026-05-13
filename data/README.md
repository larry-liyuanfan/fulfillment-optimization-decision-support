# Data Notes
## 1. What Is Public and What Is Synthetic
This study uses a hybrid data strategy.

- `Public calibration`: warehouse scale, warehouse process context, batching context, and labour cost calibration come from public sources.
- `Synthetic micro-data`: order-level arrivals, due times, item counts, volumes, and workloads are generated from transparent rules with fixed random seeds.

Public sources do not disclose order-level transaction logs for fulfilment centres, so the analysis combines public calibration with transparent synthetic order data. This keeps the macro assumptions observable and the micro-level assumptions explicit.

## 2. Public Sources Used
The main sources are:
1. Amazon facilities overview  
   [https://www.aboutamazon.com/workplace/facilities](https://www.aboutamazon.com/workplace/facilities)

2. Amazon package-flow overview  
   [https://www.aboutamazon.com/news/operations/how-do-amazon-packages-get-delivered](https://www.aboutamazon.com/news/operations/how-do-amazon-packages-get-delivered)

3. Zalando batching benchmark repository  
   [https://github.com/zalandoresearch/batching-benchmarks](https://github.com/zalandoresearch/batching-benchmarks)

4. Li, Zhang, and Jiang (2022), *Order-Picking Efficiency in E-Commerce Warehouses: A Literature Review*  
   [https://www.mdpi.com/0718-1876/17/4/91](https://www.mdpi.com/0718-1876/17/4/91)

5. U.S. Bureau of Labor Statistics, `Stockers and Order Fillers`, May 2023  
   [https://www.bls.gov/oes/2023/May/oes537065.htm](https://www.bls.gov/oes/2023/May/oes537065.htm)

## 3. Scientific Calibration Logic
### 3.1 Warehouse Scale
Amazon publicly describes sortable fulfilment centres as facilities of around `800,000` square feet with more than `1,500` full-time associates. That scale is far larger than the single-day tactical model studied here.

So this project models:
- one picking-and-packing department
- one day of operations
- one tactical planning layer inside a much larger fulfilment centre

That is why `120` to `145` orders per day is reasonable here: the instance is not a whole national fulfilment centre, but a single operational planning cell within it.

### 3.2 Order Structure
Li, Zhang, and Jiang (2022) summarise e-commerce orders as small and cite evidence of about `2` items per order in a large distribution centre. We calibrate our item-count distribution around that fact.

The resulting scenario averages are in [results/tables/instance_profiles.csv](/Users/iris/Desktop/MAST90014/Group%20Project/results/tables/instance_profiles.csv):
- `base`: `2.142` items per order
- `promotion`: `2.145`
- `tight_due_dates`: `2.112`
- `labour_shortage`: `2.117`

These averages are tightly clustered around the literature-based calibration target.

### 3.3 Labour Cost
Regular labour cost uses the BLS May 2023 hourly wage reference for stockers and order fillers:
- regular labour: `17.50` per hour
- temporary labour: `21.88` per hour, modelled as a `25%` premium
- overtime labour: `26.25` per hour, modelled as a `50%` premium

This makes the wage structure transparent and auditable rather than arbitrary.

### 3.4 Batching Context
The Zalando batching benchmark is used as a public reference that this family of warehouse-order batching problems is operationally meaningful at scale. We do not copy a proprietary instance from that repository. Instead, we use it as evidence that joint order selection, allocation, batching, and picking is a recognised optimisation setting.

## 4. Synthetic Generation Rules
The generator is implemented in [src/fulfillment_optim/data_generation.py](/Users/iris/Desktop/MAST90014/Group%20Project/src/fulfillment_optim/data_generation.py).

The main assumptions are:
- `12` hourly periods per day, with `11` release opportunities
- `12` storage zones
- three service classes: `economy`, `standard`, `priority`
- item-count distribution `[0.42, 0.30, 0.15, 0.08, 0.03, 0.02]` over `1` to `6` items
- order volumes sampled from a lognormal distribution with a lower floor
- zones touched increase with item count
- due periods sampled from scenario-specific service windows

Workload minutes are generated from interpretable formulas:
- picking time increases with item count, zones touched, and total volume
- packing time also increases with those drivers, but more slowly than picking

This keeps the generated orders heterogeneous without introducing unstable randomness or hidden hand-tuning.

## 5. Scenario Sizes
The final scenarios are:
| Scenario | Orders | Avg items/order | Avg SLA width (periods) | Total workload (minutes) |
|---|---:|---:|---:|---:|
| base | 120 | 2.142 | 3.750 | 1197.07 |
| promotion | 145 | 2.145 | 2.966 | 1456.86 |
| tight_due_dates | 125 | 2.112 | 2.096 | 1230.72 |
| labour_shortage | 120 | 2.117 | 3.633 | 1182.61 |

These scales are large enough to create meaningful trade-offs, but still small enough for exact optimisation and full reproducibility.

## 6. Why The Instances Are Stable
Each scenario has a fixed seed in [src/fulfillment_optim/config.py](/Users/iris/Desktop/MAST90014/Group%20Project/src/fulfillment_optim/config.py).

That means:
- the same scenario always regenerates the same orders
- the same notebook always reproduces the same KPIs
- any change in outputs must come from a model change, not from random drift

This stability supports reproducibility, debugging, and sensitivity analysis.

## 7. How We Check That The Instances And Solutions Are Sound
The project includes an explicit validation layer in [src/fulfillment_optim/validation.py](/Users/iris/Desktop/MAST90014/Group%20Project/src/fulfillment_optim/validation.py).

After each solve, we check:
- every order is assigned exactly once
- no order is released before it arrives
- no order is released beyond the allowed candidate window
- no wave exceeds its volume limit
- no wave exceeds its order-count limit
- picking and packing loads respect worker capacities
- direct workers never exceed total available workers
- reported tardiness matches completion minus due time

The final validation output is [results/tables/validation_summary.csv](/Users/iris/Desktop/MAST90014/Group%20Project/results/tables/validation_summary.csv), and all final checks are zero-violation.
