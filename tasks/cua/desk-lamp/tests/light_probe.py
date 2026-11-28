"""Measure how much the lamp lights the target patch.

    blender -b <file.blend> --python light_probe.py -- <out.json>

Renders frame 2 twice at 640x480 - lamp on, lamp off - projects the frame-2
target onto the camera plane, and reports the mean luminance of a square patch
around it in both images. grade.py turns that into a ratio; nothing here
decides pass or fail.
"""
import json
import os
import sys

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

TARGET = (-0.280, 0.320, 0.340)
PATCH = 61
FRAME = 2


def setup():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0
    sc.render.resolution_x = 640
    sc.render.resolution_y = 480
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'


def shot(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    return px


def patch_mean(px, cx, cy):
    h, w, _ = px.shape
    half = PATCH // 2
    x0, x1 = max(0, cx - half), min(w, cx + half + 1)
    y0, y1 = max(0, cy - half), min(h, cy + half + 1)
    if x1 <= x0 or y1 <= y0:
        return None
    return float(px[y0:y1, x0:x1].mean())


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out = argv[0]
    work = os.path.dirname(out) or "/tmp"
    setup()
    sc = bpy.context.scene
    sc.frame_set(FRAME)
    bpy.context.view_layer.update()

    cam = bpy.data.objects.get("cam_pose")
    cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
    cam = cam if cam is not None and cam.type == 'CAMERA' else (cams[0] if cams else None)
    report = {"ok": False}
    if cam is None:
        with open(out, "w") as fh:
            json.dump(report, fh)
        return
    sc.camera = cam

    co = world_to_camera_view(sc, cam, Vector(TARGET))
    w = sc.render.resolution_x
    h = sc.render.resolution_y
    cx, cy = int(round(co.x * w)), int(round((1.0 - co.y) * h))
    report["target_px"] = [cx, cy]
    report["target_in_frame"] = bool(0.0 <= co.x <= 1.0 and 0.0 <= co.y <= 1.0
                                     and co.z > 0)

    light = bpy.data.objects.get("lamp_spot")
    report["lamp_present"] = light is not None and light.type == 'LIGHT'
    if light is not None:
        report["lamp_type"] = light.data.type
        report["lamp_energy"] = float(light.data.energy)
        report["lamp_parent"] = light.parent.name if light.parent else None
        report["lamp_world"] = [round(c, 4) for c in light.matrix_world.translation]
        axis = (light.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
        report["lamp_direction"] = [round(c, 4) for c in axis]
        report["lamp_hits_down"] = bool(axis.z < -0.3)

    if light is not None:
        light.hide_render = False
        on = shot(os.path.join(work, "probe_on.png"))
        light.hide_render = True
        off = shot(os.path.join(work, "probe_off.png"))
        light.hide_render = False
        on_patch = patch_mean(on, cx, cy)
        off_patch = patch_mean(off, cx, cy)
        report["on_patch"] = on_patch
        report["off_patch"] = off_patch
        if on_patch is not None and off_patch is not None and off_patch > 1e-6:
            report["ratio"] = round(on_patch / off_patch, 4)
        report["ok"] = True

    with open(out, "w") as fh:
        json.dump(report, fh, indent=1)
    print("[probe]", json.dumps(report))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/probe.json"
        with open(out, "w") as fh:
            json.dump({"ok": False, "error": "see stderr"}, fh)
        sys.exit(2)
