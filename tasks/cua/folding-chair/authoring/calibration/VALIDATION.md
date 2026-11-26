# Current validation: folding-chair

Completed current-source verification, checked 2026-11-26T10:57:43.624670+00:00. All rows below have raw stdout/stderr, exact source/input hashes, metrics and reward files.

| Case | Reward | Checks passed | Raw evidence |
|---|---:|---:|---|
| oracle | 1 | 15/15 | [metadata](../runs/20261126T090301Z-final-oracle/run.json), [metrics](../runs/20261126T090301Z-final-oracle/verifier/metrics.json), [reward](../runs/20261126T090301Z-final-oracle/verifier/reward.txt) |
| nop | 0 | 2/15 | [metadata](../runs/20261126T090919Z-final-nop/run.json), [metrics](../runs/20261126T090919Z-final-nop/verifier/metrics.json), [reward](../runs/20261126T090919Z-final-nop/verifier/reward.txt) |
| negative-chair-common-root-collision | 0 | 11/15 | [metadata](../runs/20261126T085607Z-final-negative-chair-common-root-collision/run.json), [metrics](../runs/20261126T085607Z-final-negative-chair-common-root-collision/verifier/metrics.json), [reward](../runs/20261126T085607Z-final-negative-chair-common-root-collision/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | 13/15 | [metadata](../runs/20261126T092823Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261126T092823Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261126T092823Z-final-negative-secondary-render-substitution/verifier/reward.txt) |

NOP executes only `/bin/true` in a fresh task image and exports the untouched empty output. Negative mutations are separate runs. The final package QC is [here](../../../evaluation/20261126T105010Z-all-tasks-final-qc/qc.json).
