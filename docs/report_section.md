# Module 4 Report Section  
## Solver Performance, Reproducibility, and Validation

To assess solver reproducibility and validation reliability, we reran the baseline experiment suite across multiple local environments. The macOS run using the vendored Gurobi package reproduced the report baseline, including the `labour_shortage` sequential benchmark cost of `704.89`. In contrast, both Windows venv and Windows Anaconda runs using the officially installed academic Gurobi package consistently produced a `labour_shortage` sequential benchmark cost of `748.65`.

The discrepancy is localised rather than global. All integrated-model results remained stable, and the other sequential benchmark scenarios matched the report baseline. The difference in `labour_shortage` is fully explained by staffing usage: the Windows official-Gurobi solution uses `5` temporary-worker hours rather than `3`, while regular hours, overtime hours, and active waves remain unchanged. Since temporary labour costs `21.88` per hour, the two additional temporary hours account exactly for the `43.76` cost difference.

A Stage-1 objective diagnostic confirms this interpretation. The Mac/vendor and Windows/official release assignments both have zero weighted tardiness, the same weighted flow time of `223.4`, the same number of active waves, and the same sequential Stage-1 objective value of `534.8`. Therefore, the Windows result is not caused by a worse Stage-1 release-planning objective. Instead, the two environments selected different but Stage-1-equivalent release plans, which then produced different downstream staffing profiles.

The solver settings check shows that the exact models use `MIPGap = 0.0`, `Threads = 1`, and a default time limit of `60` seconds. This supports exact, single-threaded solving for the tested instances. No explicit solver-level `Seed` setting was found, which means equivalent optimal solutions can still be selected differently across solver builds or platforms.

The validation audit confirms that the generated solutions pass the feasibility and consistency checks, including assignment feasibility, release-window consistency, wave capacity, worker-capacity, worker-balance, and tardiness consistency. Therefore, the observed `704.89` versus `748.65` difference should not be interpreted as infeasibility or a constraint violation.

This confirms that the two-stage sequential benchmark is sensitive to cross-environment tie-breaking under labour-shortage conditions. Because the first stage fixes release decisions before staffing cost is optimised, Stage-1-equivalent release plans can still induce different downstream staffing profiles. The integrated model is less exposed to this issue because release and staffing decisions are optimised jointly.

For strict cross-machine reproducibility, the sequential benchmark should include deterministic tie-breaking in the Stage-1 release-planning model, or this benchmark sensitivity should be explicitly reported in the final submission.
