"""Anti-cheat re-render for skateboard-prop.

    blender -b <copy.blend> --python rerender.py -- <work_dir>

Renders the three delivered views, then re-renders with (a) the deck artwork
replaced by a checkerboard and (b) the deck mesh lifted 60 mm off its trucks.
Both must change their image if the delivered renders came from this scene and
the deck is real geometry.
"""
import os
import sys

import bpy
import numpy as np

VIEWS = [
    ("render_three_quarter.png", "cam_three_quarter", 1600, 1200),
    ("render_bottom.png", "cam_bottom", 1600, 900),
    ("render_edge.png", "cam_edge", 1600, 1200),
]


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


def camera(name):
    cam = bpy.data.objects.get(name)
    if cam is not None and cam.type == 'CAMERA':
        return cam
    cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
    return cams[0] if cams else None


def shot(cam_name, path, width, height):
    sc = bpy.context.scene
    cam = camera(cam_name)
    if cam is None:
        return
    sc.camera = cam
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def checker_image(img):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    tile = max(16, w // 32)
    board = (((xx // tile) + (yy // tile)) % 2).astype(np.float32)
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    rgba[..., 0] = board * 0.9 + 0.05
    rgba[..., 1] = (1.0 - board) * 0.85 + 0.05
    rgba[..., 2] = 0.1
    rgba[..., 3] = 1.0
    img.pixels.foreach_set(rgba.ravel())


def lift_deck(dz):
    """Move the deck mesh up while the trucks and wheels stay put.

    A deck that is only a picture fails this: the render cannot change.
    """
    ob = bpy.data.objects.get("deck")
    if ob is None or ob.type != 'MESH':
        return
    me = ob.data
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    co[:, 2] += dz
    me.vertices.foreach_set("co", co.ravel())
    me.update()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    work = argv[0]
    os.makedirs(work, exist_ok=True)
    setup()
    for name, cam, w, h in VIEWS:
        shot(cam, os.path.join(work, name), w, h)

    img = bpy.data.images.get("deck_graphic")
    if img is None:
        graph = next((i for i in bpy.data.images
                      if i.name not in ("Render Result", "Viewer Node")), None)
        img = graph
    if img is not None:
        checker_image(img)
        shot("cam_bottom", os.path.join(work, "ac_graphic.png"), 1600, 900)

    lift_deck(0.060)
    shot("cam_three_quarter", os.path.join(work, "ac_decklift.png"), 1600, 1200)


if __name__ == "__main__":
    main()
