"""Authoring tool: builds the reference articulated desk lamp.

    blender -b -P build_lamp.py -- <solution_dir> <materials_dir>

The lamp is a four-joint chain (yaw, shoulder, elbow, head). Frames 1-3 of
`Pose_Reach` put the head pivot on the three reach targets printed in the
design pack, solved with a two-link inverse kinematics pass.
"""
import json
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = sys.argv[sys.argv.index("--") + 1]
MATERIALS = sys.argv[sys.argv.index("--") + 2]

BASE_R, BASE_H = 0.060, 0.022
PIVOT_Z = BASE_H
L1, L2 = 0.320, 0.300
SHADE_L = 0.090
DESK_W, DESK_D, DESK_T = 1.200, 0.700, 0.030
TARGETS = [
    (0.300, 0.350, 0.120),
    (-0.280, 0.320, 0.120),
    (0.050, 0.550, 0.140),
]


def log(*a):
    print("[lamp]", *a, flush=True)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.02, 0.021, 0.024, 1)
    bg.inputs[1].default_value = 0.10
    sc.world = world


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def box(name, centre, dims, bevel=0.0025):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2,
                        affect='EDGES', clamp_overlap=True)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(centre))
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def cylinder(name, centre, radius, depth, axis='Z', segments=32, r2=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius if r2 is None else r2,
                          depth=depth)
    if axis == 'Y':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(centre))
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def empty(name, location):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = 'ARROWS'
    ob.empty_display_size = 0.04
    ob.location = location
    link(ob)
    return ob


def parent_keep(ob, parent):
    """Parent without moving the child: mesh already carries world coordinates."""
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix.Translation(Vector(-parent.location))


def plain(name, colour, rough=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    return mat


def paint_material(path):
    mat = bpy.data.materials.new("mat_paint")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.42
    img = bpy.data.images.load(path)
    img.name = "lamp_paint"
    img.pack()
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mat.node_tree.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    return mat


# --------------------------------------------------------------------------
def solve_ik(target):
    """Return (yaw, shoulder, elbow) rotations that put the head pivot on target."""
    tx, ty, tz = target
    r = math.hypot(tx, ty)
    h = tz - PIVOT_Z
    d = min(math.hypot(r, h), L1 + L2 - 1e-4)
    best = None
    for i in range(0, 1801):
        beta1 = math.radians(i * 0.1)
        # law of cosines for the elbow, both sign branches
        cos_c = (L1 * L1 + L2 * L2 - d * d) / (2 * L1 * L2)
        c = math.acos(max(-1.0, min(1.0, cos_c)))
        for sign in (+1, -1):
            beta2 = sign * (math.pi - c)
            px = L1 * math.sin(beta1) + L2 * math.sin(beta1 + beta2)
            pz = L1 * math.cos(beta1) + L2 * math.cos(beta1 + beta2)
            err = math.hypot(px - r, pz - h)
            if best is None or err < best[0]:
                best = (err, beta1, beta2, px, pz)
    err, beta1, beta2, px, pz = best
    # Refine the coarse 0.1 degree grid so the reference is far inside the
    # 8 mm acceptance band rather than sitting on the grid quantisation.
    step = math.radians(0.1)
    for _ in range(60):
        step *= 0.5
        for db1 in (-step, 0.0, step):
            for db2 in (-step, 0.0, step):
                b1, b2 = beta1 + db1, beta2 + db2
                qx = L1 * math.sin(b1) + L2 * math.sin(b1 + b2)
                qz = L1 * math.cos(b1) + L2 * math.cos(b1 + b2)
                e = math.hypot(qx - r, qz - h)
                if e < err:
                    err, beta1, beta2 = e, b1, b2
    # Rz(yaw) maps the local +Y the arm swings in onto (tx, ty): the shoulder
    # rotation tilts the chain towards local +Y, so the yaw must be measured
    # from +Y towards +X with the opposite sign.
    yaw = -math.atan2(tx, ty)
    return yaw, beta1, beta2, err


def set_pose(pose):
    yaw, beta1, beta2, err = solve_ik(pose)
    bpy.data.objects["joint_yaw"].rotation_euler = (0.0, 0.0, yaw)
    bpy.data.objects["joint_shoulder"].rotation_euler = (-beta1, 0.0, 0.0)
    bpy.data.objects["joint_elbow"].rotation_euler = (-beta2, 0.0, 0.0)
    bpy.data.objects["joint_head"].rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    head = bpy.data.objects["joint_head"].matrix_world.translation
    return (head - Vector(pose)).length, err


def build_chain(paint, metal, lamp_collection):
    joints = {}
    joints["joint_yaw"] = empty("joint_yaw", (0, 0, PIVOT_Z))
    joints["joint_shoulder"] = empty("joint_shoulder", (0, 0, PIVOT_Z))
    parent_keep(joints["joint_shoulder"], joints["joint_yaw"])
    joints["joint_elbow"] = empty("joint_elbow", (0, 0, PIVOT_Z + L1))
    parent_keep(joints["joint_elbow"], joints["joint_shoulder"])
    joints["joint_head"] = empty("joint_head", (0, 0, PIVOT_Z + L1 + L2))
    parent_keep(joints["joint_head"], joints["joint_elbow"])

    base = cylinder("base", (0, 0, BASE_H / 2), BASE_R, BASE_H, segments=48)
    base.data.materials.append(paint)
    column = cylinder("column", (0, 0, PIVOT_Z + 0.020), 0.014, 0.040, segments=24)
    column.data.materials.append(metal)

    lower = box("lower_arm", (0, 0, PIVOT_Z + L1 / 2), (0.030, 0.030, L1), bevel=0.004)
    lower.data.materials.append(paint)
    upper = box("upper_arm", (0, 0, PIVOT_Z + L1 + L2 / 2), (0.024, 0.024, L2), bevel=0.003)
    upper.data.materials.append(paint)

    shade = cylinder("shade", (0, 0, PIVOT_Z + L1 + L2 + SHADE_L / 2),
                     0.052, SHADE_L, segments=40, r2=0.030)
    shade.data.materials.append(metal)
    bulb = cylinder("bulb", (0, 0, PIVOT_Z + L1 + L2 + SHADE_L - 0.004), 0.020, 0.012,
                    segments=24)
    bulb.data.materials.append(plain("mat_bulb", (1.0, 0.93, 0.78), 0.3))

    parent_keep(lower, joints["joint_shoulder"])
    parent_keep(upper, joints["joint_elbow"])
    parent_keep(shade, joints["joint_head"])
    parent_keep(bulb, joints["joint_head"])

    for ob in (lower, upper, shade, bulb):
        for coll in list(ob.users_collection):
            coll.objects.unlink(ob)
        lamp_collection.objects.link(ob)
    return joints


def build_light(joints, lamp_collection):
    lamp = bpy.data.lights.new("lamp_spot", 'SPOT')
    lamp.energy = 45.0
    lamp.spot_size = math.radians(42)
    lamp.spot_blend = 0.35
    lamp.color = (1.0, 0.90, 0.74)
    lamp.shadow_soft_size = 0.012
    ob = bpy.data.objects.new("lamp_spot", lamp)
    lamp_collection.objects.link(ob)
    ob.location = (0, 0, PIVOT_Z + L1 + L2 + SHADE_L - 0.004)
    parent_keep(ob, joints["joint_head"])
    return ob


def aim_light(frame_target):
    """Point the spot at the target of the current pose, from the bulb."""
    light = bpy.data.objects["lamp_spot"]
    bpy.context.view_layer.update()
    eye = light.matrix_world.translation
    d = Vector(frame_target) - eye
    light.rotation_mode = 'XYZ'
    light.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()


def build_stage():
    desk = box("desk", (0.10, 0.30, -DESK_T / 2), (DESK_W, DESK_D, DESK_T), bevel=0.004)
    wood = plain("mat_desk", (0.32, 0.24, 0.17), 0.55)
    desk.data.materials.append(wood)

    # target markers: thin rings on the desk, used by nothing but the render
    ring_mat = plain("mat_marker", (0.85, 0.35, 0.15), 0.45)
    for i, t in enumerate(TARGETS, start=1):
        ring = cylinder(f"target_{i:02d}", (t[0], t[1], 0.0008), 0.030, 0.0016,
                        segments=40)
        ring.data.materials.append(ring_mat)

    def area(name, loc, energy, size, colour, target=(0.1, 0.3, 0.0)):
        lamp = bpy.data.lights.new(name, 'AREA')
        lamp.energy = energy
        lamp.size = size
        lamp.color = colour
        o = bpy.data.objects.new(name, lamp)
        o.location = loc
        d = Vector(target) - Vector(loc)
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        return link(o)

    area("light_fill", (1.4, -0.8, 1.1), 28.0, 1.6, (0.72, 0.80, 1.0))
    area("light_rim", (-0.9, 1.1, 0.9), 14.0, 1.2, (1.0, 0.88, 0.75))

    def camera(name, loc, target, lens):
        cam = bpy.data.cameras.new(name)
        cam.lens = lens
        o = link(bpy.data.objects.new(name, cam))
        o.location = loc
        d = Vector(target) - Vector(loc)
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        return o

    camera("cam_pose", (1.05, -0.95, 0.85), (0.10, 0.30, 0.22), 35.0)
    camera("cam_hero", (0.62, -0.52, 0.46), (0.08, 0.22, 0.26), 50.0)


def render(cam, path, width, height):
    sc = bpy.context.scene
    sc.camera = bpy.data.objects[cam]
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.resolution_percentage = 100
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    log("rendered", path)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
    reset_scene()
    paint = paint_material(os.path.join(MATERIALS, "textures", "lamp_paint.png"))
    metal = plain("mat_steel", (0.68, 0.69, 0.72), 0.30, 1.0)
    lamp_collection = bpy.data.collections.new("lamp")
    bpy.context.scene.collection.children.link(lamp_collection)

    joints = build_chain(paint, metal, lamp_collection)
    light = build_light(joints, lamp_collection)
    build_stage()

    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 3
    for i, target in enumerate(TARGETS, start=1):
        err_mm, _ = set_pose(target)
        log(f"target {i}: head error {err_mm * 1000:.3f} mm")
        assert err_mm < 1e-4, f"pose {i} missed by {err_mm * 1000:.2f} mm"
        aim_light(target)
        for name in ("joint_yaw", "joint_shoulder", "joint_elbow", "joint_head"):
            ob = bpy.data.objects[name]
            ob.keyframe_insert("rotation_euler", frame=i)
        light.keyframe_insert("rotation_euler", frame=i)

    # keyframe on the empties lives in one action shared by all four objects
    ad = bpy.data.objects["joint_yaw"].animation_data
    if ad and ad.action:
        ad.action.name = "Pose_Reach"

    sc.frame_set(1)
    bpy.context.view_layer.update()
    render("cam_pose", os.path.join(OUT, "render_pose_01.png"), 1600, 1200)
    sc.frame_set(2)
    bpy.context.view_layer.update()
    render("cam_pose", os.path.join(OUT, "render_pose_02.png"), 1600, 1200)
    sc.frame_set(3)
    bpy.context.view_layer.update()
    render("cam_pose", os.path.join(OUT, "render_pose_03.png"), 1600, 1200)
    render("cam_hero", os.path.join(OUT, "render_hero.png"), 1600, 1200)

    sc.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "desk_lamp.blend"))
    log("saved")

    manifest = {
        "schemaVersion": 1,
        "units": "meters",
        "blenderVersion": bpy.app.version_string,
        "assets": [
            {"path": "textures/lamp_paint.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
        ],
        "renders": [
            {"file": "render_pose_01.png", "camera": "cam_pose",
             "resolution": [1600, 1200], "samples": 64},
            {"file": "render_pose_02.png", "camera": "cam_pose",
             "resolution": [1600, 1200], "samples": 64},
            {"file": "render_pose_03.png", "camera": "cam_pose",
             "resolution": [1600, 1200], "samples": 64},
            {"file": "render_hero.png", "camera": "cam_hero",
             "resolution": [1600, 1200], "samples": 64},
        ],
    }
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    log("done")


if __name__ == "__main__":
    main()
