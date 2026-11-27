# Current validation: drawer-cabinet

Evidence checked 2026-11-27T18:32:05.177731+00:00. These records match the current verifier source. Model provenance/completeness is separate from model-solving success.

| Gate | Status | Evidence |
|---|---|---|
| oracle | PASS | 20261127T173411Z-final-oracle |
| nop | PASS | 20261127T173856Z-final-nop |
| negatives | PASS | all 4 prepared negative cases rejected by the current verifier |
| models | PENDING / FAIL | [Errno 2] No such file or directory: '/mnt/d/迅雷下载/ic-bench/tasks/cua/drawer-cabinet/authoring/model-attempts.json' |

| Case | Reward | Checks passed | Raw evidence |
|---|---:|---:|---|
| oracle | 1 | 16/16 | [metadata](../runs/20261127T173411Z-final-oracle/run.json), [metrics](../runs/20261127T173411Z-final-oracle/verifier/metrics.json), [reward](../runs/20261127T173411Z-final-oracle/verifier/reward.txt) |
| nop | 0 | 0/16 | [metadata](../runs/20261127T173856Z-final-nop/run.json), [metrics](../runs/20261127T173856Z-final-nop/verifier/metrics.json), [reward](../runs/20261127T173856Z-final-nop/verifier/reward.txt) |
| negative-cabinet-hinge-moved | 0 | 14/16 | [metadata](../runs/20261127T180728Z-final-negative-cabinet-hinge-moved/run.json), [metrics](../runs/20261127T180728Z-final-negative-cabinet-hinge-moved/verifier/metrics.json), [reward](../runs/20261127T180728Z-final-negative-cabinet-hinge-moved/verifier/reward.txt) |
| negative-cabinet-static-slides | 0 | 11/16 | [metadata](../runs/20261127T174219Z-final-negative-cabinet-static-slides/run.json), [metrics](../runs/20261127T174219Z-final-negative-cabinet-static-slides/verifier/metrics.json), [reward](../runs/20261127T174219Z-final-negative-cabinet-static-slides/verifier/reward.txt) |
| negative-cabinet-unpacked-maps | 0 | 15/16 | [metadata](../runs/20261127T182338Z-final-negative-cabinet-unpacked-maps/run.json), [metrics](../runs/20261127T182338Z-final-negative-cabinet-unpacked-maps/verifier/metrics.json), [reward](../runs/20261127T182338Z-final-negative-cabinet-unpacked-maps/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | 13/16 | [metadata](../runs/20261127T175133Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261127T175133Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261127T175133Z-final-negative-secondary-render-substitution/verifier/reward.txt) |

NOP executes only /bin/true in a fresh environment and exports the untouched output. Mutations are separate actual grading runs. Model requests, artifact grades and GUI compliance are recorded in the [model inventory](../model-attempts.json).
