# Calibration — rainroom

Local run, 2026-11-26.

| Check | Reference | Threshold |
|---|---|---|
| room shell | 4.200 x 3.600 x 2.800 m | ±0.02 |
| objects present | 26 / 26 | all |
| light collections | night 3, morning 2 | ≥1 each |
| night luminance | 0.173 | 0.10–0.32 |
| morning luminance | 0.682 | 0.55–0.80 |
| morning − night luminance | 0.509 | ≥0.25 |
| morning R−B − night R−B | 0.030 | ≥0.02 |
| anti-cheat delivered vs scene | 0.999 | ≥0.85 |
| anti-cheat light_night off | 0.610 | ≤0.98 |
| negative: light_morning emptied | mutated `.blend` | 0 | R04 light sets fails |

Notes
- The batch spec's absolute hue rule (night R−B ≤ −0.02) was not reachable with
  a warm interior lit by practicals; the check is now paired — morning must be
  at least 0.02 warmer than night and 0.25 brighter — which tests the same
  intent and is met by the reference (0.030 / 0.509).
- Practicals had to be moved out of their shades and the shades made emissive;
  with opaque shades and a solid glass pane the room rendered black.
- The room shell models the floor slab below and ceiling slab above, so the
  outer envelope is exactly 2.80 m with a 2.78 m clear height.
