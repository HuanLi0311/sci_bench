# Calibration: skateboard-prop

Measured on the reference `solution/skateboard.blend` (Blender 4.2.3, Cycles
CPU, 64 samples, denoise, seed 0) inside the verifier image.

| Metric | Reference | Threshold | Check |
|---|---:|---|---|
| deck length / width | 800.0 / 200.0 mm | 800 ± 3 / 200 ± 2 | R02 |
| slab thickness (centreline) | 12.06 mm | 12 ± 1 | R02 |
| wheelbase | 440.0 mm | 440 ± 3 | R02 |
| wheel diameter | 53.7 mm | 54 ± 1 | R02 |
| overall deck height (kicks) | 67.3 mm | 45 … 90 | R02 |
| concave at the rails | 8.0 mm | 8 ± 2 | R02 |
| ply bands per side | 7 | ≥ 7 | R04 |
| band thickness | 1.71 mm | 1.0 … 2.6 mm | R04 |
| UV area of the underside | 1.000 | 0.95 … 1.02 | R05 |
| UV extent | [0,1] × [0,1] | ≥ 0.95 each axis | R05 |
| truck metallic | 0.90 | ≥ 0.8 | R07 |
| wheel roughness | 0.65 | 0.5 … 0.8 | R07 |
| triangles | 17 496 | ≤ 40 000 | R10 |
| GLB size | 1.0 MB | ≤ 15 MB | R08 |
| GLB triangle difference | 0.0000 | ≤ 1 % | R09 |
| GLB hierarchy | deck root; trucks under deck; wheels under their truck; bearings under deck | exact | R09 |
| rear axle centre | (0, 0, 0) | ≤ 5 mm | R11 |
| delivered vs re-render | SSIM 1.000 | ≥ 0.90 | R15, R_render_structure |
| checkerboard vs base (bottom) | SSIM 0.851 | ≤ 0.98 | R14 |
| deck lifted 60 mm vs base (3/4) | SSIM 0.949 | ≤ 0.98 | R14 |

## Why these thresholds

- The slab is measured on the centreline of the flat mid-section, where the
  concave term is zero. Measuring the AABB would include the kicks (about
  97 mm tall) and would reject every correct board.
- Band thickness is measured on the straight middle of the deck, away from the
  kicks, where all seven plies are exactly 1/7 of 12 mm.
- UV area 1.000 is what "1:1, not cropped" means numerically: the seven-ply
  underside is a single rectangle, so overlapping or tiling pushes the area
  above 1.02, and cropping drops the extent below 0.95.
- `R14` replaces the proposal's "rotate the wheels 90°" mutation. A wheel is
  rotationally symmetric, so that render is identical by construction and the
  check would pass a picture of a skateboard. The two mutations here move 15 %
  and 5 % of the frame respectively on a correct board.

## Negative expectations

| Mutation | Must-fail check |
|---|---|
| `deck-single-ply` (all side bands collapsed to one material) | R04_plies |
| `deck-graphic-unlinked` (artwork unplugged from the shader) | R05_graphic_uv |
| `truck-dielectric` (truck metallic set to 0) | R07_materials |
| `secondary-render-substitution` (render replaced by its mean colour) | R_render_structure |

## Negative results kept

- The bottom UV was mirrored on the first build: the artwork read backwards when
  seen from below, which the delivered-vs-render check would not catch (the
  render matched the scene). Flipping V and leaving U fixed puts the nose
  marker at +X and the wordmark upright; R05 now measures extent and area, so a
  future mirror flip still passes geometry but would be visible in the share
  render.
- Scaling the wheels 1.4× changed the three-quarter view by SSIM 0.996 because
  the trucks hide them from a 0.8 m camera. The deck lift moved the same check
  to 0.949.
