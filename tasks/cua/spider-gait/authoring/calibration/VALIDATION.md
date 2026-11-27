# Current validation: spider-gait

Evidence checked 2026-11-27T15:20:48.894253+00:00. These records match the current verifier source. Model provenance/completeness is separate from model-solving success.

| Gate | Status | Evidence |
|---|---|---|
| oracle | PASS | 20261127T143303Z-final-oracle |
| nop | PASS | 20261127T143939Z-final-nop |
| negatives | PASS | all 4 prepared negative cases rejected by the current verifier |
| models | PASS | 0 recorded attempts; complete raw trajectories checked where inference occurred |

| Case | Reward | Checks passed | Raw evidence |
|---|---:|---:|---|
| oracle | 1 | 19/19 | [metadata](../runs/20261127T143303Z-final-oracle/run.json), [metrics](../runs/20261127T143303Z-final-oracle/verifier/metrics.json), [reward](../runs/20261127T143303Z-final-oracle/verifier/reward.txt) |
| nop | 0 | 0/19 | [metadata](../runs/20261127T143939Z-final-nop/run.json), [metrics](../runs/20261127T143939Z-final-nop/verifier/metrics.json), [reward](../runs/20261127T143939Z-final-nop/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | 17/19 | [metadata](../runs/20261127T151131Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261127T151131Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261127T151131Z-final-negative-secondary-render-substitution/verifier/reward.txt) |
| negative-spider-broken-skin | 0 | 18/19 | [metadata](../runs/20261127T150227Z-final-negative-spider-broken-skin/run.json), [metrics](../runs/20261127T150227Z-final-negative-spider-broken-skin/verifier/metrics.json), [reward](../runs/20261127T150227Z-final-negative-spider-broken-skin/verifier/reward.txt) |
| negative-spider-floating-feet | 0 | 14/19 | [metadata](../runs/20261127T150523Z-final-negative-spider-floating-feet/run.json), [metrics](../runs/20261127T150523Z-final-negative-spider-floating-feet/verifier/metrics.json), [reward](../runs/20261127T150523Z-final-negative-spider-floating-feet/verifier/reward.txt) |
| negative-spider-static-pose | 0 | 14/19 | [metadata](../runs/20261127T150854Z-final-negative-spider-static-pose/run.json), [metrics](../runs/20261127T150854Z-final-negative-spider-static-pose/verifier/metrics.json), [reward](../runs/20261127T150854Z-final-negative-spider-static-pose/verifier/reward.txt) |

NOP executes only /bin/true in a fresh environment and exports the untouched output. Mutations are separate actual grading runs. Model requests, artifact grades and GUI compliance are recorded in the [model inventory](../model-attempts.json).
