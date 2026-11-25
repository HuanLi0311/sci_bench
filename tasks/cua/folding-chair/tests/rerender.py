"""Anti-cheat re-render for the chair: frame 0 and frame 30, same camera."""
import sys

import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    f0_png, f30_png = argv[0], argv[1]
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
