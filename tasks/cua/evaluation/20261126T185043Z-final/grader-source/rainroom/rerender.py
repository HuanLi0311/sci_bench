"""Anti-cheat: render the night camera with `light_night` on and off."""
import sys
import os

import bpy


def set_coll(name, hide):
    c = bpy.data.collections.get(name)
    if c is not None:
        c.hide_render = hide


SPECS = [('night', 'cam_room', 800, 450, None), ('morning', 'cam_room', 800, 450, None)]

def render_deliveries(directory):
    sc = bpy.context.scene
    # Prevent a compositor or video sequence from substituting the 3D scene.
    sc.use_nodes = False
    sc.render.use_sequencer = False
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 16
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    for view, camera, width, height, frame in SPECS:
        sc.camera = bpy.data.objects[camera]
        sc.render.resolution_x, sc.render.resolution_y = width, height
        if frame is not None:
            sc.frame_set(frame)
        bpy.data.collections["light_night"].hide_render = view != "night"
        bpy.data.collections["light_morning"].hide_render = view != "morning"
        sc.render.filepath = os.path.join(directory, "render_" + view + ".png")
        bpy.ops.render.render(write_still=True)
    bpy.data.collections["light_night"].hide_render = False
    bpy.data.collections["light_morning"].hide_render = True


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    on_png, off_png = argv[0], argv[1]
    render_deliveries(os.path.dirname(argv[0]))
    sc = bpy.context.scene
    cam = bpy.data.objects.get("cam_room")
    if cam is None:
        cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
        cam = cams[0] if cams else None
    sc.camera = cam
    sc.render.resolution_x = 800
    sc.render.resolution_y = 450
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.cycles.samples = 16
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0

    set_coll("light_morning", True)
    set_coll("light_night", False)
    sc.render.filepath = on_png
    bpy.ops.render.render(write_still=True)

    set_coll("light_night", True)
    sc.render.filepath = off_png
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
