"""Authoring tool: builds the reference folding banner stand.

    blender -b -P build_banner.py -- <solution_dir> <materials_dir>
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

W = 0.800            # width
BASE_H, BASE_D = 0.050, 0.120
MAST_W = 0.040
MAST_TOP = 1.960
TOP_T = 0.040
H = MAST_TOP + TOP_T          # 2.000
CANVAS_W, CANVAS_H = 0.800, 1.900
CANVAS_Z0 = 0.060
CANVAS_Y = 0.030
LEG_LEN = 1.900
HINGE_Z = 0.075
HINGE_Y = -0.045
OPEN_DEG = 14.0


def log(*a):
    print("[banner]", *a, flush=True)


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
    bg.inputs[0].default_value = (0.05, 0.052, 0.056, 1)
    bg.inputs[1].default_value = 0.55
    sc.world = world


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def box(name, centre, dims, bevel=0.002):
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


def plain(name, colour, rough=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    return mat


def banner_texture(path, px_w=819, px_h=1945):
    import packgen
    c = packgen.Canvas(px_w, px_h, (28, 44, 78), scale=2)
    c.rect(0, 0, px_w, 360, (28, 44, 78), fill=(28, 44, 78), width=0)
    c.text_center(px_w / 2, 90, "ATLAS", 12, (240, 232, 210))
    c.text_center(px_w / 2, 240, "TRADE SHOW 2026", 5, (222, 150, 80))
    c.rect(60, 420, px_w - 60, 430, (240, 232, 210), fill=(240, 232, 210), width=0)
    for i in range(5):
        y = 520 + i * 180
        c.rect(80, y, 140, y + 100, (222, 150, 80), fill=(222, 150, 80), width=0)
        c.text(170, y + 20, f"STATION {i + 1:02d}", 5, (240, 232, 210))
    c.rect(60, px_h - 520, px_w - 60, px_h - 300, (44, 60, 96), fill=(44, 60, 96), width=0)
    c.text_center(px_w / 2, px_h - 470, "HALL B - BOOTH 12", 4, (240, 232, 210))
    c.text_center(px_w / 2, px_h - 380, "ATLAS-EXPO.ORG", 4, (222, 150, 80))
    with open(path, "wb") as fh:
        fh.write(c.png())


def canvas_material(path):
    mat = bpy.data.materials.new("mat_canvas")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.72
    img = bpy.data.images.load(path)
    img.name = "banner_graphic"
    img.pack()
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mat.node_tree.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    return mat


def build_canvas(mat):
    nx, ny = 8, 40
    verts, faces, uvs = [], [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = -CANVAS_W / 2 + CANVAS_W * i / nx
            z = CANVAS_Z0 + CANVAS_H * j / ny
            verts.append((x, CANVAS_Y, z))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
            # The canvas faces +Y and is viewed from +Y, so +X is on the
            # viewer's left: flip U so the print reads left-to-right.
            uvs.append([(1 - i / nx, j / ny), (1 - (i + 1) / nx, j / ny),
                        (1 - (i + 1) / nx, (j + 1) / ny), (1 - i / nx, (j + 1) / ny)])
    me = bpy.data.meshes.new("canvas")
    me.from_pydata(verts, [], faces)
    me.validate()
    me.materials.append(mat)
    uv = me.uv_layers.new(name="UVMap")
    for poly, quad in zip(me.polygons, uvs):
        for li, co in zip(poly.loop_indices, quad):
            uv.data[li].uv = co
    ob = link(bpy.data.objects.new("canvas", me))
    return ob


def build_frame(alu):
    base = box("base", (0, 0, BASE_H / 2), (W, BASE_D, BASE_H))
    masts = []
    for side, x in (("left", -W / 2 + MAST_W / 2), ("right", W / 2 - MAST_W / 2)):
        masts.append(box(f"mast_{side}", (x, 0, (BASE_H + MAST_TOP) / 2),
                         (MAST_W, MAST_W, MAST_TOP - BASE_H)))
    top = box("top_bar", (0, 0, MAST_TOP + TOP_T / 2), (W, MAST_W, TOP_T))
    for ob in [base, top] + masts:
        ob.data.materials.append(alu)
    return base, masts, top


def build_leg(alu):
    hinge = bpy.data.objects.new("hinge_rear", None)
    hinge.empty_display_type = 'SINGLE_ARROW'
    hinge.location = (0.0, HINGE_Y, HINGE_Z)
    link(hinge)
    bpy.context.view_layer.update()
    leg = box("leg_rear", (0.0, HINGE_Y, HINGE_Z + LEG_LEN / 2), (0.036, 0.036, LEG_LEN),
              bevel=0.003)
    leg.data.materials.append(alu)
    leg.parent = hinge
    # Explicit inverse: the mesh already carries world coordinates, so the
    # parent must not translate it a second time.
    leg.matrix_parent_inverse = Matrix.Translation(Vector(-hinge.location))
    return hinge, leg


def build_stage():
    ground = box("ground", (0, 0, -0.005), (4.0, 4.0, 0.010), bevel=0.0)
    g = plain("mat_ground", (0.17, 0.17, 0.18), 0.7)
    ground.data.materials.append(g)

    def area(name, loc, energy, size, colour=(1, 1, 1), target=(0, 0, 1.0)):
        lamp = bpy.data.lights.new(name, 'AREA')
        lamp.energy = energy
        lamp.size = size
        lamp.color = colour
        o = bpy.data.objects.new(name, lamp)
        o.location = loc
        d = Vector(target) - o.location
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        return link(o)

    area("light_key", (1.6, 2.2, 2.6), 260.0, 2.0, (1.0, 0.97, 0.93), (0, 0, 1.1))
    area("light_fill", (-2.0, 1.6, 1.2), 90.0, 2.4, (0.86, 0.91, 1.0), (0, 0, 1.0))
    area("light_rim", (0.4, -2.4, 2.4), 140.0, 1.6, (1.0, 0.95, 0.88), (0, 0, 1.2))

    def camera(name, loc, target, lens, ortho=None):
        cam = bpy.data.cameras.new(name)
        cam.lens = lens
        if ortho:
            cam.type = 'ORTHO'
            cam.ortho_scale = ortho
        o = link(bpy.data.objects.new(name, cam))
        o.location = loc
        d = Vector(target) - Vector(loc)
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        return o

    camera("cam_front", (0, 3.2, 1.0), (0, 0, 1.0), 50.0, ortho=2.15)
    camera("cam_three_quarter", (1.9, 2.4, 1.8), (0, 0, 1.0), 35.0)
    camera("cam_folded", (0.0, 2.2, 1.0), (0, 0, 1.0), 50.0, ortho=2.15)


def set_hinge(hinge, deg):
    """Open the rear leg away from the print (towards -Y)."""
    hinge.rotation_mode = 'XYZ'
    hinge.rotation_euler = (math.radians(-deg), 0.0, 0.0)
    bpy.context.view_layer.update()


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
    graphic = os.path.join(OUT, "textures", "banner_graphic.png")
    banner_texture(graphic)
    mat = canvas_material(graphic)
    alu = plain("mat_aluminium", (0.70, 0.72, 0.75), 0.32, 0.92)

    build_frame(alu)
    canvas = build_canvas(mat)
    hinge, leg = build_leg(alu)
    build_stage()

    set_hinge(hinge, OPEN_DEG)
    render("cam_front", os.path.join(OUT, "render_front.png"), 1200, 1600)
    render("cam_three_quarter", os.path.join(OUT, "render_three_quarter.png"), 1600, 1200)
    set_hinge(hinge, 0.0)
    render("cam_folded", os.path.join(OUT, "render_folded.png"), 1200, 1600)
    set_hinge(hinge, OPEN_DEG)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "banner_stand.blend"))
    log("saved")

    manifest = {
        "schemaVersion": 1,
        "units": "meters",
        "blenderVersion": bpy.app.version_string,
        "assets": [
            {"path": "textures/banner_graphic.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
        ],
        "renders": [
            {"file": "render_front.png", "camera": "cam_front",
             "resolution": [1200, 1600], "samples": 64},
            {"file": "render_three_quarter.png", "camera": "cam_three_quarter",
             "resolution": [1600, 1200], "samples": 64},
            {"file": "render_folded.png", "camera": "cam_folded",
             "resolution": [1200, 1600], "samples": 64},
        ],
    }
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    log("done")


if __name__ == "__main__":
    main()
