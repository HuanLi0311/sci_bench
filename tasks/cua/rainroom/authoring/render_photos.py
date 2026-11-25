"""Render four reference photographs for the rainroom pack."""
import os
import sys

import bpy


def set_hide(night_hidden, morning_hidden):
    for name, hide in (("light_night", night_hidden), ("light_morning", morning_hidden)):
        c = bpy.data.collections.get(name)
        if c:
            c.hide_render = hide


def main():
    out = sys.argv[sys.argv.index("--") + 1]
    os.makedirs(out, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 900
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 92
    shots = [("ref_night", 0), ("ref_morning", 1)]
    for name, morning in shots:
        set_hide(bool(morning), not bool(morning))
        sc.render.filepath = os.path.join(out, name + ".jpg")
        bpy.ops.render.render(write_still=True)
        print("[photos]", name, flush=True)
    # detail: close-up of the window and table while the morning lights are on
    set_hide(True, False)
    cd = bpy.data.cameras.new("ref_detail")
    cd.lens = 60
    cam = bpy.data.objects.new("ref_detail", cd)
    cam.location = (0.4, -0.7, 1.35)
    from mathutils import Vector
    d = Vector((1.4, 0.6, 1.5)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    sc.render.filepath = os.path.join(out, "ref_detail.jpg")
    bpy.ops.render.render(write_still=True)
    print("[photos] detail", flush=True)


if __name__ == "__main__":
    main()
