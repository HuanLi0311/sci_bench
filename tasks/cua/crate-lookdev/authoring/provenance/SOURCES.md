# Provenance

Everything shipped in this task was authored for it. There are no third-party
assets, so nothing here has an external licence to honour.

| Artefact | Origin | Licence |
|---|---|---|
| `environment/materials/drawings/crate_three_views.png/.pdf` | `authoring/make_materials.py`, matplotlib | CC0-1.0 |
| `environment/materials/spec/material_spec.pdf` | `authoring/make_materials.py`, reportlab | CC0-1.0 |
| `environment/materials/hdri/studio_soft.hdr` | `authoring/make_materials.py`, procedural RGBE equirect (1024×512) | CC0-1.0 |
| `environment/materials/photos/*.jpg` | rendered from the reference crate by `authoring/render_photos.py` | CC0-1.0 |
| `environment/materials/LICENSE.txt` | written for this task | CC0-1.0 |
| `solution/crate.blend`, `solution/textures/*`, `solution/render_*.png` | `authoring/build_crate.py`, procedural numpy maps baked to 2048² PNG | CC0-1.0 |
| `solution/manifest.json` | `authoring/build_crate.py` | CC0-1.0 |

## Reproducing the reference

```
docker build -t cua-crate-env:dev environment
docker run --rm -v "$PWD":/task cua-crate-env:dev \
    blender -b -P /task/authoring/build_crate.py -- /task/solution /task/environment/materials
docker run --rm -v "$PWD":/task cua-crate-env:dev \
    blender -b /task/solution/crate.blend -P /task/authoring/render_photos.py \
    -- /task/environment/materials/photos
```

The material pack is regenerated with
`python3 authoring/make_materials.py environment/materials`
(matplotlib, reportlab, numpy).

## Base image

`blender-bench:gui` is the local Blender desktop image: Ubuntu 24.04, Blender
4.2.3 LTS from the official linux-x64 tarball at `/opt/blender`, Xvfb + XFCE +
x11vnc + xdotool, an entrypoint that brings the desktop up on `:1`. Its recipe
is recorded in `authoring/base-image.md`. The official tarball host
(`download.blender.org`) and its mirrors are blocked from this network, which is
why the task builds on the local image rather than downloading Blender itself.
