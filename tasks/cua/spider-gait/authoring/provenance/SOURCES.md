# Provenance

Everything shipped in this task was authored for it. There are no third-party
assets, so nothing here has an external licence to honour.

| Artefact | Origin | Licence |
|---|---|---|
| `environment/materials/drawings/spider_three_views.png` | `authoring/make_materials.py`, drawn from `authoring/spider_spec.py` | CC0-1.0 |
| `environment/materials/spec/bone_spec.{csv,xlsx}` | `authoring/make_materials.py`, from the same bone table | CC0-1.0 |
| `environment/materials/spec/gait_timing.csv`, `gait_phase.png` | `authoring/make_materials.py`, from the same phase table | CC0-1.0 |
| `environment/materials/spec/spider_spec.pdf` | `authoring/make_materials.py`, hand-written PDF | CC0-1.0 |
| `environment/materials/poses/key_pose_01..04.png` | rendered from the reference by `authoring/build_spider.py` | CC0-1.0 |
| `environment/materials/textures/chitin_basecolor.png` | `authoring/make_materials.py`, procedural numpy pattern | CC0-1.0 |
| `environment/materials/LICENSE.txt` | written for this task | CC0-1.0 |
| `solution/spider.blend`, `solution/textures/*`, `solution/render_*.png` | `authoring/build_spider.py` | CC0-1.0 |
| `solution/manifest.json` | `authoring/build_spider.py` | CC0-1.0 |

## Reproducing the reference

```
docker build -t cua-qc-spider-gait-env environment
docker run --rm -v "$PWD":/task -w /task cua-qc-spider-gait-env \
    blender -b -P authoring/make_materials.py -- /task/environment/materials
docker run --rm -v "$PWD":/task -w /task cua-qc-spider-gait-env \
    blender -b -P authoring/build_spider.py -- /task/solution /task/environment/materials
docker run --rm -v "$PWD":/task -w /task cua-qc-spider-gait-env \
    blender -b -P authoring/make_materials.py -- /task/environment/materials /task/solution
```

The last line copies the four reference key poses into `materials/poses/`.

## Base image

`blender-bench:gui` is the local Blender desktop image: Ubuntu 24.04, Blender
4.2.3 LTS at `/opt/blender`, Xvfb + XFCE + x11vnc + xdotool, an entrypoint that
brings the desktop up on `:1`. The official tarball host is blocked from this
network, which is why the task builds on the local image. `vendor/codex` is the
same 0.172.0 install the sibling CUA tasks ship, because `npm i -g
@openai/codex` cannot reach the platform package from here.
