> Historical authoring notes below are preserved as claims/measurements from the earlier rubric. Their original raw Oracle logs were not in this task directory. Newly captured repeat executions are indexed in [RUNS.md](../../../RUNS.md), with exact source/input hashes, stdout/stderr, per-check metrics and reward files. These repeat executions do not reconstruct missing historical logs. A mutation is a negative test, not NOP. See [EVIDENCE.md](../../../EVIDENCE.md) and [model-attempts.json](../model-attempts.json).

# Calibration — toy-car

Local run, 2026-11-26.

| Check | Reference | Threshold |
|---|---|---|
| wheelbase | 0.2400 m | ±0.003 |
| wheel diameter | 0.060 m x4 | ±0.002 |
| axle level / parallel | 0.0 / 0.0 | ≤0.002 |
| body moved by wheel spin | 0.0 | <1e-6 |
| door overlap at 0/25/50/75 | 0 / 0 / 0 / 0 | none |
| silhouette IoU | 1.00 x4 | ≥0.75 |
| anti-cheat delivered vs scene | 0.999 | ≥0.90 |
| anti-cheat wheel spin+steer | 0.986 | ≤0.995 |
| negative: wheels scaled 1.2x | mutated `.blend` | 0 | R04 wheel diameter fails |

Notes
- Silhouettes are compared after a border flood-fill that removes the white
  background, at 240x240. Both the reference plates and submissions go through
  the same path, so a faithful model scores 1.00.
- The anti-cheat spins all four wheels 90 degrees and steers the front pair 25
  degrees: spinning alone only changed 1.2 % of the frame (SSIM 0.988), too
  close to the 0.98 threshold.
- Tread blocks are real geometry on the wheels so the spin is visible; without
  them a smooth cylinder renders identically at any angle.
