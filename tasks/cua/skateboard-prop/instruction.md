You are working in a Blender 4.2 desktop session. `/app/materials` contains the
design pack for a skateboard game prop; `/app/out` is empty and is where you
deliver.

## What you are given

- `materials/drawings/skateboard_three_views.png` (and `.pdf`) — plan, side and
  end views with dimensions and the seven-ply edge detail.
- `materials/spec/deck_graphic.png` — 2048 × 512 artwork for the underside,
  printed 1:1 with its nose marker at the +X end.
- `materials/spec/material_spec.pdf` (and `.csv`, `.xlsx`) — deck, truck, wheel
  and bearing materials with numeric ranges.
- `materials/photos/` — three renders of the reference board.
- `materials/LICENSE.txt` — the licence for everything in the pack.

## What to build

Model the board, light and shade it, and render the three views. Use the GUI;
the deliverable is a scene and a GLB a colleague can drop into an engine.

1. Deck `deck`: 800 × 200 mm plan, 12 mm slab, seven-ply maple with seven
   visible edge bands of about 1.7 mm each and slightly different colours;
   kicktails rising at 20° over the last 130 mm at both ends; 8 mm concave at
   the rails. The underside carries the artwork 1:1 — UVs cover the sheet
   without overlap or cropping — and the top is grip tape.
2. Hardware: `truck_front`, `truck_rear` (6061 aluminium, 180 mm wide,
   metallic ≥ 0.8), `wheel_01` … `wheel_04` (polyurethane 78A, 54 mm diameter,
   32 mm wide, roughness 0.5–0.8) and one `bearings` mesh (steel).
3. Hierarchy: `deck` is the root; both trucks are its children; wheels 01–02
   hang under `truck_front`, wheels 03–04 under `truck_rear`.
4. Geometry and placement: wheelbase 440 mm axle-to-axle; the rear axle centre
   is the scene origin (0, 0, 0) and +X points to the nose.
5. Keep the whole board under 40 000 triangles. Textures are at most 2048 px in
   either direction, PBR metallic-roughness, and packed into the .blend.
6. Export `skateboard.glb` from this scene: GLB, under 15 MB, textures
   embedded, metres, hierarchy preserved.

## What to deliver in /app/out

| File | Content |
|---|---|
| `skateboard.blend` | editable scene, artwork packed |
| `skateboard.glb` | engine-ready export of the same board |
| `render_three_quarter.png` | `cam_three_quarter`, 1600 × 1200 |
| `render_bottom.png` | `cam_bottom`, orthographic, 1600 × 900 |
| `render_edge.png` | `cam_edge`, 100 mm macro, 1600 × 1200 |
| `manifest.json` | units, assets and licences, render parameters |

`cam_three_quarter`: 35 mm lens, 1.2 m from the deck centre horizontally, 0.8 m
above the deck plane. `cam_bottom`: orthographic, 900 × 506 mm coverage,
looking up at the underside. `cam_edge`: 100 mm lens, 0.25 m from the side rail,
framing the seven plies. All three cameras stay in the file with those names.
Render with Cycles on CPU, 64 samples, denoising on, fixed seed.

`manifest.json` follows the usual shape and lists the artwork:

```json
{
  "schemaVersion": 1,
  "units": "meters",
  "blenderVersion": "4.2.3",
  "assets": [
    {"path": "spec/deck_graphic.png", "role": "texture",
     "source": "self-authored", "license": "CC0-1.0", "url": ""}
  ],
  "renders": [
    {"file": "render_bottom.png", "camera": "cam_bottom",
     "resolution": [1600, 900], "samples": 64}
  ]
}
```

## How it is checked

The .blend must reopen; the eight named parts must exist with the stated
parents; deck 800 ± 3 × 200 ± 2 mm and 12 ± 1 mm thick; wheelbase 440 ± 3 mm;
wheel diameter 54 ± 1 mm; seven distinct edge bands per side, each 1–2.6 mm
thick, with distinct colours; the underside artwork 2048 × 512, mapped 1:1 with
UV area and extent matching the sheet; textures packed and no larger than 2048;
truck metallic ≥ 0.8 and wheel roughness 0.5–0.8; rear axle centre at the
origin within 5 mm; at most 40 000 triangles; the three renders at the stated
sizes from the named cameras; the manifest covering the artwork.

The GLB is re-imported into an empty scene: it must contain the same parts and
hierarchy, within 1 % of the .blend triangle count, at least seven materials,
and embedded (not linked) images.

Two anti-cheat checks run against the delivered files. Every delivered render
is re-rendered from your scene and compared with the PNG you shipped (per
channel and in structure), the artwork is swapped for a checkerboard and the
underside re-rendered, and the four wheels are scaled 1.4× and the three-quarter
view re-rendered. If the parts and the renders are real, both images must
change.

You have 7200 seconds to complete this task.
