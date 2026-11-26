"""Anti-cheat re-render for the booth.

    blender -b <copy.blend> --python rerender.py -- <base.png> <moved.png>

Renders cam_entrance twice at 960x540: once as delivered, once with cabinet_01
shifted 0.5 m along X. A real cabinet changes the picture; a painted backdrop
does not.
"""
import sys
import os

import bpy


SPECS = [('entrance', 'cam_entrance', 960, 540, None), ('top', 'cam_top', 960, 720, None)]

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
    base_png, moved_png = argv[0], argv[1]

    render_deliveries(os.path.dirname(argv[0]))
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
        cab.location.y += 0.5
    bpy.context.view_layer.update()

    sc.render.filepath = moved_png
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
