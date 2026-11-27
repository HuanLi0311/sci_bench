# Current validation: skateboard-prop

Evidence checked 2026-11-27T15:20:48.894253+00:00. These records match the current verifier source. Model provenance/completeness is separate from model-solving success.

| Gate | Status | Evidence |
|---|---|---|
| oracle | PASS | 20261127T143303Z-final-oracle |
| nop | PASS | 20261127T144217Z-final-nop |
| negatives | PASS | all 4 prepared negative cases rejected by the current verifier |
| models | PASS | 0 recorded attempts; complete raw trajectories checked where inference occurred |

| Case | Reward | Checks passed | Raw evidence |
|---|---:|---:|---|
| oracle | 1 | 16/16 | [metadata](../runs/20261127T143303Z-final-oracle/run.json), [metrics](../runs/20261127T143303Z-final-oracle/verifier/metrics.json), [reward](../runs/20261127T143303Z-final-oracle/verifier/reward.txt) |
| nop | 0 | 0/16 | [metadata](../runs/20261127T144217Z-final-nop/run.json), [metrics](../runs/20261127T144217Z-final-nop/verifier/metrics.json), [reward](../runs/20261127T144217Z-final-nop/verifier/reward.txt) |
| negative-deck-graphic-unlinked | 0 | 12/16 | [metadata](../runs/20261127T144236Z-final-negative-deck-graphic-unlinked/run.json), [metrics](../runs/20261127T144236Z-final-negative-deck-graphic-unlinked/verifier/metrics.json), [reward](../runs/20261127T144236Z-final-negative-deck-graphic-unlinked/verifier/reward.txt) |
| negative-deck-single-ply | 0 | 15/16 | [metadata](../runs/20261127T144000Z-final-negative-deck-single-ply/run.json), [metrics](../runs/20261127T144000Z-final-negative-deck-single-ply/verifier/metrics.json), [reward](../runs/20261127T144000Z-final-negative-deck-single-ply/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | 15/16 | [metadata](../runs/20261127T145447Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261127T145447Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261127T145447Z-final-negative-secondary-render-substitution/verifier/reward.txt) |
| negative-truck-dielectric | 0 | 15/16 | [metadata](../runs/20261127T145105Z-final-negative-truck-dielectric/run.json), [metrics](../runs/20261127T145105Z-final-negative-truck-dielectric/verifier/metrics.json), [reward](../runs/20261127T145105Z-final-negative-truck-dielectric/verifier/reward.txt) |

NOP executes only /bin/true in a fresh environment and exports the untouched output. Mutations are separate actual grading runs. Model requests, artifact grades and GUI compliance are recorded in the [model inventory](../model-attempts.json).
