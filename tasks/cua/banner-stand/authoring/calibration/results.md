# Calibration: banner-stand

Measured on the reference `solution/banner_stand.blend` (Blender 4.2.3, Cycles
CPU, 64 samples, denoise, seed 0) inside the verifier image.

| Metric | Reference | Threshold | Check |
|---|---:|---|---|
| frame width / height | 800.0 / 2000.0 mm | 800 ± 3 / 2000 ± 3 | R02 |
| frame on the floor | min z 0.0 mm | \|z\| ≤ 2 | R02 |
| canvas width / height | 800.0 / 1900.0 mm | 800 ± 3 / 1900 ± 3 | R04 |
| canvas planarity | 0.0 mm | ≤ 2 | R04 |
| canvas top edge | 1960 mm | 1960 ± 3 | R04 |
| UV area / extent | 1.000 / [0,1]² | 0.95 … 1.02, ≥ 0.95 | R05 |
| print aspect | 819 × 1945 (0.4211 vs 0.4211) | within 2 % | R05 |
| hinge location | (0, −0.045, 0.075) | ± 10 mm | R06 |
| brace at 14°: top z | 1922.2 mm | 1860 … 1960 | R06 |
| brace at 14°: reach | 521.4 mm | 460 … 560 | R06 |
| brace at 0°: bottom z | 75.0 mm | 75 ± 10 | R06 |
| folded depth | 123.0 mm | ≤ 130 | R06 |
| BVH contact, 0/7/14° | 0 / 0 / 0 | 0 | R07 |
| aluminium metallic | 0.92 | ≥ 0.8 | R08 |
| canvas roughness | 0.72 | 0.55 … 0.85 | R08 |
| triangles | 952 | ≤ 40 000 | R10 |
| delivered vs re-render | SSIM 0.994 | ≥ 0.90 | R14 |
| checker print vs base | SSIM 0.826 | ≤ 0.98 | R13 |
| brace 25° vs 14° | SSIM 0.914 | ≤ 0.98 | R13 |

## Why these thresholds

- The canvas is 1900 tall, not 2000: the 40 mm top bar occupies 1960–2000, and
  the print hangs from its underside. Requiring 2000 would force the print to
  overlap the bar.
- The brace is hinged at the base rather than at the bar. A rigid bar hinged at
  the top and long enough to reach the floor at 14° necessarily passes 60 mm
  below the floor when folded; hinging at the base keeps both the folded and the
  open state clean, and the folded depth is then set by the base (120 mm).
- Folded depth 130 mm leaves 7 mm over the reference 123 mm. The base alone is
  120 mm, so this threshold is effectively "the brace folds inside the base".
- SSIM 0.90 for the delivered-vs-re-render comparison is measured at 600 × 800 /
  800 × 600; the reference scores 0.994.

## Negative expectations

| Mutation | Must-fail check |
|---|---|
| `banner-leg-unparented` (brace no longer follows the hinge) | R06_fold_geometry |
| `banner-canvas-cropped` (UVs scaled to 0.8) | R05_uv |
| `banner-unpacked-print` (image reference left unpacked) | R09_self_contained |
| `secondary-render-substitution` (render replaced by its mean colour) | R_render_structure |

## Negative results kept

- The first build mapped the print left-to-right in world X; viewed from +Y it
  read mirrored. The delivered-vs-render check cannot catch that (both are
  mirrored), so the reference flips U and the share render is inspected by eye
  during calibration.
- Parenting with `matrix_parent_inverse` read before the depsgraph updated put
  the brace 1.96 m too high. The reference sets the inverse from the hinge's
  location explicitly and the verifier measures world coordinates, which is what
  caught it.
- Rotating the brace the wrong way was not a modelling error the eye notices in
  a still; the BVH contact count at 7° went from 0 to 26 and the verifier
  reported it.
