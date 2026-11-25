# Provenance

All artefacts authored for this task, CC0-1.0.

| Artefact | Origin |
|---|---|
| `materials/drawings/hinge_layout.png/.pdf`, `states.pdf` | `authoring/make_chair_materials.py` |
| `materials/tables/*.xlsx` | same (openpyxl) |
| `materials/photos/*.jpg` | rendered from `solution/folding_chair.blend` by `authoring/render_photos.py` |
| `solution/folding_chair.blend`, renders | `authoring/build_chair.py` |

Rebuild:

```
/tmp/av2/bin/python authoring/make_chair_materials.py environment/materials
bash authoring/rebuild.sh          # build_chair.py + pose report
docker run --rm -v "$PWD":/task cua-crate-env:dev \
    blender -b /task/solution/folding_chair.blend -P /task/authoring/render_photos.py \
    -- /task/environment/materials/photos
```
