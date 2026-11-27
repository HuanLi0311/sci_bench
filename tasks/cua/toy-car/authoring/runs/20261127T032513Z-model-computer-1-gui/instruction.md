You are working in a Blender 4.2 desktop session. `/app/materials` holds the
toy-car pack; `/app/out` is where you deliver.

## What you are given

- `materials/videos/front.mp4`, `materials/videos/side.mp4` — a 3 s turntable
  from each view (frame grabs in `materials/frames/`).
- `materials/tables/car_sizes.xlsx` — length 380, width 160, wheelbase 240,
  wheel diameter 60 mm, ride height 32, steer 30°, doors 75°.
- `materials/drawings/joint_spec.pdf` — the rig rules and materials.
- `materials/silhouettes/` — front, side, back and top silhouette plates.
- `materials/photos/` — the four orthographic reference renders.

## What to build

Model the car in metres, front facing +X.

1. `body`, `chassis`, and four wheels `wheel_fl`, `wheel_fr`, `wheel_rl`,
   `wheel_rr`; wheelbase 240 mm, wheel diameter 60 mm, axles parallel and level.
2. Each wheel sits on a hub empty that spins about the axle; the front pair
   sits on `steer_fl` / `steer_fr` pivots that yaw ±30°. Spinning or steering a
   wheel must not move the body.
3. Doors `door_l` and `door_r` open 0–75° about a vertical hinge at the door's
   front edge, without passing through the body at 0/25/50/75°.
4. Materials: matte red plastic body, dark chassis, semi-transparent glass,
   rubber tyres. Textures packed.
5. At most 150k triangles.

## What to deliver in /app/out

| File | Camera | Resolution |
|---|---|---|
| `toy_car.blend` | — | — |
| `render_front.png` | `cam_front`, orthographic | 1200 × 1200 |
| `render_side.png` | `cam_side`, orthographic | 1200 × 1200 |
| `render_back.png` | `cam_back`, orthographic | 1200 × 1200 |
| `render_top.png` | `cam_top`, orthographic | 1200 × 1200 |
| `manifest.json` | — | — |

Cycles CPU, 64 samples, denoise on, white background. The four cameras stay in
the file under those names.

`manifest.json` lists every asset with a source and a licence.

## How it is checked

The file must reopen; all parts present; wheelbase 240 ±3 mm; wheel diameter
60 ±2 mm; axles level and parallel within 2 mm; spinning a wheel leaves the
body exactly in place; front wheels have steering pivots; doors hinge at the
front edge with no body penetration at 0/25/50/75°; four 1200 × 1200 renders
from the named cameras; silhouette IoU ≥ 0.75 against the supplied plates;
textures packed; manifest complete.

Anti-cheat: the side camera is re-rendered, then all four wheels are spun 90°
and the front pair steered 25°. The first render must match your
`render_side.png` (SSIM ≥ 0.90) and the second must differ (SSIM ≤ 0.995).

Each delivered view/state is independently re-rendered from its specified
camera. It must match in every RGB channel (SSIM >= 0.90) and in image
structure (relative RGB gradient error after a 2-pixel Gaussian blur <= 0.60).
Agreement on a large uniform background alone is insufficient. Compositing
or a video sequence cannot substitute for the delivered 3D scene.

You have 7200 seconds to complete this task.
