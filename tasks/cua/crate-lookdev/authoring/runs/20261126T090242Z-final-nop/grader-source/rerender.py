"""Anti-cheat re-render.

    blender -b <copy.blend> --python rerender.py -- <base.png> <lid_open.png>

Renders cam_front twice at 960x540: once as delivered, once with the lid hinge
rotated to 60 degrees. If the delivered render_front.png really came from this
scene, the first pass matches it and the second pass does not.
"""
import math
import sys
import os

import bpy


SPECS = [('front', 'cam_front', 960, 720, None), ('back', 'cam_back', 960, 720, None), ('top', 'cam_top', 960, 768, None), ('macro', 'cam_macro', 960, 720, None)]

def render_deliveries(directory):
    sc = bpy.context.scene
    # Prevent a compositor or video sequence from substituting the 3D scene.
    sc.use_nodes = False
    sc.render.use_sequencer = False
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    for view, camera, width, height, frame in SPECS:
        sc.camera = bpy.data.objects[camera]
        sc.render.resolution_x, sc.render.resolution_y = width, height
        if frame is not None:
            sc.frame_set(frame)
        sc.render.filepath = os.path.join(directory, "render_" + view + ".png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    base_png, lid_png = argv[0], argv[1]

    render_deliveries(os.path.dirname(argv[0]))
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
