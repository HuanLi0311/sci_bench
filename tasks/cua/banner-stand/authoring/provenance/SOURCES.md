# Provenance

Everything shipped in this task was authored for it.

| Artefact | Origin | Licence |
|---|---|---|
| `environment/materials/drawings/banner_three_views.png` | `authoring/make_materials.py`, drawn from the build dimensions | CC0-1.0 |
| `environment/materials/spec/banner_spec.pdf`, `parts.{csv,xlsx}` | `authoring/make_materials.py` | CC0-1.0 |
| `environment/materials/photos/ref_*.png` | rendered from the reference by `authoring/build_banner.py` | CC0-1.0 |
| `environment/materials/LICENSE.txt` | written for this task | CC0-1.0 |
| `solution/banner_stand.blend`, `solution/textures/banner_graphic.png`, `solution/render_*.png` | `authoring/build_banner.py` | CC0-1.0 |
| `solution/manifest.json` | `authoring/build_banner.py` | CC0-1.0 |

## Reproducing the reference

```
docker build -t cua-qc-banner-stand-env environment
docker run --rm -v "$PWD":/task -w /task cua-qc-banner-stand-env \
    blender -b -P authoring/build_banner.py -- /task/solution /task/environment/materials
docker run --rm -v "$PWD":/task -w /task cua-qc-banner-stand-env \
    blender -b -P authoring/make_materials.py -- /task/environment/materials /task/solution
```

## Base image

`blender-bench:gui` is the local Blender desktop image (Ubuntu 24.04 + Blender
4.2.3 LTS at `/opt/blender`, Xvfb/XFCE/x11vnc, desktop on `:1`). `vendor/codex`
matches the sibling CUA tasks; the public registry does not serve the platform
package from this network.
