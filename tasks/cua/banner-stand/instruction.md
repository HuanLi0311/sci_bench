You are working in a Blender 4.2 desktop session. `/app/materials` contains the
design pack for a folding banner stand; `/app/out` is empty and is where you
deliver.

## What you are given

- `materials/drawings/banner_three_views.png` (and `.pdf`) — front elevation,
  side elevation open and side elevation folded, with the rear-leg angle.
- `materials/spec/banner_spec.pdf` — frame, canvas, hinge and material brief.
- `materials/spec/parts.csv` (and `.xlsx`) — part list with sizes.
- `materials/photos/` — three reference renders.
- `materials/LICENSE.txt` — the licence for everything in the pack.

## What to build

Model the stand, apply the print and render three views. Use the GUI; the
deliverable is a scene a colleague can keep editing.

1. Frame, in metres: `base` 800 × 120 × 50 mm on the floor, `mast_left` and
   `mast_right` 40 × 40 mm rising to z = 1960 at x = ±380, `top_bar`
   800 × 40 × 40 mm from 1960 to 2000. Overall 800 wide and 2000 high. Origin
   at floor centre, +Y front, +Z up.
2. Canvas `canvas`: 800 × 1900 mm from z = 60 to 1960, facing +Y. It hangs flat:
   every vertex within 2 mm of its plane and its top edge within 3 mm of the top
   bar underside. The print is mapped 1:1 with no crop and no overlap; UV area 1.0.
3. Rear leg `leg_rear`: 2020 mm long, parented to an empty `hinge_rear` at
   (0, 0, 1.960) that rotates about X, swinging the leg away from the print. At 0° it is
   folded against the masts; at 14° it is open and its foot rests on the floor
   (|z| ≤ 5 mm) about 490 mm behind the stand. At 0°, 7° and 14° the leg must not touch the masts,
   the top bar or the canvas. Folded, the whole stand is at most 130 mm deep.
4. Materials: printed textile on the canvas (roughness 0.55–0.85, artwork
   packed) and aluminium frame at metallic ≥ 0.8.

## What to deliver in /app/out

| File | Camera | Content |
|---|---|---|
| `banner_stand.blend` | — | editable scene, print packed |
| `render_front.png` | `cam_front` | 1200 × 1600, leg at 14° |
| `render_three_quarter.png` | `cam_three_quarter` | 1600 × 1200, leg at 14° |
| `render_folded.png` | `cam_folded` | 1200 × 1600, leg folded to 0° |
| `manifest.json` | — | units, assets and licences |

`cam_front` and `cam_folded`: orthographic, 2.15 m coverage, looking at the stand
from +Y. `cam_three_quarter`: 35 mm perspective from the front right. Render
with Cycles on CPU, 64 samples, denoising on, fixed seed.

`manifest.json` follows the usual shape:

```json
{
  "schemaVersion": 1,
  "units": "meters",
  "blenderVersion": "4.2.3",
  "assets": [
    {"path": "textures/banner_graphic.png", "role": "texture",
     "source": "self-authored", "license": "CC0-1.0", "url": ""}
  ],
  "renders": [
    {"file": "render_front.png", "camera": "cam_front",
     "resolution": [1200, 1600], "samples": 64}
  ]
}
```

## How it is checked

The file must reopen; frame 800 ± 3 mm wide and 2000 ± 3 mm high, standing on
the floor; all parts present with `leg_rear` parented to an empty `hinge_rear`;
the canvas 800 ± 3 × 1900 ± 3 mm, flat within 2 mm, top within 3 mm of the bar;
UV area 1.0 with full extent and the print aspect within 2 % of 800/1900; the
hinge at (0, 0, 1.96) ± 10 mm; at 14° the leg tip on the floor and 450–540 mm
behind the stand; folded depth ≤ 130 mm; no contact between the leg and the
frame at 0°, 7° and 14°; aluminium metallic ≥ 0.8 and canvas roughness in range;
the print packed; at most 40 000 triangles; the three renders at the stated
sizes from the named cameras; the manifest covering the print.

Two anti-cheat checks run against the delivered files. The rendered views are
rebuilt from your scene and compared with the PNGs you shipped, and then two
mutations must change their image: the print replaced by a checkerboard, and the
rear leg moved to 25° instead of 14°.

You have 7200 seconds to complete this task.
