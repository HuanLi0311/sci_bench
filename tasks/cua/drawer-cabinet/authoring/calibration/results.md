# Calibration: drawer-cabinet

Measured on the reference `solution/drawer_cabinet.blend` (Blender 4.2.3, Cycles
CPU, 64 samples, denoise, seed 0) inside the verifier image.

| Metric | Reference | Threshold | Check |
|---|---:|---|---|
| outer envelope | 1000.0 × 450.0 × 900.0 mm | 1000 ± 3, 450 ± 3, 900 ± 3 | R02 |
| carcass panels | 6 × 18.0 mm | 18 ± 1 | R04 |
| drawer travel | 420.0 mm, all five | 420 ± 2 | R05 |
| drawer clearance at 420 | 0 overlaps | 0 | R06 |
| door overlaps at 0/55/110° | 0 / 0 / 0 | 0 | R07 |
| combined pose (drawer_05 out, door 110°) | 0 | 0 | R08 |
| 2K maps wired | 3 (base, roughness, normal) | 3 | R09 |
| steel metallic | 1.00 | ≥ 0.9 | R09 |
| triangles | 2596 | ≤ 60 000 | R11 |
| delivered vs re-render | SSIM 0.994 | ≥ 0.90 | R15 |
| night vs day-lit | SSIM 0.661 | ≤ 0.98 | R14 |
| drawer 300 vs 150 mm | SSIM 0.768 | ≤ 0.98 | R14 |

## Why these thresholds

- The envelope is measured over the carcass panels plus the feet, so the plinth
  counts toward the 900 mm height. Measuring the panels alone reports 840 mm and
  would reject a correct cabinet.
- Travel is measured by moving the slide empty 420 mm and reading the drawer's
  world AABB before and after; that also proves the drawer is parented to the
  slide rather than merely placed next to it.
- The door hinge sits on the front face (0.481, 0.2265, 0.505). A hinge on the
  panel's mid-thickness swings the inner corner into the carcass within 20° of
  opening; the reference measured 70 overlapping faces before the hinge was
  moved out and 0 after.
- Re-renders are 800 × 600 against delivered 1600 × 1200 images: 4× cheaper, and
  the reference still scores 0.994.

## Negative expectations

| Mutation | Must-fail check |
|---|---|
| `cabinet-static-slides` (drawers unparented from the slides) | R05_travel |
| `cabinet-door-unparented` (door no longer follows the hinge) | R07_door_hinge |
| `cabinet-unpacked-maps` (image reference left unpacked) | R10_self_contained |
| `secondary-render-substitution` (render replaced by its mean colour) | R_render_structure |

## Negative results kept

- The first carcass stopped at 880 mm because the top panel was placed at the
  last drawer bay instead of the envelope top; the verifier reported 820 mm
  before the feet were included and 840 mm after, which is what caught it.
- The normal map was not detected at first: the traversal followed only the
  first input socket of every intermediate node, and `Normal Map` takes its
  colour on the second socket. The fix scans every input.
- Moving two verifier passes in parallel on this machine (7.8 GB WSL VM) gets
  the whole container group reaped; every recorded run here is serial.
