# Current validation: folding-chair

Evidence checked 2026-11-27T15:20:48.894253+00:00. These records match the current verifier source. Model provenance/completeness is separate from model-solving success.

| Gate | Status | Evidence |
|---|---|---|
| oracle | PASS | 20261126T185107Z-final-oracle |
| nop | PASS | 20261126T185750Z-final-nop |
| negatives | PASS | all 3 prepared negative cases rejected by the current verifier |
| models | PASS | 1 recorded attempts; complete raw trajectories checked where inference occurred |

| Case | Reward | Checks passed | Raw evidence |
|---|---:|---:|---|
| oracle | 1 | 15/15 | [metadata](../runs/20261126T185107Z-final-oracle/run.json), [metrics](../runs/20261126T185107Z-final-oracle/verifier/metrics.json), [reward](../runs/20261126T185107Z-final-oracle/verifier/reward.txt) |
| nop | 0 | 2/15 | [metadata](../runs/20261126T185750Z-final-nop/run.json), [metrics](../runs/20261126T185750Z-final-nop/verifier/metrics.json), [reward](../runs/20261126T185750Z-final-nop/verifier/reward.txt) |
| negative-chair-common-root-collision | 0 | 11/15 | [metadata](../runs/20261126T185045Z-final-negative-chair-common-root-collision/run.json), [metrics](../runs/20261126T185045Z-final-negative-chair-common-root-collision/verifier/metrics.json), [reward](../runs/20261126T185045Z-final-negative-chair-common-root-collision/verifier/reward.txt) |
| negative-chair-shared-hinge-collision | 0 | 11/15 | [metadata](../runs/20261126T185045Z-final-negative-chair-shared-hinge-collision/run.json), [metrics](../runs/20261126T185045Z-final-negative-chair-shared-hinge-collision/verifier/metrics.json), [reward](../runs/20261126T185045Z-final-negative-chair-shared-hinge-collision/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | 13/15 | [metadata](../runs/20261126T185856Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261126T185856Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261126T185856Z-final-negative-secondary-render-substitution/verifier/reward.txt) |

NOP executes only /bin/true in a fresh environment and exports the untouched output. Mutations are separate actual grading runs. Model requests, artifact grades and GUI compliance are recorded in the [model inventory](../model-attempts.json).
