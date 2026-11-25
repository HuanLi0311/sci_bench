# Provenance

All artefacts authored here, CC0-1.0; the photographs are renders of
`solution/rainroom.blend`.

Deviation: the batch spec asked for four photographs; the pack ships three
(night, morning, detail) because they are enough to read the palette and the
window treatment.

```
/tmp/av2/bin/python authoring/make_rainroom_materials.py environment/materials
docker run --rm -v "$PWD":/task cua-crate-env:dev \
    blender -b /task/solution/rainroom.blend -P /task/authoring/render_photos.py \
    -- /task/environment/materials/photos
```
