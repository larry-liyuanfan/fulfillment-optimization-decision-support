# Module 4 Video Script  
## 30–45 Seconds

For Module 4, I checked solver performance, reproducibility, and validation across different local environments.

The key finding is that the macOS run using the vendored Gurobi package reproduces the report baseline, where the `labour_shortage` sequential benchmark has a cost of `704.89`. However, both Windows venv and Windows Anaconda runs using the official Gurobi package consistently return `748.65` for the same benchmark.

I then recomputed the sequential Stage-1 objective for both release assignments. Both have the same Stage-1 objective value of `534.8`, with zero tardiness, the same weighted flow time, and the same number of active waves. This confirms that the two environments selected different but Stage-1-equivalent release plans.

The downstream difference appears in staffing: the Windows result uses two additional temporary-worker hours, adding exactly `43.76` cost units. Since validation checks pass and the integrated model remains stable, I interpret this as cross-environment tie-breaking sensitivity in the two-stage sequential benchmark, not a general model failure. A practical recommendation is to add deterministic tie-breaking to the sequential release model.
