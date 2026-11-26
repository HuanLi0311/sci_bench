# Current validation: crate-lookdev

Completed current-source verification, checked 2026-11-26T10:57:43.590206+00:00. All rows below have raw stdout/stderr, exact source/input hashes, metrics and reward files.

| Case | Reward | Checks passed | Raw evidence |
|---|---:|---:|---|
| oracle | 1 | 15/15 | [metadata](../runs/20261126T094534Z-final-oracle/run.json), [metrics](../runs/20261126T094534Z-final-oracle/verifier/metrics.json), [reward](../runs/20261126T094534Z-final-oracle/verifier/reward.txt) |
| nop | 0 | 0/15 | [metadata](../runs/20261126T095104Z-final-nop/run.json), [metrics](../runs/20261126T095104Z-final-nop/verifier/metrics.json), [reward](../runs/20261126T095104Z-final-nop/verifier/reward.txt) |
| negative-crate-disconnected-maps | 0 | 10/15 | [metadata](../runs/20261126T094503Z-final-negative-crate-disconnected-maps/run.json), [metrics](../runs/20261126T094503Z-final-negative-crate-disconnected-maps/verifier/metrics.json), [reward](../runs/20261126T094503Z-final-negative-crate-disconnected-maps/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | 13/15 | [metadata](../runs/20261126T095146Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261126T095146Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261126T095146Z-final-negative-secondary-render-substitution/verifier/reward.txt) |
| model-regrade | 0 | 7/15 | [metadata](../runs/20261126T095121Z-final-model-regrade/run.json), [metrics](../runs/20261126T095121Z-final-model-regrade/verifier/metrics.json), [reward](../runs/20261126T095121Z-final-model-regrade/verifier/reward.txt) |

NOP executes only `/bin/true` in a fresh task image and exports the untouched empty output. Negative mutations are separate runs. The final package QC is [here](../../../evaluation/20261126T105010Z-all-tasks-final-qc/qc.json).

The historical model now receives a genuine artifact score of 0 after successful FONT scene extraction: size, hinge/penetration, material variation, stencil wear and camera requirements fail. Earlier scores produced by the TextCurve parser exception are preserved and superseded; the original Harbor run itself had a verifier infrastructure error.
