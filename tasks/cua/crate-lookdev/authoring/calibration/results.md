> Historical authoring notes below are preserved as claims/measurements from the earlier rubric. Their original raw Oracle logs were not in this task directory. Newly captured repeat executions are indexed in [RUNS.md](../../../RUNS.md), with exact source/input hashes, stdout/stderr, per-check metrics and reward files. These repeat executions do not reconstruct missing historical logs. A mutation is a negative test, not NOP. See [EVIDENCE.md](../../../EVIDENCE.md) and [model-attempts.json](../model-attempts.json).

# Calibration record — crate-lookdev

Local runs, 2026-11-25. Verifier image `cua-crate-tests:dev`, agent image
`cua-crate-env:dev`, both Blender 4.2.3 LTS on this WSL2 host.

| Run | Input | Reward | Notes |
|---|---|---|---|
| oracle | `solution/` as shipped | **1** | 13/13 checks, 2858 triangles, R13 0.991 / 0.948 |
| swapped render | `render_front.png` replaced by `render_top.png` | 0 | R10 distinct-hash fails, R13 delivered_vs_scene = 0.563 |
| unpacked textures | `.blend` with all images unpacked | 0 | R07 big_maps = 0, packed_all = false |

Reference numbers measured by `check_scene.py`:

- outer envelope 0.805 × 0.602 × 0.6005 m (tolerance ±0.005)
- panel thickness 20.0 mm on all five panels (tolerance 18–22 mm)
- bevels 3.0 mm on panels and lid (threshold ≥ 2 mm)
- lid pivot at (0, 0.300, 0.580), overlaps 0 / 0 / 0 at 0°, 45°, 95°
- oak roughness standard deviation 0.072 (threshold ≥ 0.05)
- bracket metallic 1.0 (threshold ≥ 0.9)
- stencil worn-edge fraction 0.043 (threshold ≥ 0.02)
- camera geometry: front/back 1.598 m at z 0.900, lens 35; top ortho 1.0;
  macro 100 mm at 0.271 m from the nearest bracket (tolerance ±0.06)

## Threshold rationale

- **SSIM 0.90 for "delivered image came from the scene"** — two renders of the
  same scene at the same resolution differ only by sampling noise; measured
  0.991 on a 960×720 re-render against the 1600×1200 delivery after downscale.
  A substituted image measured 0.563.
- **SSIM 0.98 for "the lid change must show"** — 60° of lid rotation changes a
  small fraction of the frame; measured 0.948. Lowering the threshold toward
  0.90 would start failing legitimate renders whose lid is partly out of frame.
- **Outer-size tolerance ±5 mm** — brackets stand 1 mm proud, so the true
  envelope is 802 mm; keeping 5 mm leaves room for a modeller who flushes them.

## Known deviations from the batch spec

- Blender is the archive build in the local `blender-bench:gui` image
  (4.2.3 LTS, same version, different provenance). The official tarball host is
  unreachable from this network; see `authoring/base-image.md`.
- `[environment]` asks for 4 CPUs / 8 GB. The rendering reference was produced
  on 24 host cores; a 4-CPU agent container will be slower, which is why the
  agent budget is 2 h and the verifier 30 min.

## Not yet done

- Five blind CUA trials against a frontier model have not been run; the
  published target pass rate (45–65%) is a design estimate, not a measurement.

## Final current-source validation

The completed final records are in [VALIDATION.md](VALIDATION.md). Current-source Oracle reward=1, genuine NOP reward=0, and all required negative cases reward=0. Historical claims, failed development runs and superseded snapshots above remain tied to their own recorded inputs/source versions.
