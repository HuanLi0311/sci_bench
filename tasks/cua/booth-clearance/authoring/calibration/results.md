> Historical authoring notes below are preserved as claims/measurements from the earlier rubric. Their original raw Oracle logs were not in this task directory. Newly captured repeat executions are indexed in [RUNS.md](../../../RUNS.md), with exact source/input hashes, stdout/stderr, per-check metrics and reward files. These repeat executions do not reconstruct missing historical logs. A mutation is a negative test, not NOP. See [EVIDENCE.md](../../../EVIDENCE.md) and [model-attempts.json](../model-attempts.json).

# Calibration — booth-clearance

Local runs, 2026-11-26, verifier image rebuilt from `tests/`.

| Run | Input | Reward | Notes |
|---|---|---|---|
| oracle | shipped `solution/` | **1** | 16/16, 1166 triangles |
| shifted cabinet (anti-cheat) | re-render with `cabinet_01` +0.5 m in Y | n/a | SSIM 0.972 vs threshold 0.98 |
| delivered-image substitution | not run yet | — | — |
| negative: entrance_zone deleted | mutated `.blend` | 0 | R02 objects fails |

Reference measurements: footprint 6.000 × 4.000 m; cabinet clearances 4.091 m
and 1.805 m; hydrant 1.30 m; visibility true/true/true; brand delta 1.9e-6;
renders 1920×1080 and 2048×1536; SSIM match 0.995.

## Notes

- The anti-cheat shifts the cabinet in Y, not X. An X shift moved it along the
  view axis and only changed 1.8 % of the frame (SSIM 0.982, above the 0.98
  threshold); a lateral shift is the honest test of "the cabinet is real".
- BVH ray casts must be built from world-space vertices. `BVHTree.FromObject`
  keeps object-local space and produced a false "column occludes product_02"
  verdict before this was fixed. The same fix was applied to `crate-lookdev`.

## Current frozen verifier evidence

The current verifier has a complete Oracle and a genuine no-op baseline. Raw metadata, exact source/input SHA-256 hashes, stdout/stderr, per-check metrics and reward files are linked below.

| Run | Reward | Checks | Raw record |
|---|---:|---|---|
| Oracle | 1 | 19/19 pass | [metadata](../runs/20261126T081658Z-final-oracle/run.json), [metrics](../runs/20261126T081658Z-final-oracle/verifier/metrics.json), [reward](../runs/20261126T081658Z-final-oracle/verifier/reward.txt) |
| NOP | 0 | 5/19 pass | [metadata](../runs/20261126T082355Z-final-nop/run.json), [metrics](../runs/20261126T082355Z-final-nop/verifier/metrics.json), [reward](../runs/20261126T082355Z-final-nop/verifier/reward.txt) |

NOP executes only `/bin/true` in the fresh task environment and exports the untouched empty `/app/out`; it is not a marker-deletion mutation. For the hardening changes and measured structural regressions, see [HARDENING.md](HARDENING.md).
