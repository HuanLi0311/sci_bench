You are working in a Blender 4.2 desktop session. `/app/materials` holds the
design pack for an exhibition booth; `/app/out` is where you deliver.

## What you are given

- `materials/drawings/booth_floor_plan.png` (and `.pdf`) — 6.0 × 4.0 m booth,
  entrance, corner column, hydrant position, 1:50.
- `materials/drawings/constraints.pdf` — clearance, sight-line and budget rules.
- `materials/tables/product_sizes.xlsx` — three power stations, millimetres.
- `materials/tables/furniture_list.xlsx` — cabinets, counter, plinths.
- `materials/brand/brand_sheet.pdf`, `logo.svg`, `logo.png` — colours and mark.
- `materials/photos/` — four reference photographs of the booth.

## What to build

Model the booth in metres and keep it editable.

1. `booth_shell`: floor, two side walls, back wall and the entrance wall with a
   2.4 m opening centred on the 4 m side. Footprint 6.0 × 4.0 m, walls 4.0 m high.
2. `counter` (1.8 × 0.6 × 1.0), `cabinet_01` and `cabinet_02`
   (1.2 × 0.5 × 2.0), three plinths (0.8 × 0.8 × 0.4) and `product_01`,
   `product_02`, `product_03` from the size table, standing on the plinths.
3. `entrance_zone`: a marker for the 2.4 m opening, at the entrance.
4. `lighting`: the light rig (an empty named `lighting` with the lights parented,
   or a light object of that name).
5. Brand colours: `#1F6F5C` on the back wall, `#F2C14E` on secondary surfaces.
   The logo goes on the back wall as a packed texture.
6. Constraints: cabinets at least 0.9 m clear of `entrance_zone`; nothing within
   1.2 m of the hydrant at (-4.2, 0); all three products visible from the
   entrance camera with no occlusion; at most 300k triangles.
7. Everything inside the 6 × 4 × 4 m envelope. Textures packed, no absolute
   paths.

## What to deliver in /app/out

| File | Camera | Resolution |
|---|---|---|
| `booth.blend` | — | — |
| `render_entrance.png` | `cam_entrance`: 1.5 m inside the entrance, 1.6 m high, 35 mm, facing the booth centre | 1920 × 1080 |
| `render_top.png` | `cam_top`: orthographic, covering the whole 6 × 4 m footprint | 2048 × 1536 |
| `manifest.json` | — | — |

Cycles CPU, 64 samples, denoise on, fixed seed. Both cameras stay in the file
under those exact names.

`manifest.json` lists every asset with source and licence, e.g.

```json
{"schemaVersion": 1, "units": "meters", "blenderVersion": "4.2.3",
 "assets": [{"path": "brand/logo.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""}],
 "renders": [{"file": "render_entrance.png", "camera": "cam_entrance",
              "resolution": [1920, 1080], "samples": 64}]}
```

## How it is checked

The file must reopen; the named objects must exist; footprint 6.0 × 4.0 m
±0.02 m with walls within the 4 m limit; everything inside the envelope;
cabinet clearance ≥ 0.9 m; hydrant clearance ≥ 1.2 m; all three products
unoccluded from the entrance camera; back wall within 2/255 of the brand
colour; every mesh has a material; textures packed and free of absolute paths;
≤ 300k triangles; both renders at the stated size from the stated cameras; a
manifest covering the assets.

Anti-cheat: the scene is re-rendered from `cam_entrance` and compared with your
`render_entrance.png` (must match, SSIM ≥ 0.90), then `cabinet_01` is moved
0.5 m and rendered again (the image must change, SSIM ≤ 0.98).

Both delivered images are independently re-rendered from their named cameras
and compared per RGB channel (SSIM >= 0.90). Their image structure must also
match: relative RGB gradient error after a 2-pixel Gaussian blur <= 0.60.
Uniform-background agreement alone is insufficient. The entrance marker must remain at
the specified entrance; moving it does not redefine the clearance zone.
Furniture, plinth and product sizes are checked against the supplied tables
within 20 mm, allowing rotation in the floor plan. Each product must stand on
its corresponding plinth, within 20 mm vertically and within its footprint.
The brand-colour check measures materials actually used on the inward-facing
back wall; an unused material slot does not count.
Colours are compared in sRGB (the space used by the hexadecimal values), with
Blender's linear shader values converted before comparison. Secondary
`#F2C14E` must also be assigned to an actual geometry surface; an unused yellow
material or unused slot does not count.

`entrance_zone` is an auxiliary marker and may be either an Empty or a mesh.
The marker identifies the specified entrance; its display size does not alter
the required clear zone. Cabinet clearance is measured from the fixed vertical
opening plane at x=-3 m, -1.2 <= y <= 1.2 m. The actual shell must have the
2.4 m opening (checked at z=1 m), with wall on both sides. Product visibility
requires the product centres to lie inside the entrance camera's frame as well
as have unobstructed sight lines.

The entrance camera must face the booth centre (direction cosine >= 0.95).
The secondary brand colour must occupy a face of at least 0.02 square metres
on the counter or a plinth, visible to an entrance or top camera ray.

You have 7200 seconds to complete this task.
