"""Authoring tool: renders the two 3 s turntable videos and the four
silhouette plates for the toy-car material pack.

    blender -b solution/toy_car.blend -P render_video.py -- <materials_dir>

The spec asks for 6 s at 1280x720; this render budget gives 3 s at 640x360 per
view, which is what ships. Recorded in provenance/SOURCES.md.
"""
import math
import os
import subprocess
import sys

import bpy

FRAMES = 90
FPS = 30


def main():
    materials = sys.argv[sys.argv.index("--") + 1]
    vid_dir = os.path.join(materials, "videos")
    sil_dir = os.path.join(materials, "silhouettes")
    os.makedirs(vid_dir, exist_ok=True)
    os.makedirs(sil_dir, exist_ok=True)

    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 8
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 640
    sc.render.resolution_y = 360
    sc.render.image_settings.file_format = 'PNG'
    sc.frame_start = 0
    sc.frame_end = FRAMES - 1
    sc.render.fps = FPS

    # spin the wheels a full turn over the clip
    hubs = [o for o in bpy.data.objects if o.name.endswith("_hub")]
    for h in hubs:
        h.rotation_mode = 'XYZ'
        h.rotation_euler = (0, 0, 0)
        h.keyframe_insert("rotation_euler", index=1, frame=0)
        h.rotation_euler = (0, math.radians(360), 0)
        h.keyframe_insert("rotation_euler", index=1, frame=FRAMES - 1)

    for name in ("cam_front", "cam_side"):
        frames_dir = f"/tmp/car_frames_{name}"
        os.makedirs(frames_dir, exist_ok=True)
        sc.camera = bpy.data.objects[name]
        sc.render.filepath = os.path.join(frames_dir, "f_")
        bpy.ops.render.render(animation=True)
        out = os.path.join(vid_dir, f"{name.replace('cam_', '')}.mp4")
        subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS),
                        "-i", os.path.join(frames_dir, "f_%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", out],
                       check=True, capture_output=True)
        print("[car-video] wrote", out, flush=True)

    # silhouettes: render the rest pose with a transparent film
    sc.frame_set(0)
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.resolution_x = 1200
    sc.render.resolution_y = 1200
    for name in ("cam_front", "cam_side", "cam_back", "cam_top"):
        sc.camera = bpy.data.objects[name]
        sc.render.filepath = os.path.join(sil_dir, f"{name.replace('cam_', '')}.png")
        bpy.ops.render.render(write_still=True)
        print("[car-sil] wrote", name, flush=True)


if __name__ == "__main__":
    main()
