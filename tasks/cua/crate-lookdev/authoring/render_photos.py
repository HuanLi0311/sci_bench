"""Authoring tool: renders the four 'reference photos' shipped in materials/.

    blender -b solution/crate.blend -P authoring/render_photos.py -- <photos_dir>

Uses the reference crate itself so the photo pack, the drawing and the
deliverable all describe one object.
"""
import math
import os
import sys

import bpy
from mathutils import Vector


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def cam(name, loc, target, lens=50):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    bpy.context.collection.objects.link(ob)
    look_at(ob, target)
    return ob


def main():
    out = sys.argv[sys.argv.index("--") + 1]
    os.makedirs(out, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 92

    shots = {
        "ref_front34": ((1.25, -1.05, 0.75), (0, 0, 0.30), 45),
        "ref_back34": ((-1.05, 1.25, 0.80), (0, 0, 0.30), 45),
        "ref_top": ((0.0, 0.02, 2.6), (0, 0, 0.30), 55),
        "ref_corner": ((0.62, -0.52, 0.66), (0.40, -0.30, 0.55), 85),
    }
    for name, (loc, tgt, lens) in shots.items():
        c = cam(name, loc, tgt, lens)
        sc.camera = c
        sc.render.filepath = os.path.join(out, name + ".jpg")
        bpy.ops.render.render(write_still=True)
        print("[photos] wrote", name, flush=True)


if __name__ == "__main__":
    main()
