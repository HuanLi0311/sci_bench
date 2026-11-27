# Current validation: toy-car

Evidence checked 2026-11-27T15:20:48.894253+00:00. These records match the current verifier source. Model provenance/completeness is separate from model-solving success.

| Gate | Status | Evidence |
|---|---|---|
| oracle | PASS | 20261126T185446Z-final-oracle |
| nop | PASS | 20261126T185856Z-final-nop |
| negatives | PASS | all 2 prepared negative cases rejected by the current verifier |
| models | PASS | 1 recorded attempts; complete raw trajectories checked where inference occurred |

| Case | Reward | Checks passed | Raw evidence |
|---|---:|---:|---|
| oracle | 1 | 16/16 | [metadata](../runs/20261126T185446Z-final-oracle/run.json), [metrics](../runs/20261126T185446Z-final-oracle/verifier/metrics.json), [reward](../runs/20261126T185446Z-final-oracle/verifier/reward.txt) |
| nop | 0 | 1/16 | [metadata](../runs/20261126T185856Z-final-nop/run.json), [metrics](../runs/20261126T185856Z-final-nop/verifier/metrics.json), [reward](../runs/20261126T185856Z-final-nop/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | 12/16 | [metadata](../runs/20261126T190201Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261126T190201Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261126T190201Z-final-negative-secondary-render-substitution/verifier/reward.txt) |
| negative-toy-wrong-wheel-parent | 0 | 12/16 | [metadata](../runs/20261126T185059Z-final-negative-toy-wrong-wheel-parent/run.json), [metrics](../runs/20261126T185059Z-final-negative-toy-wrong-wheel-parent/verifier/metrics.json), [reward](../runs/20261126T185059Z-final-negative-toy-wrong-wheel-parent/verifier/reward.txt) |

NOP executes only /bin/true in a fresh environment and exports the untouched output. Mutations are separate actual grading runs. Model requests, artifact grades and GUI compliance are recorded in the [model inventory](../model-attempts.json).
