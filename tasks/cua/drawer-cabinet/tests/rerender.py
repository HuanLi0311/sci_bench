"""Anti-cheat re-render for drawer-cabinet.

    blender -b <copy.blend> --python rerender.py -- <work_dir>

Rebuilds the three canonical poses (day / night / detail), then renders two
mutations: the night view with the day lights switched on, and the detail view
with drawer_02 pulled 150 mm instead of 300 mm.
"""
import os
import sys

import bpy


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


def set_lights(day_on, night_on):
    for name, on in (("light_day", day_on), ("light_night", night_on)):
        collection = bpy.data.collections.get(name)
        if collection is None:
            continue
        collection.hide_render = not on
        for ob in collection.objects:
            ob.hide_render = not on


def set_pose(drawer=None, amount=0.0, door_deg=0.0):
    for i in range(1, 6):
        slide = bpy.data.objects.get(f"slide_{i:02d}")
        if slide is not None:
            slide.location.y = 0.0
    if drawer is not None:
        slide = bpy.data.objects.get(f"slide_{drawer:02d}")
        if slide is not None:
            slide.location.y = amount
    hinge = bpy.data.objects.get("hinge_right")
    if hinge is not None:
        hinge.rotation_mode = 'XYZ'
        hinge.rotation_euler = (0.0, 0.0, -door_deg * 3.141592653589793 / 180.0)
    bpy.context.view_layer.update()


def shot(cam_name, path, width, height):
    sc = bpy.context.scene
    cam = bpy.data.objects.get(cam_name)
    if cam is None or cam.type != 'CAMERA':
        cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
        cam = cams[0] if cams else None
    if cam is None:
        return
    sc.camera = cam
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    work = argv[0]
    os.makedirs(work, exist_ok=True)
    setup()

    set_pose()
    set_lights(True, False)
    shot("cam_front34", os.path.join(work, "render_day.png"), 800, 600)

    set_pose()
    set_lights(False, True)
    shot("cam_front34", os.path.join(work, "render_night.png"), 800, 600)
    # mutation: same night camera, but the day lights are on as well
    set_lights(True, True)
    shot("cam_front34", os.path.join(work, "ac_lights.png"), 800, 600)

    set_pose(drawer=2, amount=0.300)
    set_lights(True, False)
    shot("cam_detail", os.path.join(work, "render_detail.png"), 800, 600)
    # mutation: the same drawer pulled 150 mm
    set_pose(drawer=2, amount=0.150)
    shot("cam_detail", os.path.join(work, "ac_drawer.png"), 800, 600)


if __name__ == "__main__":
    main()
