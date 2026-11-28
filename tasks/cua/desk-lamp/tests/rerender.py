"""Anti-cheat re-render for desk-lamp.

    blender -b <copy.blend> --python rerender.py -- <work_dir>

Rebuilds the four delivered views from the scene, then renders pose 1 with the
yaw joint turned 25 degrees. A pose that is really keyed on the joint chain
changes; a still mesh with a keyed empty does not.
"""
import math
import os
import sys

import bpy

VIEWS = [
    ("render_pose_01.png", "cam_pose", 1600, 1200, 1),
    ("render_pose_02.png", "cam_pose", 1600, 1200, 2),
    ("render_pose_03.png", "cam_pose", 1600, 1200, 3),
    ("render_hero.png", "cam_hero", 1600, 1200, 1),
]


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


def shot(cam_name, path, width, height, frame):
    sc = bpy.context.scene
    cam = bpy.data.objects.get(cam_name)
    if cam is None or cam.type != 'CAMERA':
        cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
        cam = cams[0] if cams else None
    if cam is None:
        return
    sc.camera = cam
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.frame_set(frame)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    work = argv[0]
    os.makedirs(work, exist_ok=True)
    setup()
    for name, cam, w, h, frame in VIEWS:
        shot(cam, os.path.join(work, name), w, h, frame)

    yaw = bpy.data.objects.get("joint_yaw")
    if yaw is not None:
        if yaw.animation_data is not None:
            yaw.animation_data.action = None
        yaw.rotation_mode = 'XYZ'
        yaw.rotation_euler = (0.0, 0.0, yaw.rotation_euler[2] + math.radians(25.0))
        bpy.context.view_layer.update()
        shot("cam_pose", os.path.join(work, "ac_yaw.png"), 1600, 1200, 1)


if __name__ == "__main__":
    main()
