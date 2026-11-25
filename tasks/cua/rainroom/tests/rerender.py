"""Anti-cheat: render the night camera with `light_night` on and off."""
import sys

import bpy


def set_coll(name, hide):
    c = bpy.data.collections.get(name)
    if c is not None:
        c.hide_render = hide


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    on_png, off_png = argv[0], argv[1]
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
    sc.cycles.samples = 64
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
