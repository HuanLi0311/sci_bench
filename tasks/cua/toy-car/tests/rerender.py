"""Anti-cheat: side view before and after spinning one wheel 90 degrees."""
import math
import sys
import os

import bpy


SPECS = [('front', 'cam_front', 960, 960, None), ('side', 'cam_side', 960, 960, None), ('back', 'cam_back', 960, 960, None), ('top', 'cam_top', 960, 960, None)]

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
    base_png, spun_png = argv[0], argv[1]
    render_deliveries(os.path.dirname(argv[0]))
    sc = bpy.context.scene
    cam = bpy.data.objects.get("cam_side")
    if cam is None:
        cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
        cam = cams[0] if cams else None
    sc.camera = cam
    sc.render.resolution_x = 960
    sc.render.resolution_y = 960
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0

    sc.render.filepath = base_png
    bpy.ops.render.render(write_still=True)

    for name in ("wheel_fl", "wheel_fr", "wheel_rl", "wheel_rr"):
        w = bpy.data.objects.get(name)
        hub = w.parent if w is not None else None
        if hub is not None:
            hub.rotation_mode = 'XYZ'
            hub.rotation_euler = (0, math.radians(90), 0)
    for name in ("steer_fl", "steer_fr"):
        st = bpy.data.objects.get(name)
        if st is not None:
            st.rotation_mode = 'XYZ'
            st.rotation_euler = (0, 0, math.radians(25))
    bpy.context.view_layer.update()

    sc.render.filepath = spun_png
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
