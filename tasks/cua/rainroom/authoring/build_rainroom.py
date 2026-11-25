"""Authoring tool: builds the rainroom scene, two lighting collections and the
night/morning renders.

    blender -b -P build_rainroom.py -- <out_dir> <materials_dir>
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

W, D, H = 4.2, 3.6, 2.8
T = 0.02


def log(*a):
    print("[rain]", *a, flush=True)


def reset():
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
    sc.view_settings.view_transform = 'AgX'


def box(name, center, dims, bevel=0.004):
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


def cyl(name, center, r, depth, axis='Z', verts=24):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r,
                          depth=depth)
    if axis == 'X':
        bmesh.ops.rotate(bm, verts=bm.verts,
                         matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, 'Y'))
    elif axis == 'Y':
        bmesh.ops.rotate(bm, verts=bm.verts,
                         matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, 'X'))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = center
    bpy.context.collection.objects.link(ob)
    return ob


def mat(name, color, rough=0.5, metal=0.0, transmission=0.0, ior=1.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = ior
    if transmission > 0:
        m.blend_method = 'BLEND'
    return m


def build_room():
    parts = [box("floor", (0, 0, -T / 2), (W, D, T)),
             box("ceiling", (0, 0, H + T / 2), (W, D, T)),
             box("wall_back", (0, D / 2 - T / 2, H / 2), (W, T, H)),
             box("wall_front", (0, -D / 2 + T / 2, H / 2), (W, T, H)),
             box("wall_left", (-W / 2 + T / 2, 0, H / 2), (T, D, H))]
    # right wall with a 1.2 x 1.4 window opening
    win_w, win_h, win_z = 1.2, 1.4, 1.5
    side = (D - win_w) / 2
    parts.append(box("wall_right_lo", (W / 2 - T / 2, -D / 2 + side / 2, H / 2),
                     (T, side, H)))
    parts.append(box("wall_right_hi", (W / 2 - T / 2, D / 2 - side / 2, H / 2),
                     (T, side, H)))
    parts.append(box("wall_right_top", (W / 2 - T / 2, 0, (win_z + win_h / 2 + H) / 2),
                     (T, win_w, H - win_z - win_h / 2)))
    parts.append(box("wall_right_sill", (W / 2 - T / 2, 0, (win_z - win_h / 2) / 2),
                     (T, win_w, win_z - win_h / 2)))
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    shell = bpy.context.view_layer.objects.active
    shell.name = "room_shell"
    shell.data.name = "room_shell"
    return shell


def build_furniture():
    objs = {}
    m_walnut = mat("mat_walnut", (0.16, 0.09, 0.05, 1), 0.42)
    m_linen = mat("mat_linen", (0.62, 0.60, 0.55, 1), 0.85)
    m_ceramic = mat("mat_ceramic", (0.82, 0.80, 0.76, 1), 0.22)
    m_copper = mat("mat_copper", (0.72, 0.42, 0.26, 1), 0.32, 1.0)
    m_glass = mat("mat_glass", (0.85, 0.92, 0.95, 1), 0.06, transmission=0.0)
    m_glass.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.12
    m_plant = mat("mat_plant", (0.18, 0.28, 0.14, 1), 0.7)

    def emissive(name, color, strength):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = color
        em.inputs["Strength"].default_value = strength
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
        return m

    def add(name, ob, material):
        ob.data.materials.append(material)
        objs[name] = ob

    add("rug", box("rug", (0, 0.2, 0.006), (2.6, 2.0, 0.012), 0.002), m_linen)
    add("sofa", box("sofa", (-1.45, 0.55, 0.42), (0.85, 1.9, 0.75), 0.03), m_linen)
    add("sofa_back", box("sofa_back", (-1.75, 0.55, 0.62), (0.22, 1.9, 0.5), 0.03), m_linen)
    add("coffee_table", box("coffee_table", (0.1, 0.35, 0.36), (1.2, 0.7, 0.05), 0.01), m_walnut)
    for i, (x, y) in enumerate(((-0.4, 0.05), (0.6, 0.05), (-0.4, 0.65), (0.6, 0.65))):
        add(f"table_leg_{i+1}", box(f"table_leg_{i+1}", (x, y, 0.18), (0.05, 0.05, 0.36), 0.004), m_walnut)
    add("side_table", box("side_table", (-1.35, -0.9, 0.28), (0.45, 0.45, 0.04), 0.01), m_walnut)
    add("side_table_leg", box("side_table_leg", (-1.35, -0.9, 0.14), (0.06, 0.06, 0.28), 0.004), m_walnut)
    add("floor_lamp", cyl("floor_lamp", (1.55, 1.3, 0.9), 0.02, 1.8), m_copper)
    add("floor_lamp_shade", cyl("floor_lamp_shade", (1.55, 1.3, 1.72), 0.18, 0.28),
        emissive("mat_shade_glow", (0.95, 0.95, 1.0, 1), 0.9))
    add("table_lamp", cyl("table_lamp", (-1.35, -0.9, 0.42), 0.05, 0.22),
        emissive("mat_lamp_glow", (0.95, 0.95, 1.0, 1), 0.6))
    add("bookshelf", box("bookshelf", (1.85, 0.1, 0.95), (0.35, 1.5, 1.9), 0.01), m_walnut)
    for i, (z, h) in enumerate(((0.35, 0.3), (0.75, 0.28), (1.15, 0.26), (1.55, 0.24))):
        add(f"books_{i+1}", box(f"books_{i+1}", (1.83, -0.35 + 0.2 * i, z), (0.12, 0.16, h), 0.004), m_linen)
    add("vase_01", cyl("vase_01", (0.15, 0.35, 0.5), 0.07, 0.22), m_ceramic)
    add("vase_02", cyl("vase_02", (0.35, 0.3, 0.47), 0.05, 0.16), m_ceramic)
    add("mug_01", cyl("mug_01", (0.5, 0.45, 0.41), 0.04, 0.09), m_ceramic)
    add("mug_02", cyl("mug_02", (0.62, 0.4, 0.41), 0.04, 0.09), m_ceramic)
    add("tray", cyl("tray", (0.3, 0.55, 0.39), 0.16, 0.02), m_copper)
    add("candle_01", cyl("candle_01", (0.25, 0.55, 0.45), 0.03, 0.1), m_ceramic)
    add("candle_02", cyl("candle_02", (0.37, 0.55, 0.44), 0.028, 0.08), m_ceramic)
    add("bottle", cyl("bottle", (0.05, 0.2, 0.47), 0.045, 0.18), m_glass)
    add("plant_pot", cyl("plant_pot", (1.7, -1.1, 0.18), 0.16, 0.32), m_ceramic)
    add("plant_leaves", box("plant_leaves", (1.7, -1.1, 0.62), (0.42, 0.42, 0.55), 0.02), m_plant)
    add("cushion_01", box("cushion_01", (-1.55, 0.1, 0.68), (0.16, 0.4, 0.4), 0.02), m_linen)
    add("cushion_02", box("cushion_02", (-1.55, 0.85, 0.68), (0.16, 0.4, 0.4), 0.02), m_linen)
    add("curtain_l", box("curtain_l", (1.95, -0.75, 1.5), (0.06, 0.5, 1.5), 0.01), m_linen)
    add("curtain_r", box("curtain_r", (1.95, 0.75, 1.5), (0.06, 0.5, 1.5), 0.01), m_linen)
    add("wall_art", box("wall_art", (0.2, 1.74, 1.7), (0.9, 0.03, 0.6), 0.002), m_copper)
    add("window_glass", box("window_glass", (2.09, 0, 1.5), (0.01, 1.2, 1.4), 0.0), m_glass)
    return objs


def build_lights():
    def coll(name):
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        return c

    def light(name, cname, kind, loc, rot, energy, color, size=1.0):
        c = bpy.data.collections.get(cname) or coll(cname)
        ld = bpy.data.lights.new(name, kind)
        ld.energy = energy
        ld.color = color
        if kind == 'AREA':
            ld.size = size
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        ob.rotation_euler = rot
        c.objects.link(ob)
        return ob

    night = coll("light_night")
    morning = coll("light_morning")
    # night: cool window glow, two warm practicals
    light("night_window", "light_night", 'AREA', (2.6, 0, 1.5),
          (0, math.radians(-90), 0), 1100, (0.22, 0.40, 1.0), 1.2)
    light("night_lamp_a", "light_night", 'POINT', (1.55, 1.3, 1.56), (0, 0, 0),
          10, (1.0, 0.78, 0.58), 0.1)
    light("night_lamp_b", "light_night", 'POINT', (-1.35, -0.9, 0.66), (0, 0, 0),
          5, (1.0, 0.78, 0.58), 0.08)
    # morning: warm low sun through the window plus soft fill
    sun = light("morning_sun", "light_morning", 'SUN', (2.6, -1.2, 2.4),
                (math.radians(62), 0, math.radians(115)), 5.0, (1.0, 0.86, 0.66))
    light("morning_fill", "light_morning", 'AREA', (1.9, 0.4, 1.9),
          (0, math.radians(-90), 0), 600, (1.0, 0.92, 0.80), 1.6)
    return night, morning


def world_setup():
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.55, 0.62, 0.72, 1)
    bg.inputs["Strength"].default_value = 0.12


def camera():
    cd = bpy.data.cameras.new("cam_room")
    cd.lens = 22
    cam = bpy.data.objects.new("cam_room", cd)
    cam.location = (1.55, -1.55, 1.55)
    d = Vector((-0.3, 0.5, 1.05)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def render_pair(out_dir, night, morning):
    sc = bpy.context.scene
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 900
    sc.render.resolution_percentage = 100
    for name, show, hide in (("render_night", night, morning),
                             ("render_morning", morning, night)):
        for c in bpy.data.collections:
            if c.name in ("light_night", "light_morning"):
                c.hide_render = (c == hide)
        sc.render.filepath = os.path.join(out_dir, name + ".png")
        bpy.ops.render.render(write_still=True)
        log("rendered", name)
    for c in bpy.data.collections:
        if c.name in ("light_night", "light_morning"):
            c.hide_render = False


def write_manifest(out_dir, objs):
    man = {
        "schemaVersion": 1,
        "units": "meters",
        "blenderVersion": bpy.app.version_string,
        "assets": [{"path": "textures/rain_streaks.png", "role": "texture",
                    "source": "self-authored", "license": "CC0-1.0", "url": ""}],
        "renders": [
            {"file": "render_night.png", "camera": "cam_room",
             "resolution": [1600, 900], "samples": 64},
            {"file": "render_morning.png", "camera": "cam_room",
             "resolution": [1600, 900], "samples": 64},
        ],
        "objects": sorted(objs),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=2)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_dir, materials = argv[0], argv[1]
    os.makedirs(out_dir, exist_ok=True)
    reset()
    shell = build_room()
    shell.data.materials.append(mat("mat_wall", (0.72, 0.70, 0.66, 1), 0.85))
    objs = build_furniture()
    build_lights()
    world_setup()
    camera()
    night = bpy.data.collections["light_night"]
    morning = bpy.data.collections["light_morning"]
    render_pair(out_dir, night, morning)
    write_manifest(out_dir, list(objs) + ["room_shell"])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "rainroom.blend"),
                                compress=True)
    log("saved")


if __name__ == "__main__":
    main()
