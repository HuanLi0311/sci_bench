"""Anti-cheat re-render for banner-stand.

    blender -b <copy.blend> --python rerender.py -- <work_dir>

Rebuilds the three canonical poses from the scene, then renders two mutations:
the front view with the print replaced by a checkerboard, and the three-quarter
view with the rear leg at 25 degrees instead of 14.
"""
import os
import sys

import bpy
import numpy as np


def setup():
    sc = bpy.context.scene
    sc.use_nodes = False
    sc.render.use_sequencer = False
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'


def set_hinge(deg):
    hinge = bpy.data.objects.get("hinge_rear")
    if hinge is None:
        return
    hinge.rotation_mode = 'XYZ'
    hinge.rotation_euler = (deg * 3.141592653589793 / 180.0, 0.0, 0.0)
    bpy.context.view_layer.update()


def shot(cam, path, width, height):
    sc = bpy.context.scene
    ob = bpy.data.objects.get(cam)
    if ob is None or ob.type != 'CAMERA':
        cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
        ob = cams[0] if cams else None
    if ob is None:
        return
    sc.camera = ob
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def checker(img):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    tile = max(16, w // 24)
    board = (((xx // tile) + (yy // tile)) % 2).astype(np.float32)
    rgba = np.zeros((h, w, 4), np.float32)
    rgba[..., 0] = board * 0.9 + 0.05
    rgba[..., 1] = (1 - board) * 0.85 + 0.05
    rgba[..., 2] = 0.12
    rgba[..., 3] = 1.0
    img.pixels.foreach_set(rgba.ravel())


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    work = argv[0]
    os.makedirs(work, exist_ok=True)
    setup()

    set_hinge(14)
    shot("cam_front", os.path.join(work, "render_front.png"), 600, 800)
    shot("cam_three_quarter", os.path.join(work, "render_three_quarter.png"), 800, 600)
    set_hinge(0)
    shot("cam_folded", os.path.join(work, "render_folded.png"), 600, 800)

    img = bpy.data.images.get("banner_graphic")
    if img is None:
        img = next((i for i in bpy.data.images
                    if i.name not in ("Render Result", "Viewer Node")), None)
    if img is not None:
        checker(img)
        set_hinge(14)
        shot("cam_front", os.path.join(work, "ac_graphic.png"), 600, 800)

    set_hinge(25)
    shot("cam_three_quarter", os.path.join(work, "ac_hinge.png"), 800, 600)


if __name__ == "__main__":
    main()
