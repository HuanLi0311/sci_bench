"""Authoring tool: renders the four reference photographs for the booth pack."""
import os
import sys

import bpy
from mathutils import Vector


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def cam(name, loc, target, lens=35):
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
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 92
    shots = {
        "ref_overview": ((-1.4, 0.2, 1.65), (1.6, 0, 1.0), 28),
        "ref_products": ((1.2, -0.6, 1.3), (2.2, 0.0, 0.55), 50),
        "ref_counter": ((-1.2, -0.4, 1.4), (-2.0, -1.5, 0.6), 40),
        "ref_corner": ((1.4, 1.2, 2.6), (2.6, -1.6, 1.2), 35),
    }
    for name, (loc, tgt, lens) in shots.items():
        sc.camera = cam(name, loc, tgt, lens)
        sc.render.filepath = os.path.join(out, name + ".jpg")
        bpy.ops.render.render(write_still=True)
        print("[photos]", name, flush=True)


if __name__ == "__main__":
    main()
