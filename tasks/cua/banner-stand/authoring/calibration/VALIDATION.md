# Current validation: banner-stand

Evidence checked 2026-11-27T18:32:48.850020+00:00. These records match the current verifier source. Model provenance/completeness is separate from model-solving success.

| Gate | Status | Evidence |
|---|---|---|
| oracle | PASS | 20261127T173916Z-final-oracle |
| nop | PASS | 20261127T174206Z-final-nop |
| negatives | PASS | all 4 prepared negative cases rejected by the current verifier |
| models | PASS | 0 recorded attempts; complete raw trajectories checked where inference occurred |

| Case | Reward | Checks passed | Raw evidence |
|---|---:|---:|---|
| oracle | 1 | 15/15 | [metadata](../runs/20261127T173916Z-final-oracle/run.json), [metrics](../runs/20261127T173916Z-final-oracle/verifier/metrics.json), [reward](../runs/20261127T173916Z-final-oracle/verifier/reward.txt) |
| nop | 0 | 0/15 | [metadata](../runs/20261127T174206Z-final-nop/run.json), [metrics](../runs/20261127T174206Z-final-nop/verifier/metrics.json), [reward](../runs/20261127T174206Z-final-nop/verifier/reward.txt) |
| negative-banner-canvas-cropped | 0 | 11/15 | [metadata](../runs/20261127T175618Z-final-negative-banner-canvas-cropped/run.json), [metrics](../runs/20261127T175618Z-final-negative-banner-canvas-cropped/verifier/metrics.json), [reward](../runs/20261127T175618Z-final-negative-banner-canvas-cropped/verifier/reward.txt) |
| negative-banner-hinge-moved | 0 | 14/15 | [metadata](../runs/20261127T181649Z-final-negative-banner-hinge-moved/run.json), [metrics](../runs/20261127T181649Z-final-negative-banner-hinge-moved/verifier/metrics.json), [reward](../runs/20261127T181649Z-final-negative-banner-hinge-moved/verifier/reward.txt) |
| negative-banner-unpacked-print | 0 | 14/15 | [metadata](../runs/20261127T182816Z-final-negative-banner-unpacked-print/run.json), [metrics](../runs/20261127T182816Z-final-negative-banner-unpacked-print/verifier/metrics.json), [reward](../runs/20261127T182816Z-final-negative-banner-unpacked-print/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | 12/15 | [metadata](../runs/20261127T180159Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261127T180159Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261127T180159Z-final-negative-secondary-render-substitution/verifier/reward.txt) |

NOP executes only /bin/true in a fresh environment and exports the untouched output. Mutations are separate actual grading runs. Model requests, artifact grades and GUI compliance are recorded in the [model inventory](../model-attempts.json).
