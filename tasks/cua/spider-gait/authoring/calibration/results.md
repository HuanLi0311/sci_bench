# Calibration: spider-gait

Measured on the reference `solution/spider.blend` (Blender 4.2.3, Cycles CPU,
64 samples, denoise, seed 0) inside the verifier image.

| Metric | Reference | Threshold | Check |
|---|---:|---|---|
| bones / meshes | 25 / 26 | exact | R02, R03 |
| bone heads/tails | match `bone_spec.csv` within 0.5 mm | exact | R02 |
| mesh bound to its own bone | 26/26, 100 % of vertices | every mesh | R03 |
| body length | 180.0 mm | 180 ± 5 | R04 |
| foot span | 420.0 mm | 420 ± 10 | R04 |
| stance height | 120.0 mm | 120 ± 5 | R04 |
| loop seam | 0.0° / 0.0 mm | ≤ 0.5° / ≤ 1 mm | R06 |
| playback fps | 24 | exact | R05 |
| stance toe Z (max) | 1.5 mm | -1 … +2 mm | R07 |
| lowest toe Z | 1.5 mm | ≥ -1 mm | R08 |
| swing peak | 42.9 mm | ≥ 15 mm | R09 |
| stance drift | 0.0 mm | ≤ 5 mm | R10 |
| body bob | 0.0 mm | ≤ 8 mm | R11 |
| BVH overlaps, 24 frames | 0 | 0 | R12 |
| triangles | 2906 | ≤ 80 000 | R14 |
| delivered vs re-render | SSIM 1.000 | ≥ 0.90 | R18, R_render_structure |
| frame 7 vs frame 1 | SSIM 0.964 | ≤ 0.98 | R17 |

## Why these thresholds

- The seam is exactly 0 because frame 25 is generated from the same phase as
  frame 1. 0.5° / 1 mm leaves room for an agent that keys both ends by hand from
  a different rig orientation.
- Stance contact is measured on the tibia tail, not on the mesh. The drawing
  puts the toe at Z = 1.5 mm, so the accepted band is -1 … +2 mm; anything
  inside that is on the floor for this scale.
- 15 mm of swing lift is a third of the reference's 42.9 mm. It separates a real
  step from a twitch without demanding the reference's exact amplitudes.
- 5 mm of drift is measured across the whole stance window. The reference keys
  the identity during stance and measures 0; a hand-keyed gait that keeps the
  toe still to within 5 mm reads as planted at 420 mm span.
- The phase anti-cheat renders frame 7 — the submitted cycle shifted six frames.
  A still or fake action scores 1.000 and fails; the reference scores 0.964.

## Negative expectations

| Mutation | Must-fail check |
|---|---|
| `spider-broken-skin` (vertex groups removed from one segment) | R03_skinning |
| `spider-floating-feet` (rig raised 20 mm) | R07_support |
| `spider-static-pose` (action removed) | R17_phase_anticheat |
| `secondary-render-substitution` (render replaced by its mean colour) | R_render_structure |

## Negative results kept

- A first swing profile keyed only at lift-off and mid-swing left frame 25 one
  interpolation step away from frame 1 (0.9° seam). Keying all 25 frames from
  the phase function removed the class of bug entirely.
- The first collision pass sampled four key frames. A leg that clipped the
  abdomen between them would have passed, so the check now walks all 24 frames
  (about 20 s of verifier time).
