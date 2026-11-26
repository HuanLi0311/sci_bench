# Current validation: rainroom

Completed current-source verification, checked 2026-11-26T10:57:43.651546+00:00. All rows below have raw stdout/stderr, exact source/input hashes, metrics and reward files.

| Case | Reward | Checks passed | Raw evidence |
|---|---:|---:|---|
| oracle | 1 | 16/16 | [metadata](../runs/20261126T090928Z-final-oracle/run.json), [metrics](../runs/20261126T090928Z-final-oracle/verifier/metrics.json), [reward](../runs/20261126T090928Z-final-oracle/verifier/reward.txt) |
| nop | 0 | 1/16 | [metadata](../runs/20261126T091908Z-final-nop/run.json), [metrics](../runs/20261126T091908Z-final-nop/verifier/metrics.json), [reward](../runs/20261126T091908Z-final-nop/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | 14/16 | [metadata](../runs/20261126T093333Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261126T093333Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261126T093333Z-final-negative-secondary-render-substitution/verifier/reward.txt) |

NOP executes only `/bin/true` in a fresh task image and exports the untouched empty output. Negative mutations are separate runs. The final package QC is [here](../../../evaluation/20261126T105010Z-all-tasks-final-qc/qc.json).
