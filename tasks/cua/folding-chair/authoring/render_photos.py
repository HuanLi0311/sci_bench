"""Render the six reference photographs for the chair pack."""
import os
import sys

import bpy
from mathutils import Vector


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def main():
    out = sys.argv[sys.argv.index("--") + 1]
    os.makedirs(out, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 1200
    sc.render.image_settings.file_format = 'JPEG'
    sc.camera = bpy.data.objects["cam_states"]
    shots = [("ref_unfolded", 0), ("ref_half", 20), ("ref_folded", 60),
             ("ref_locked", 0)]
    for name, frame in shots:
        sc.frame_set(frame)
        pin = bpy.data.objects.get("lock_pin")
        if pin:
            pin.hide_render = name != "ref_locked"
        sc.render.filepath = os.path.join(out, name + ".jpg")
        bpy.ops.render.render(write_still=True)
        print("[photos]", name, flush=True)
    # hinge close-up
    cd = bpy.data.cameras.new("ref_hinge")
    cd.lens = 100
    cam = bpy.data.objects.new("ref_hinge", cd)
    cam.location = (-0.55, -0.45, 0.45)
    bpy.context.collection.objects.link(cam)
    look_at(cam, (-0.28, 0, 0.225))
    sc.camera = cam
    sc.frame_set(0)
    sc.render.filepath = os.path.join(out, "ref_hinge.jpg")
    bpy.ops.render.render(write_still=True)
    print("[photos] hinge", flush=True)


if __name__ == "__main__":
    main()
