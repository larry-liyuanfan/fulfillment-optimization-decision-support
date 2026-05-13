# Module 4: Solver Performance, Reproducibility, and Validation

## Key Checks

- Tested Windows venv, Windows Anaconda, and macOS venv environments.
- Ran Windows official-Gurobi repeated checks three times.
- Checked solver status, labour cost, late orders, temp/overtime hours, and solve time.
- Audited validation outputs for feasibility and consistency.
- Compared Mac/vendor and Windows/official sequential benchmark outputs.

---

## Main Finding

| Environment | `labour_shortage` Sequential Cost | Interpretation |
|---|---:|---|
| Mac/vendor | `704.89` | Reproduces report baseline |
| Windows/official | `748.65` | Internally stable across repeated runs |

Difference:

```text
748.65 - 704.89 = 43.76
```

This equals:

```text
2 extra temporary-worker hours × 21.88 = 43.76
```

---

## Stage-1 Diagnostic

- Stage-1 objective is identical in both environments:
  - Mac/vendor = `534.8`
  - Windows/official = `534.8`
- Weighted tardiness = `0.0` in both.
- Weighted flow time = `223.4` in both.
- Active waves = `11` in both.
- Therefore, the two environments selected different but Stage-1-equivalent release plans.

---

## Interpretation

- The difference is localised to the `labour_shortage` sequential benchmark.
- Integrated model results remain stable.
- Validation checks pass, so this is not a feasibility issue.
- Only `9` of `120` orders have different release periods.
- The discrepancy confirms cross-environment tie-breaking sensitivity in Stage-1 release-plan selection.

---

## Recommendation

- Add deterministic tie-breaking to the sequential Stage-1 release model.
- Or clearly report `labour_shortage` sequential benchmark sensitivity in the final report.
