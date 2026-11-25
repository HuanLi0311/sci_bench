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
    sc.render.resolution_y = 720
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0

    sc.render.filepath = base_png
    bpy.ops.render.render(write_still=True)

    lid = bpy.data.objects.get("crate_lid")
    hinge = lid.parent if lid is not None else None
    obj = hinge if hinge is not None else lid
    if obj is not None:
        obj.rotation_mode = 'XYZ'
        base = obj.rotation_euler[0]

        def centre_z():
            deps = bpy.context.evaluated_depsgraph_get()
            ev = lid.evaluated_get(deps)
            me = ev.to_mesh()
            mw = ev.matrix_world
            z = sum((mw @ v.co).z for v in me.vertices) / max(len(me.vertices), 1)
            ev.to_mesh_clear()
            return z

        z0 = centre_z()
        obj.rotation_euler[0] = base + math.radians(60)
        bpy.context.view_layer.update()
        z_pos = centre_z()
        obj.rotation_euler[0] = base - math.radians(60)
        bpy.context.view_layer.update()
        z_neg = centre_z()
        sign = 1 if z_pos > z_neg else -1
        obj.rotation_euler[0] = base + sign * math.radians(60)
        bpy.context.view_layer.update()

    sc.render.filepath = lid_png
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
