> Historical authoring notes below are preserved as claims/measurements from the earlier rubric. Their original raw Oracle logs were not in this task directory. Newly captured repeat executions are indexed in [RUNS.md](../../../RUNS.md), with exact source/input hashes, stdout/stderr, per-check metrics and reward files. These repeat executions do not reconstruct missing historical logs. A mutation is a negative test, not NOP. See [EVIDENCE.md](../../../EVIDENCE.md) and [model-attempts.json](../model-attempts.json).

# Calibration — folding-chair

Local run, 2026-11-26.

| Run | Input | Reward | Notes |
|---|---|---|---|
| oracle | shipped `solution/` | **1** | 13/13, 96 triangles, fold 89 mm, 0 strict overlaps |
| frame-30 re-render | anti-cheat | n/a | SSIM 0.915 vs frame 0 (threshold 0.98) |
| negative: hinge_03 moved 50 mm | mutated `.blend` | 0 | R03 hinge position fails |

Reference measurements: unfolded 0.620 x 0.580 x 0.823 m; folded thickness
0.089 m; hinges at (-0.28,0,0.225), (0.28,0,0.225), (-0.28,0.27,0.43),
(0,0.27,0.475); bar centroids 15 mm from the hinge axis (the two bars are
pinned side by side, hence the 20 mm coincidence tolerance).

## Notes

- The fold is driven by rotating each bar about its own origin, which sits on
  the hinge axis; hinge empties are the parents, so the joint stays coincident
  through the whole animation.
- Bars are offset 15 mm either side of the hinge plane and the seat/back are
  narrower than the bar spacing: without that, the scissor legs pass through
  the seat during the fold (measured 460 overlapping triangle pairs).
- Pairs that share a hinge are excluded from the interpenetration check —
  contact at a pinned joint is expected, penetration elsewhere is not.
