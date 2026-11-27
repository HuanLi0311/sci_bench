"""Authoring tool: builds the reference drawer cabinet, renders and manifest.

    blender -b -P build_cabinet.py -- <solution_dir> <materials_dir>

Authoring only; never shipped to the agent and never used by the verifier.
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

W, D, H, T = 1.000, 0.450, 0.900, 0.018
FRONT_Y = D / 2
BAY_Z0, BAY_Z1 = 0.130, 0.880
BAY_H = (BAY_Z1 - BAY_Z0) / 5
DRAWER_W = 0.440
TRAY_D = 0.400
TRAVEL = 0.420
PLINTH = 0.060
HINGE_X = 0.481
DOOR_W = 0.450
DOOR_Y = 0.2175
DOOR_Z0, DOOR_Z1 = BAY_Z0, BAY_Z1
DOOR_HINGE_Z = (DOOR_Z0 + DOOR_Z1) / 2


def log(*a):
    print("[cabinet]", *a, flush=True)


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
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.05, 0.052, 0.056, 1.0)
    bg.inputs[1].default_value = 0.25
    sc.world = world


def link(ob, collection=None):
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def box(name, centre, dims, bevel=0.0025, segments=2):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segments,
                        affect='EDGES', clamp_overlap=True)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(centre))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    return link(ob)


def cylinder(name, centre, radius, depth, axis='Z', segments=24):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius, depth=depth)
    if axis == 'X':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(90), 3, 'Y'))
    elif axis == 'Y':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(centre))
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.object
    ob.name = name
    ob.data.name = name
    return ob


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------
def wood_maps(size=2048, seed=99):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    warp = (np.sin(x / size * 34 * np.pi + 1.7 * np.sin(y / size * 6 * np.pi)) * 0.5 + 0.5)
    fine = (np.sin(x / size * 190 * np.pi + 3.1 * np.sin(y / size * 21 * np.pi)) * 0.5 + 0.5)
    ring = np.clip(0.65 * warp + 0.35 * fine, 0, 1)
    base = np.zeros((size, size, 3), np.float32)
    base[..., 0] = 0.26 + 0.20 * ring
    base[..., 1] = 0.19 + 0.15 * ring
    base[..., 2] = 0.13 + 0.10 * ring
    rough = 0.38 + 0.30 * (1 - ring)
    height = 0.28 * ring + 0.06 * rng.standard_normal((size, size))
    gy, gx = np.gradient(height)
    normal = np.dstack((-gx * 6.0, -gy * 6.0, np.ones_like(gx)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    normal = normal * 0.5 + 0.5
    return (np.clip(base, 0, 1) * 255).astype(np.uint8), \
        (np.clip(rough, 0, 1) * 255).astype(np.uint8), \
        (np.clip(normal, 0, 1) * 255).astype(np.uint8)


def save_image(name, rgb, path):
    import packgen
    if rgb.ndim == 2:
        rgb = np.dstack([rgb, rgb, rgb])
    with open(path, "wb") as fh:
        fh.write(packgen.encode_png(rgb))
    img = bpy.data.images.load(path)
    img.name = name
    img.pack()
    return img


def textured_material(name, images, rough_value=0.45):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough_value
    base, rough, normal = images
    tb = nt.nodes.new("ShaderNodeTexImage"); tb.image = base; tb.location = (-500, 320)
    tr = nt.nodes.new("ShaderNodeTexImage"); tr.image = rough; tr.location = (-500, 60)
    tr.image.colorspace_settings.name = 'Non-Color'
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = normal; tn.location = (-500, -200)
    tn.image.colorspace_settings.name = 'Non-Color'
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-220, -200)
    nt.links.new(tb.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tr.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def metal_material(name, colour=(0.66, 0.67, 0.70), rough=0.28):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    return mat


# --------------------------------------------------------------------------
def build_carcass(wood):
    parts = []
    half = W / 2
    top_z0 = H - T
    parts.append(box("carcass_left", (-half + T / 2, 0, (top_z0 + PLINTH) / 2),
                     (T, D, top_z0 - PLINTH)))
    parts.append(box("carcass_right", (half - T / 2, 0, (top_z0 + PLINTH) / 2),
                     (T, D, top_z0 - PLINTH)))
    parts.append(box("carcass_top", (0, 0, H - T / 2), (W, D, T)))
    parts.append(box("carcass_bottom", (0, 0, PLINTH + T / 2), (W, D, T)))
    parts.append(box("carcass_back", (0, -D / 2 + T / 2, (top_z0 + PLINTH) / 2),
                     (W, T, top_z0 - PLINTH)))
    parts.append(box("carcass_divider", (0, 0, (top_z0 + PLINTH) / 2), (T, D - T, top_z0 - PLINTH)))
    for ob in parts:
        ob.data.materials.append(wood)
    return parts


def build_drawer(index, wood, metal):
    z0 = BAY_Z0 + (index - 1) * BAY_H
    zc = z0 + BAY_H / 2
    x_lo, x_hi = -0.480 + T, -0.020 - 0.0
    width = DRAWER_W
    front = box(f"drawer_{index:02d}_front", ((x_lo + x_hi) / 2, FRONT_Y - T / 2 + 0.0005, zc),
                (width, T, BAY_H - 0.010))
    side_l = box(f"drawer_{index:02d}_side_l", (x_lo + T / 2, FRONT_Y - T - TRAY_D / 2, zc),
                 (T, TRAY_D, BAY_H - 0.030))
    side_r = box(f"drawer_{index:02d}_side_r", (x_hi - T / 2, FRONT_Y - T - TRAY_D / 2, zc),
                 (T, TRAY_D, BAY_H - 0.030))
    back = box(f"drawer_{index:02d}_back", ((x_lo + x_hi) / 2, FRONT_Y - T - TRAY_D + T / 2, zc),
               (width - 2 * T, T, BAY_H - 0.030))
    bottom = box(f"drawer_{index:02d}_bottom", ((x_lo + x_hi) / 2, FRONT_Y - T - TRAY_D / 2,
                                                zc - BAY_H / 2 + 0.030),
                 (width - 2 * T, TRAY_D, T))
    handle = cylinder(f"handle_{index:02d}",
                      ((x_lo + x_hi) / 2, FRONT_Y + 0.014, zc), 0.007, 0.320, axis='X', segments=16)
    for ob in (front, side_l, side_r, back, bottom):
        ob.data.materials.append(wood)
    handle.data.materials.append(metal)
    drawer = join([front, side_l, side_r, back, bottom, handle], f"drawer_{index:02d}")
    return drawer


def build_door(wood, metal):
    hinge = bpy.data.objects.new("hinge_right", None)
    hinge.empty_display_type = 'SINGLE_ARROW'
    hinge.location = (HINGE_X, FRONT_Y + 0.0015, DOOR_HINGE_Z)
    link(hinge)
    door = box("door_right", (HINGE_X - DOOR_W / 2, DOOR_Y, DOOR_HINGE_Z),
               (DOOR_W, T, DOOR_Z1 - DOOR_Z0 - 0.004))
    door.data.materials.append(wood)
    handle = cylinder("handle_door", (HINGE_X - DOOR_W + 0.030, FRONT_Y + 0.014, DOOR_HINGE_Z),
                      0.007, 0.180, axis='Z', segments=16)
    handle.data.materials.append(metal)
    door = join([door, handle], "door_right")
    door.parent = hinge
    door.matrix_parent_inverse = hinge.matrix_world.inverted()
    return hinge, door


def build_feet(metal):
    feet = []
    for x in (-W / 2 + 0.060, W / 2 - 0.060):
        for y in (-D / 2 + 0.060, D / 2 - 0.060):
            f = cylinder(f"foot_{len(feet) + 1}", (x, y, PLINTH / 2), 0.022, PLINTH, segments=20)
            f.data.materials.append(metal)
            feet.append(f)
    return feet


def build_stage(day_collection, night_collection):
    ground = box("ground", (0, 0, -0.005), (3.0, 3.0, 0.010), bevel=0.0)
    gmat = bpy.data.materials.new("mat_ground")
    gmat.use_nodes = True
    g = gmat.node_tree.nodes["Principled BSDF"]
    g.inputs["Base Color"].default_value = (0.16, 0.16, 0.17, 1)
    g.inputs["Roughness"].default_value = 0.7
    ground.data.materials.append(gmat)

    def area(name, collection, loc, energy, size, colour, target=(0, 0, 0.45)):
        lamp = bpy.data.lights.new(name, 'AREA')
        lamp.energy = energy
        lamp.size = size
        lamp.color = colour
        o = bpy.data.objects.new(name, lamp)
        o.location = loc
        d = Vector(target) - o.location
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        collection.objects.link(o)
        return o

    day_collection = bpy.data.collections.new("light_day")
    night_collection = bpy.data.collections.new("light_night")
    bpy.context.scene.collection.children.link(day_collection)
    bpy.context.scene.collection.children.link(night_collection)
    area("light_key", day_collection, (1.1, 1.4, 1.6), 120.0, 1.2, (1.0, 0.97, 0.92))
    area("light_fill", day_collection, (-1.3, 1.0, 0.9), 45.0, 1.5, (0.86, 0.91, 1.0))
    area("light_rim", day_collection, (0.2, -1.2, 1.3), 55.0, 1.0, (1.0, 0.95, 0.88))
    area("light_night_key", night_collection, (0.55, 1.1, 1.25), 22.0, 0.6, (1.0, 0.72, 0.42))
    area("light_night_spot", night_collection, (-0.6, 1.0, 0.7), 8.0, 0.5, (0.55, 0.66, 1.0))

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

    camera("cam_front34", (1.15, 1.05, 1.15), (0, 0, 0.45), 35.0)
    camera("cam_detail", (0.02, 1.02, 0.66), (-0.24, 0.46, 0.355), 50.0)


def set_state(drawers, slides, hinge, open_drawer=None, amount=0.0, door_deg=0.0):
    for slide in slides:
        slide.location.y = 0.0
    if open_drawer is not None:
        slides[open_drawer - 1].location.y = amount
    hinge.rotation_euler = (0.0, 0.0, -math.radians(door_deg))
    bpy.context.view_layer.update()


def set_lights(day, night, day_on, night_on):
    for collection, on in ((day, day_on), (night, night_on)):
        collection.hide_render = not on
        for ob in collection.objects:
            ob.hide_render = not on


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
    base, rough, normal = wood_maps()
    imgs = (
        save_image("wood_basecolor", base, os.path.join(OUT, "textures", "wood_basecolor.png")),
        save_image("wood_roughness", rough, os.path.join(OUT, "textures", "wood_roughness.png")),
        save_image("wood_normal", normal, os.path.join(OUT, "textures", "wood_normal.png")),
    )
    wood = textured_material("mat_wood", imgs)
    metal = metal_material("mat_metal")

    build_carcass(wood)
    slides, drawers = [], []
    for i in range(1, 6):
        drawer = build_drawer(i, wood, metal)
        slide = bpy.data.objects.new(f"slide_{i:02d}", None)
        slide.empty_display_type = 'ARROWS'
        slide.location = (0, 0, 0)
        link(slide)
        drawer.parent = slide
        drawer.matrix_parent_inverse = slide.matrix_world.inverted()
        slides.append(slide)
        drawers.append(drawer)
    hinge, door = build_door(wood, metal)
    build_feet(metal)
    build_stage(None, None)

    sc = bpy.context.scene
    day = bpy.data.collections["light_day"]
    night = bpy.data.collections["light_night"]

    # Canonical delivered states: day and night closed, detail with drawer 02
    # pulled 300 mm. The verifier rebuilds exactly these three poses.
    set_state(drawers, slides, hinge, open_drawer=2, amount=0.300)
    set_lights(day, night, True, False)
    render("cam_detail", os.path.join(OUT, "render_detail.png"), 1600, 1200)

    set_state(drawers, slides, hinge)
    render("cam_front34", os.path.join(OUT, "render_day.png"), 1600, 1200)
    set_lights(day, night, False, True)
    render("cam_front34", os.path.join(OUT, "render_night.png"), 1600, 1200)

    set_lights(day, night, True, True)
    set_state(drawers, slides, hinge)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "drawer_cabinet.blend"))
    log("saved")

    manifest = {
        "schemaVersion": 1,
        "units": "meters",
        "blenderVersion": bpy.app.version_string,
        "assets": [
            {"path": "textures/wood_basecolor.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
            {"path": "textures/wood_roughness.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
            {"path": "textures/wood_normal.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
        ],
        "renders": [
            {"file": "render_day.png", "camera": "cam_front34", "resolution": [1600, 1200], "samples": 64},
            {"file": "render_night.png", "camera": "cam_front34", "resolution": [1600, 1200], "samples": 64},
            {"file": "render_detail.png", "camera": "cam_detail", "resolution": [1600, 1200], "samples": 64},
        ],
    }
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    log("done")


if __name__ == "__main__":
    main()
