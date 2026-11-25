"""Authoring tool: builds the reference toy car, four orthographic renders and
the four silhouette plates.

    blender -b -P build_car.py -- <out_dir> <materials_dir>
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector, Matrix

L, Wd, H = 0.380, 0.160, 0.200       # overall
AXLE = 0.240
WHEEL_D = 0.060
WHEEL_W = 0.025
TRACK_X = 0.075
BODY_Z = 0.060


def log(*a):
    print("[car]", *a, flush=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_percentage = 100


def box(name, center, dims, bevel=0.002):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = center
    bpy.context.collection.objects.link(ob)
    if bevel:
        m = ob.modifiers.new("bevel", 'BEVEL')
        m.width = bevel
        m.segments = 2
    return ob


def cylinder(name, radius, depth, axis='Y'):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32,
                          radius1=radius, radius2=radius, depth=depth)
    if axis == 'Y':
        bmesh.ops.rotate(bm, verts=bm.verts,
                         matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def parent_keep(ob, parent):
    bpy.context.view_layer.update()
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()


def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = 0.03
    e.location = loc
    bpy.context.collection.objects.link(e)
    if parent:
        parent_keep(e, parent)
    return e


def material(name, color, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def build():
    parts = {}
    body = box("body", (0, 0, BODY_Z + 0.045), (L, Wd, 0.09), 0.006)
    chassis = box("chassis", (0, 0, BODY_Z - 0.005), (L - 0.02, Wd - 0.02, 0.02), 0.002)
    cabin = box("cabin", (0.02, 0, BODY_Z + 0.115), (0.18, Wd - 0.02, 0.05), 0.004)
    parts["body"], parts["chassis"], parts["cabin"] = body, chassis, cabin

    wheels = {}
    for name, fx, fy in (("wheel_fl", 1, 1), ("wheel_fr", 1, -1),
                         ("wheel_rl", -1, 1), ("wheel_rr", -1, -1)):
        x = fx * AXLE / 2
        y = fy * (Wd / 2 - WHEEL_W / 2 + 0.004)
        hub = empty(name + "_hub", (x, y, WHEEL_D / 2))
        w = cylinder(name, WHEEL_D / 2, WHEEL_W)
        parent_keep(w, hub)
        w.location = (0, 0, 0)
        hub.parent = body
        wheels[name] = (w, hub, fx, fy)
        parts[name] = w
    parts["wheels"] = wheels

    doors = {}
    for side, sy in (("l", 1), ("r", -1)):
        y = sy * (Wd / 2 + 0.004)
        hinge = empty(f"door_{side}_hinge", (0.06, y, BODY_Z + 0.045))
        d = box(f"door_{side}", (0, 0, 0), (0.10, 0.008, 0.055), 0.002)
        parent_keep(d, hinge)
        hinge.parent = body
        doors[side] = (d, hinge)
        parts[f"door_{side}"] = d
    parts["doors"] = doors
    return parts


def assign_materials(parts):
    m_body = material("mat_body", (0.55, 0.12, 0.10, 1), 0.45)
    m_dark = material("mat_chassis", (0.05, 0.05, 0.06, 1), 0.6)
    m_glass = material("mat_cabin", (0.25, 0.35, 0.42, 1), 0.15, 0.0)
    m_tyre = material("mat_tyre", (0.03, 0.03, 0.035, 1), 0.8)
    parts["body"].data.materials.append(m_body)
    parts["cabin"].data.materials.append(m_glass)
    parts["chassis"].data.materials.append(m_dark)
    for w, _h, _fx, _fy in parts["wheels"].values():
        w.data.materials.append(m_tyre)
    for d, _h in parts["doors"].values():
        d.data.materials.append(m_body)


def stage():
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bg.inputs["Strength"].default_value = 1.0
    for name, loc, power, size in (("key", (0.6, -0.5, 0.7), 60, 0.6),
                                   ("fill", (-0.6, 0.4, 0.5), 25, 0.6),
                                   ("rim", (0.0, 0.6, 0.6), 30, 0.5)):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = power
        ld.size = size
        ob = bpy.data.objects.new("light_" + name, ld)
        ob.location = loc
        d = Vector((0, 0, 0.1)) - ob.location
        ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        bpy.context.collection.objects.link(ob)


def cameras():
    sc = bpy.context.scene
    cams = {}
    for name, loc, rot in (
        ("cam_front", (2.0, 0, 0.1), (math.radians(90), 0, math.radians(90))),
        ("cam_side", (0, -2.0, 0.1), (math.radians(90), 0, 0)),
        ("cam_back", (-2.0, 0, 0.1), (math.radians(90), 0, math.radians(-90))),
        ("cam_top", (0, 0, 2.0), (0, 0, 0)),
    ):
        cd = bpy.data.cameras.new(name)
        cd.type = 'ORTHO'
        cd.ortho_scale = 0.50
        ob = bpy.data.objects.new(name, cd)
        ob.location = loc
        if name == "cam_top":
            ob.rotation_euler = (0, 0, 0)
        else:
            ob.rotation_euler = rot
        bpy.context.collection.objects.link(ob)
        cams[name] = ob
    sc.camera = cams["cam_side"]
    return cams


def render_views(cams, out_dir, prefix="render"):
    sc = bpy.context.scene
    sc.render.resolution_x = 1200
    sc.render.resolution_y = 1200
    sc.render.film_transparent = False
    for name, cam in cams.items():
        sc.camera = cam
        sc.render.filepath = os.path.join(out_dir, f"{prefix}_{name.split('_')[1]}.png")
        bpy.ops.render.render(write_still=True)
        log("rendered", name)
    sc.render.film_transparent = False


def write_manifest(out_dir):
    man = {
        "schemaVersion": 1,
        "units": "meters",
        "blenderVersion": bpy.app.version_string,
        "assets": [
            {"path": "textures/tyre_basecolor.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
        ],
        "renders": [
            {"file": f"render_{v}.png", "camera": f"cam_{v}",
             "resolution": [1200, 1200], "samples": 64}
            for v in ("front", "side", "back", "top")
        ],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=2)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_dir, materials = argv[0], argv[1]
    os.makedirs(out_dir, exist_ok=True)
    reset()
    parts = build()
    assign_materials(parts)
    stage()
    cams = cameras()
    render_views(cams, out_dir)
    write_manifest(out_dir)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "toy_car.blend"),
                                compress=True)
    log("saved")


if __name__ == "__main__":
    main()
