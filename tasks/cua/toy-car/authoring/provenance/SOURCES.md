# Provenance

All artefacts authored here, CC0-1.0. The videos, extracted frames, silhouettes
and photographs are rendered from `solution/toy_car.blend`.

Deviation from the batch spec: videos are 3 s at 640x360 rather than 6 s at
1280x720, because the whole pack is rendered on CPU inside the task image.
Frames are extracted every ~0.41 s.

```
bash authoring/extract_frames.sh          # inside the container (ffmpeg)
/tmp/av2/bin/python authoring/make_silhouettes.py solution environment/materials/silhouettes
/tmp/av2/bin/python authoring/make_car_materials.py environment/materials
```
