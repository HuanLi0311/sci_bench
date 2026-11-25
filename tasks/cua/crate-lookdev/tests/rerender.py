"""Anti-cheat re-render.

    blender -b <copy.blend> --python rerender.py -- <base.png> <lid_open.png>

Renders cam_front twice at 960x540: once as delivered, once with the lid hinge
rotated to 60 degrees. If the delivered render_front.png really came from this
scene, the first pass matches it and the second pass does not.
"""
import math
import sys

import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    base_png, lid_png = argv[0], argv[1]

    sc = bpy.context.scene
    cam = bpy.data.objects.get("cam_front")
    if cam is None:
        cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
        cam = cams[0] if cams else None
    sc.camera = cam
    sc.render.resolution_x = 960
    sc.render.resolution_y = 540
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0

    sc.render.filepath = base_png
    bpy.ops.render.render(write_still=True)

    lid = bpy.data.objects.get("crate_lid")
    hinge = lid.parent if lid is not None else None
    if hinge is not None:
        hinge.rotation_mode = 'XYZ'
        hinge.rotation_euler[0] = math.radians(60)
    elif lid is not None:
        lid.rotation_mode = 'XYZ'
        lid.rotation_euler[0] = math.radians(60)
    bpy.context.view_layer.update()

    sc.render.filepath = lid_png
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
