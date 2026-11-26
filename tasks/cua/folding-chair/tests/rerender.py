"""Anti-cheat re-render for the chair: frame 0 and frame 30, same camera."""
import sys
import os

import bpy


SPECS = [('unfolded', 'cam_states', 960, 960, 0), ('half', 'cam_states', 960, 960, 20), ('folded', 'cam_states', 960, 960, 60), ('locked', 'cam_states', 960, 960, 0)]

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
        bpy.data.objects["lock_pin"].hide_render = view != "locked"
        sc.render.filepath = os.path.join(directory, "render_" + view + ".png")
        bpy.ops.render.render(write_still=True)
    sc.frame_set(0)
    bpy.data.objects["lock_pin"].hide_render = True


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    f0_png, f30_png = argv[0], argv[1]
    render_deliveries(os.path.dirname(argv[0]))
    sc = bpy.context.scene
    cam = bpy.data.objects.get("cam_states")
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

    for frame, path in ((0, f0_png), (30, f30_png)):
        sc.frame_set(frame)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
