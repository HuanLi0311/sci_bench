# Current validation: booth-clearance

Evidence checked 2026-11-27T15:20:48.894253+00:00. These records match the current verifier source. Model provenance/completeness is separate from model-solving success.

| Gate | Status | Evidence |
|---|---|---|
| oracle | PASS | 20261126T125639Z-final-oracle |
| nop | PASS | 20261126T130004Z-final-nop |
| negatives | PASS | all 9 prepared negative cases rejected by the current verifier |
| models | PASS | 2 recorded attempts; complete raw trajectories checked where inference occurred |

| Case | Reward | Checks passed | Raw evidence |
|---|---:|---:|---|
| oracle | 1 | 22/22 | [metadata](../runs/20261126T125639Z-final-oracle/run.json), [metrics](../runs/20261126T125639Z-final-oracle/verifier/metrics.json), [reward](../runs/20261126T125639Z-final-oracle/verifier/reward.txt) |
| nop | 0 | 5/22 | [metadata](../runs/20261126T130004Z-final-nop/run.json), [metrics](../runs/20261126T130004Z-final-nop/verifier/metrics.json), [reward](../runs/20261126T130004Z-final-nop/verifier/reward.txt) |
| negative-booth-camera-away | 0 | 17/22 | [metadata](../runs/20261126T125630Z-final-negative-booth-camera-away/run.json), [metrics](../runs/20261126T125630Z-final-negative-booth-camera-away/verifier/metrics.json), [reward](../runs/20261126T125630Z-final-negative-booth-camera-away/verifier/reward.txt) |
| negative-booth-closed-opening | 0 | 18/22 | [metadata](../runs/20261126T125630Z-final-negative-booth-closed-opening/run.json), [metrics](../runs/20261126T125630Z-final-negative-booth-closed-opening/verifier/metrics.json), [reward](../runs/20261126T125630Z-final-negative-booth-closed-opening/verifier/reward.txt) |
| negative-booth-hidden-secondary-color | 0 | 18/22 | [metadata](../runs/20261126T125858Z-final-negative-booth-hidden-secondary-color/run.json), [metrics](../runs/20261126T125858Z-final-negative-booth-hidden-secondary-color/verifier/metrics.json), [reward](../runs/20261126T125858Z-final-negative-booth-hidden-secondary-color/verifier/reward.txt) |
| negative-booth-missing-secondary-color | 0 | 18/22 | [metadata](../runs/20261126T125639Z-final-negative-booth-missing-secondary-color/run.json), [metrics](../runs/20261126T125639Z-final-negative-booth-missing-secondary-color/verifier/metrics.json), [reward](../runs/20261126T125639Z-final-negative-booth-missing-secondary-color/verifier/reward.txt) |
| negative-booth-moved-entrance-marker | 0 | 18/22 | [metadata](../runs/20261126T125621Z-final-negative-booth-moved-entrance-marker/run.json), [metrics](../runs/20261126T125621Z-final-negative-booth-moved-entrance-marker/verifier/metrics.json), [reward](../runs/20261126T125621Z-final-negative-booth-moved-entrance-marker/verifier/reward.txt) |
| negative-booth-product-floating | 0 | 18/22 | [metadata](../runs/20261126T125621Z-final-negative-booth-product-floating/run.json), [metrics](../runs/20261126T125621Z-final-negative-booth-product-floating/verifier/metrics.json), [reward](../runs/20261126T125621Z-final-negative-booth-product-floating/verifier/reward.txt) |
| negative-booth-product-scaled | 0 | 17/22 | [metadata](../runs/20261126T125621Z-final-negative-booth-product-scaled/run.json), [metrics](../runs/20261126T125621Z-final-negative-booth-product-scaled/verifier/metrics.json), [reward](../runs/20261126T125621Z-final-negative-booth-product-scaled/verifier/reward.txt) |
| negative-booth-unused-brand-slot | 0 | 18/22 | [metadata](../runs/20261126T125629Z-final-negative-booth-unused-brand-slot/run.json), [metrics](../runs/20261126T125629Z-final-negative-booth-unused-brand-slot/verifier/metrics.json), [reward](../runs/20261126T125629Z-final-negative-booth-unused-brand-slot/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | 21/22 | [metadata](../runs/20261126T125652Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261126T125652Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261126T125652Z-final-negative-secondary-render-substitution/verifier/reward.txt) |

NOP executes only /bin/true in a fresh environment and exports the untouched output. Mutations are separate actual grading runs. Model requests, artifact grades and GUI compliance are recorded in the [model inventory](../model-attempts.json).
