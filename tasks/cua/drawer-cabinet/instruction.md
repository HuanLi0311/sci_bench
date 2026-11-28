You are working in a Blender 4.2 desktop session. `/app/materials` contains the
design pack for a drawer cabinet; `/app/out` is empty and is where you deliver.

## What you are given

- `materials/drawings/cabinet_three_views.png` (and `.pdf`) — front and side
  elevations, the drawer travel, and a door-hinge detail at 0°, 55° and 110°.
- `materials/spec/cabinet_spec.pdf` — carcass, drawer, door, material and
  render brief.
- `materials/spec/parts.csv` (and `.xlsx`) — part list with sizes.
- `materials/photos/` — three reference renders (day, night, detail).
- `materials/textures/wood_basecolor.png` — sample oak base colour.
- `materials/LICENSE.txt` — the licence for everything in the pack.

## What to build

Model the cabinet, light it twice and render three views. Use the GUI; the
deliverable is a scene a colleague can keep editing, not a screenshot.

1. Carcass, in metres, matching the drawing: 1000 wide × 450 deep × 900 high,
   panels 18 mm, 60 mm plinth with four feet. The carcass is separate meshes:
   `carcass_left`, `carcass_right`, `carcass_top`, `carcass_bottom`,
   `carcass_back` and a centre `carcass_divider`. Origin at floor centre, +Y
   front, +Z up.
2. Five drawers `drawer_01` … `drawer_05` in the left bay: fronts 440 × 140 mm
   and 18 mm thick on a 150 mm vertical pitch (10 mm gaps), trays 400 mm deep, steel handles. Each drawer is its own
   mesh, parented to an empty `slide_01` … `slide_05`; the empty translates
   along +Y from 0 to 420 mm and nothing else moves. Fully open, the tray must
   clear the carcass and every other drawer.
3. One door `door_right`, 450 × 746 × 18 mm, covering the right bay, parented to
   an empty `hinge_right` at (0.481, 0.2265, 0.505) that rotates about the
   vertical axis from 0° to 110°, swinging outwards. At 0°, 55° and 110° the
   door must not touch the carcass or the drawer fronts.
4. Materials: oak with 2048² base colour, roughness and normal maps driven into
   the shader and packed; steel handles and feet at metallic 1.0.
5. Two light collections, `light_day` (three area lights) and `light_night`
   (warm key plus cool fill), both saved in the file.

## What to deliver in /app/out

| File | Camera | Content |
|---|---|---|
| `drawer_cabinet.blend` | — | editable scene, maps packed |
| `render_day.png` | `cam_front34` | 1600 × 1200, day lights only |
| `render_night.png` | `cam_front34` | 1600 × 1200, night lights only |
| `render_detail.png` | `cam_detail` | 1600 × 1200, `drawer_02` out 300 mm, day lights |
| `manifest.json` | — | units, assets and licences |

`cam_front34`: 35 mm lens, 1.6 m from the cabinet centre horizontally, 1.15 m
above the floor. `cam_detail`: 50 mm lens, 0.60 m from the pulled drawer front,
aimed at `drawer_02` at its 300 mm position. Both cameras stay in the file.
Render with Cycles on CPU, 64 samples, denoising on, fixed seed.

`manifest.json` follows the usual shape:

```json
{
  "schemaVersion": 1,
  "units": "meters",
  "blenderVersion": "4.2.3",
  "assets": [
    {"path": "textures/wood_basecolor.png", "role": "texture",
     "source": "self-authored", "license": "CC0-1.0", "url": ""}
  ],
  "renders": [
    {"file": "render_day.png", "camera": "cam_front34",
     "resolution": [1600, 1200], "samples": 64}
  ]
}
```

## How it is checked

The file must reopen; outer size 1000 ± 3 × 450 ± 3 × 900 ± 3 mm; all six
carcass panels, five drawers, five slides and the door with its hinge present
and correctly parented; panel thickness 18 ± 1 mm; each slide moves its drawer
420 ± 2 mm and at full extension nothing overlaps the carcass or a neighbour;
the door at 0°, 55° and 110° never touches the carcass; the top drawer out and
the door at 110° still clear each other; three packed 2048² maps wired to base
colour, roughness and normal; handles metallic ≥ 0.9; at most 60 000 triangles;
the three renders at the stated sizes from the named cameras; the manifest
covering the maps.

Two anti-cheat checks run against the delivered files. The three delivered
renders are rebuilt from your scene in the canonical poses and compared with the
PNGs you shipped, and then two mutations must change their image: the night view
with the day lights switched on, and the detail view with `drawer_02` pulled
150 mm instead of 300 mm.

You have 7200 seconds to complete this task.
