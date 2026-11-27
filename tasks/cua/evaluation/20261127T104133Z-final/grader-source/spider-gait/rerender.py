"""Anti-cheat re-render for spider-gait.

    blender -b <copy.blend> --python rerender.py -- <work_dir>

Renders the five delivered views from the submitted scene, then renders the
same side camera at frame 7. Frame 7 is the submitted cycle six frames out of
phase, so the two must differ if the action is real animation rather than a
still pose.
"""
import os
import sys

import bpy

SPECS = [
    ("render_pose_01.png", "cam_side", 960, 540, 1),
    ("render_pose_02.png", "cam_side", 960, 540, 10),
    ("render_pose_03.png", "cam_side", 960, 540, 18),
    ("render_pose_04.png", "cam_side", 960, 540, 21),
    ("render_top.png", "cam_top", 960, 960, 1),
]
SHIFT_FRAME = 7


def setup():
    sc = bpy.context.scene
    sc.use_nodes = False
    sc.render.use_sequencer = False
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.frame_start = 1
    sc.frame_end = 24


def camera(name):
    cam = bpy.data.objects.get(name)
    if cam is not None and cam.type == 'CAMERA':
        return cam
    cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
    return cams[0] if cams else None


def shot(sc, cam_name, frame, path, width, height):
    cam = camera(cam_name)
    if cam is None:
        return False
    sc.camera = cam
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.frame_set(frame)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return os.path.exists(path)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    work = argv[0]
    os.makedirs(work, exist_ok=True)
    setup()
    sc = bpy.context.scene
    for name, cam, width, height, frame in SPECS:
        shot(sc, cam, frame, os.path.join(work, name), width, height)
    shot(sc, "cam_side", SHIFT_FRAME, os.path.join(work, "ac_shift.png"), 960, 540)


if __name__ == "__main__":
    main()
