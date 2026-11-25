"""Authoring tool: builds the reference exhibition booth and its renders.

    blender -b -P build_booth.py -- <out_dir> <materials_dir>

Authoring tool, not shipped to the agent and not used by the verifier.
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector

W, D, H = 6.0, 4.0, 4.0
WALL_T = 0.02
ENTRANCE = 2.4
COLUMN = 0.4
HYD = Vector((-4.2, 0.0, 0.0))
BRAND_PRIMARY = (0.1216, 0.4353, 0.3608, 1.0)     # #1F6F5C
BRAND_SECONDARY = (0.9490, 0.7569, 0.3059, 1.0)   # #F2C14E

PRODUCTS = [("product_01", 0.30, 0.20, 0.25),
            ("product_02", 0.38, 0.26, 0.32),
            ("product_03", 0.46, 0.30, 0.38)]
PLINTH_Z = 0.40


def log(*a):
    print("[booth]", *a, flush=True)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = 'METERS'
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'


def box(name, center, dims, bevel=0.0):
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
    if bevel > 0:
        m = ob.modifiers.new("bevel", 'BEVEL')
        m.width = bevel
        m.segments = 2
    return ob


def build_shell():
    parts = []
    parts.append(box("floor", (0, 0, -WALL_T / 2), (W, D, WALL_T)))
    parts.append(box("back_wall", (W / 2 - WALL_T / 2, 0, H / 2), (WALL_T, D, H)))
    parts.append(box("wall_left", (0, -D / 2 + WALL_T / 2, H / 2), (W, WALL_T, H)))
    parts.append(box("wall_right", (0, D / 2 - WALL_T / 2, H / 2), (W, WALL_T, H)))
    side = (D - ENTRANCE) / 2
    parts.append(box("entry_wall_lo", (-W / 2 + WALL_T / 2, -D / 2 + side / 2, H / 2),
                     (WALL_T, side, H)))
    parts.append(box("entry_wall_hi", (-W / 2 + WALL_T / 2, D / 2 - side / 2, H / 2),
                     (WALL_T, side, H)))
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    shell = bpy.context.view_layer.objects.active
    shell.name = "booth_shell"
    shell.data.name = "booth_shell"
    return shell


def build_furniture():
    objs = {}
    objs["cabinet_01"] = box("cabinet_01", (-0.5, -1.75, 1.0), (1.2, 0.5, 2.0), 0.006)
    objs["cabinet_02"] = box("cabinet_02", (1.5, 1.75, 1.0), (1.2, 0.5, 2.0), 0.006)
    objs["counter"] = box("counter", (-2.0, -1.5, 0.5), (1.8, 0.6, 1.0), 0.006)
    plinths = []
    for i, y in enumerate((-1.2, 0.0, 1.2)):
        plinths.append(box(f"plinth_0{i+1}", (2.2, y, PLINTH_Z / 2),
                           (0.8, 0.8, PLINTH_Z), 0.004))
    objs["plinths"] = plinths
    products = []
    for i, (name, w, d, h) in enumerate(PRODUCTS):
        y = (-1.2, 0.0, 1.2)[i]
        products.append(box(name, (2.2, y, PLINTH_Z + h / 2), (d, w, h), 0.01))
    objs["products"] = products
    objs["column"] = box("column", (W / 2 - COLUMN / 2 - 0.02, -D / 2 + COLUMN / 2 + 0.02, H / 2),
                         (COLUMN, COLUMN, H), 0.004)
    # entrance marker: a 1 cm mat filling the 2.4 m opening, just inside
    objs["entrance_zone"] = box("entrance_zone", (-W / 2 + 0.06, 0, 0.005),
                                (0.12, ENTRANCE, 0.01))
    return objs


def material(name, color, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def logo_decal(materials_dir):
    png = os.path.join(materials_dir, "brand", "logo.png")
    img = bpy.data.images.load(png)
    img.pack()
    me = bpy.data.meshes.new("logo_decal")
    x = W / 2 - WALL_T - 0.001
    w, h = 0.9, 0.3
    me.from_pydata([(x, -w / 2, 2.45), (x, w / 2, 2.45),
                    (x, w / 2, 2.45 + h), (x, -w / 2, 2.45 + h)],
                   [], [(0, 3, 2, 1)])
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    for i, co in enumerate([(1, 0), (0, 0), (0, 1), (1, 1)]):
        uv.data[i].uv = co
    ob = bpy.data.objects.new("logo_decal", me)
    bpy.context.collection.objects.link(ob)
    mat = bpy.data.materials.new("mat_logo")
    mat.use_nodes = True
    mat.blend_method = 'CLIP'
    nt = mat.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    bsdf = nt.nodes["Principled BSDF"]
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    ob.data.materials.append(mat)
    return ob


def add_lighting():
    root = bpy.data.objects.new("lighting", None)
    root.empty_display_type = 'PLAIN_AXES'
    bpy.context.collection.objects.link(root)
    specs = [("key", (1.0, -1.0, 3.2), 220, 2.0),
             ("fill", (-2.0, 1.2, 2.6), 90, 2.0),
             ("rim", (2.0, 1.0, 3.0), 120, 1.5)]
    for name, loc, power, size in specs:
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = power
        ld.size = size
        ob = bpy.data.objects.new("light_" + name, ld)
        ob.location = loc
        d = Vector((1.0, 0, 1.2)) - ob.location
        ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        bpy.context.collection.objects.link(ob)
        ob.parent = root
    return root


def add_world():
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.85, 0.87, 0.88, 1.0)
    bg.inputs["Strength"].default_value = 0.35


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def add_cameras():
    cams = {}
    cd = bpy.data.cameras.new("cam_entrance")
    cd.lens = 35
    cam = bpy.data.objects.new("cam_entrance", cd)
    cam.location = (-W / 2 + 1.5, 0.0, 1.6)
    bpy.context.collection.objects.link(cam)
    look_at(cam, (1.2, 0.0, 1.1))
    cams["entrance"] = cam

    cd = bpy.data.cameras.new("cam_top")
    cd.type = 'ORTHO'
    cd.ortho_scale = 6.2
    cam = bpy.data.objects.new("cam_top", cd)
    cam.location = (0, 0, 6.0)
    look_at(cam, (0, 0, 0))
    bpy.context.collection.objects.link(cam)
    cams["top"] = cam
    return cams


RENDERS = [("render_entrance", "entrance", (1920, 1080)),
           ("render_top", "top", (2048, 1536))]


def render_all(cams, out_dir):
    sc = bpy.context.scene
    for fname, key, res in RENDERS:
        sc.camera = cams[key]
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.resolution_percentage = 100
        sc.render.filepath = os.path.join(out_dir, fname + ".png")
        bpy.ops.render.render(write_still=True)
        log("rendered", fname)


def write_manifest(out_dir):
    import json
    man = {
        "schemaVersion": 1,
        "units": "meters",
        "blenderVersion": bpy.app.version_string,
        "assets": [
            {"path": "brand/logo.png", "role": "texture", "source": "self-authored",
             "license": "CC0-1.0", "url": ""},
        ],
        "renders": [
            {"file": f + ".png", "camera": "cam_" + c, "resolution": list(r),
             "samples": 64} for f, c, r in RENDERS
        ],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=2)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_dir, materials = argv[0], argv[1]
    os.makedirs(out_dir, exist_ok=True)

    reset_scene()
    shell = build_shell()
    furn = build_furniture()
    add_world()
    add_lighting()
    decal = logo_decal(materials)

    m_primary = material("mat_brand_primary", BRAND_PRIMARY, 0.45)
    m_secondary = material("mat_brand_secondary", BRAND_SECONDARY, 0.4)
    m_white = material("mat_wall_white", (0.82, 0.83, 0.84, 1), 0.6)
    m_floor = material("mat_floor", (0.28, 0.29, 0.30, 1), 0.5)
    m_cab = material("mat_cabinet", (0.09, 0.10, 0.11, 1), 0.35)
    m_prod = material("mat_product", (0.16, 0.17, 0.18, 1), 0.4)
    m_col = material("mat_column", (0.75, 0.75, 0.74, 1), 0.6)
    m_zone = material("mat_entrance_marker", (0.55, 0.55, 0.55, 1), 0.7)

    shell.data.materials.append(m_white)
    # back wall face gets the brand colour
    shell.data.materials.append(m_primary)
    shell.data.materials.append(m_floor)
    for p in shell.data.polygons:
        c = p.center
        if c.z < 0.0:
            p.material_index = 2
        elif c.x > W / 2 - 0.1:
            p.material_index = 1

    furn["cabinet_01"].data.materials.append(m_cab)
    furn["cabinet_02"].data.materials.append(m_cab)
    furn["counter"].data.materials.append(m_secondary)
    furn["column"].data.materials.append(m_col)
    furn["entrance_zone"].data.materials.append(m_zone)
    for i, pl in enumerate(furn["plinths"]):
        pl.data.materials.append(m_primary if i % 2 == 0 else m_secondary)
    for pr in furn["products"]:
        pr.data.materials.append(m_prod)

    for img in bpy.data.images:
        if img.source == 'FILE' and not img.packed_file:
            img.pack()

    cams = add_cameras()
    render_all(cams, out_dir)
    write_manifest(out_dir)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "booth.blend"),
                                compress=True)
    log("saved", os.path.join(out_dir, "booth.blend"))


if __name__ == "__main__":
    main()
