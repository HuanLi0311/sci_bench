# Provenance

Everything shipped here was authored for this task; no third-party assets.

| Artefact | Origin | Licence |
|---|---|---|
| `materials/drawings/booth_floor_plan.png/.pdf` | `authoring/make_booth_materials.py` (matplotlib) | CC0-1.0 |
| `materials/drawings/constraints.pdf` | same (reportlab) | CC0-1.0 |
| `materials/tables/*.xlsx` | same (openpyxl) | CC0-1.0 |
| `materials/brand/brand_sheet.pdf`, `logo.svg`, `logo.png` | same | CC0-1.0 |
| `materials/photos/*.jpg` | rendered from the reference booth by `authoring/render_photos.py` | CC0-1.0 |
| `solution/booth.blend`, renders | `authoring/build_booth.py` | CC0-1.0 |

Rebuild:

```
python3 authoring/make_booth_materials.py environment/materials
docker run --rm -v "$PWD":/task cua-crate-env:dev \
    blender -b -P /task/authoring/build_booth.py -- /task/solution /task/environment/materials
docker run --rm -v "$PWD":/task cua-crate-env:dev \
    blender -b /task/solution/booth.blend -P /task/authoring/render_photos.py \
    -- /task/environment/materials/photos
```
