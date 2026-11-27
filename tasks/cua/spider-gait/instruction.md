You are working in a Blender 4.2 desktop session. `/app/materials` contains the
design pack for a cartoon spider game character; `/app/out` is empty and is
where you deliver.

## What you are given

- `materials/drawings/spider_three_views.png` (and `.pdf`) — top / front / side
  views, millimetres, joint centres marked.
- `materials/spec/bone_spec.xlsx` (and `.csv`, `.pdf`) — all 25 bones with
  parent, head and tail coordinates, segment lengths and roll rule.
- `materials/spec/gait_timing.csv` and `gait_phase.png` — the 24-frame cycle:
  phases, touchdown frame, stance window and swing window per foot.
- `materials/poses/key_pose_01..04.png` — touchdown, mid-stance, lift-off and
  mid-swing, rendered from the side camera.
- `materials/textures/chitin_basecolor.png` — 1024 px body pattern.
- `materials/LICENSE.txt` — the licence for everything in the pack.

## What to build

Model the spider, rig it, animate the gait and render the key poses. Use the
GUI; the deliverable is a scene a colleague can keep editing, not a screenshot.

1. Geometry, in metres, matching the drawing:
   - head-thorax `body_head` and abdomen `body_abdomen` as separate meshes;
     body length 180 mm, stance height 120 mm;
   - eight legs, each in three rigid segments; toe-to-toe span 420 mm;
   - one mesh per segment, named `leg_01_coxa` … `leg_08_tibia`
     (24 meshes), all with real thickness. Do not join a leg into one mesh.
2. Rig `rig_spider`, 25 deform bones:
   - `body` is the root; every leg is `body → coxa → femur → tibia`;
   - names, parents, head/tail coordinates and lengths exactly as in
     `bone_spec`;
   - every segment mesh carries an Armature modifier bound to `rig_spider`,
     every vertex has 1–4 deform weights summing to 1, and no vertex is
     unweighted.
3. Action `Walk_Cycle` on the armature:
   - keys 1–25 with frame 25 identical to frame 1; scene playback 1–24, fps 24;
   - alternating tetrapod: legs 01/03/05/07 at phases 0/6/12/18 and legs
     02/04/06/08 twelve frames later; stance 18 frames, swing 6 frames;
   - stance feet planted (≤ 5 mm horizontal drift, toe tip Z between -1 and
     +2 mm); swing feet lift at least 15 mm; body vertical bob ≤ 8 mm;
   - no self-intersection between legs, or between a leg and either body mesh,
     at frames 1, 10, 18 and 21.
4. Pack the texture into the .blend. The file must open and render after
   `/app/materials` is removed.

## What to deliver in /app/out

| File | Content |
|---|---|
| `spider.blend` | editable scene, texture packed |
| `render_pose_01.png` | `cam_side`, frame 1, 960 × 540 |
| `render_pose_02.png` | `cam_side`, frame 10, 960 × 540 |
| `render_pose_03.png` | `cam_side`, frame 18, 960 × 540 |
| `render_pose_04.png` | `cam_side`, frame 21, 960 × 540 |
| `render_top.png` | `cam_top`, orthographic, 960 × 960 |
| `manifest.json` | units, Blender version, asset sources and licences |

`cam_side`: 50 mm lens, 0.75 m from the body centre, 0.13 m above the floor.
`cam_top`: orthographic, 0.50 × 0.50 m coverage, looking straight down. Both
cameras stay in the file with those names. Render with Cycles on CPU, 64
samples, denoising on, fixed seed.

`manifest.json` follows the usual shape and lists the texture:

```json
{
  "schemaVersion": 1,
  "units": "meters",
  "blenderVersion": "4.2.3",
  "assets": [
    {"path": "textures/chitin_basecolor.png", "role": "texture",
     "source": "self-authored", "license": "CC0-1.0", "url": ""}
  ],
  "renders": [
    {"file": "render_pose_01.png", "camera": "cam_side",
     "resolution": [960, 540], "samples": 64}
  ]
}
```

## How it is checked

The file must reopen in Blender; all 25 bones and 26 segment/body meshes must
exist with the stated names, parents and skin weights; body length 180 ± 5 mm,
foot span 420 ± 10 mm, stance height 120 ± 5 mm; the action must cover frames
1–25 with scene range 1–24; frame 1 and frame 25 must agree within 0.5° and
1 mm; stance toes within -1…+2 mm of the floor, swing toes at least 15 mm up,
stance drift at most 5 mm; no leg/body interpenetration at the four key frames;
at most 80 000 triangles; the five renders at the stated sizes from the two
named cameras; the texture packed; the manifest covering the texture.

Two anti-cheat checks run against the delivered files. Every delivered render
is re-rendered from your scene and compared with the PNG you shipped (structure
and per-channel agreement), and the cycle is rendered six frames out of phase:
if the action is real, that image must differ.

You have 7200 seconds to complete this task.
