"""Anti-cheat re-render for the booth.

    blender -b <copy.blend> --python rerender.py -- <base.png> <moved.png>

Renders cam_entrance twice at 960x540: once as delivered, once with cabinet_01
shifted 0.5 m along X. A real cabinet changes the picture; a painted backdrop
does not.
"""
import sys

import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    base_png, moved_png = argv[0], argv[1]

    sc = bpy.context.scene
    cam = bpy.data.objects.get("cam_entrance")
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

    cab = bpy.data.objects.get("cabinet_01")
    if cab is not None:
        cab.location.x += 0.5
    bpy.context.view_layer.update()

    sc.render.filepath = moved_png
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
