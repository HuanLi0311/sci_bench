"""Authoring tool: builds the reference skateboard scene, GLB and renders.

Run with Blender 4.2.3:
    blender -b -P build_skateboard.py -- <solution_dir> <materials_dir>

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

OUT = sys.argv[sys.argv.index("--") + 1]
MATERIALS = sys.argv[sys.argv.index("--") + 2]

DECK_L = 0.800
DECK_W = 0.200
DECK_T = 0.012
X0, X1 = -0.180, 0.620
DECK_Z = 0.030           # underside of the flat centre
KICK_DEG = 20.0
KICK_LEN = 0.130
CONCAVE = 0.008
WHEELBASE = 0.440
WHEEL_R = 0.027
WHEEL_W = 0.032
AXLE_LEN = 0.180
TRUCK_H = 0.030

PLY_COLOURS = [
    (0.74, 0.60, 0.40), (0.40, 0.27, 0.16), (0.68, 0.52, 0.32),
    (0.30, 0.20, 0.12), (0.72, 0.57, 0.37), (0.45, 0.31, 0.19),
    (0.63, 0.47, 0.28),
]


def log(*a):
    print("[deck]", *a, flush=True)


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
    sc.render.fps = 24
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.035, 0.037, 0.04, 1.0)
    bg.inputs[1].default_value = 0.6
    sc.world = world


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def principled(mat):
    return mat.node_tree.nodes["Principled BSDF"]


def plain(name, colour, rough=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = principled(mat)
    b.inputs["Base Color"].default_value = (*colour, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    return mat


def image_material(name, path, rough=0.4):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = principled(mat)
    b.inputs["Roughness"].default_value = rough
    img = bpy.data.images.load(path)
    img.name = "deck_graphic"
    img.pack()
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = 'Linear'
    mat.node_tree.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    return mat


# --------------------------------------------------------------------------
def kick(x):
    d = max(0.0, (-0.050) - x, x - 0.490)
    if d <= 0.0:
        return 0.0
    # ease the first 15 mm so the bend is not a hard crease
    t = min(1.0, d / 0.015)
    eased = d - 0.015 * (1.0 - t * t * (3 - 2 * t)) * 0.5
    return math.tan(math.radians(KICK_DEG)) * max(0.0, eased)


def concave(y):
    return CONCAVE * (y / (DECK_W / 2)) ** 2


def deck_z(x, y):
    return DECK_Z + kick(x) + concave(y)


def build_deck(graphic):
    nx, ny = 96, 24
    xs = np.linspace(X0, X1, nx + 1)
    ys = np.linspace(-DECK_W / 2, DECK_W / 2, ny + 1)
    verts = []
    top_idx = np.zeros((nx + 1, ny + 1), dtype=int)
    bot_idx = np.zeros((nx + 1, ny + 1), dtype=int)
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            z = deck_z(x, y)
            top_idx[i, j] = len(verts)
            verts.append((x, y, z + DECK_T))
            bot_idx[i, j] = len(verts)
            verts.append((x, y, z))
    faces = []
    mats = []
    uv_faces = []

    grip = bpy.data.materials.new("mat_grip")
    grip.use_nodes = True
    gb = principled(grip)
    gb.inputs["Base Color"].default_value = (0.045, 0.045, 0.05, 1)
    gb.inputs["Roughness"].default_value = 0.95
    noise = grip.node_tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 320.0
    noise.inputs["Detail"].default_value = 6.0
    bump = grip.node_tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.45
    grip.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    grip.node_tree.links.new(bump.outputs["Normal"], gb.inputs["Normal"])

    plies = [plain(f"mat_ply_{k + 1}", c, 0.55) for k, c in enumerate(PLY_COLOURS)]
    mats = [grip, graphic] + plies

    def add_face(indices, mat, uv=None):
        faces.append(tuple(indices))
        uv_faces.append(uv)

    # top (grip) and bottom (graphic) grids
    for i in range(nx):
        for j in range(ny):
            add_face([top_idx[i, j], top_idx[i + 1, j], top_idx[i + 1, j + 1], top_idx[i, j + 1]], 0)
            add_face([bot_idx[i, j], bot_idx[i, j + 1], bot_idx[i + 1, j + 1], bot_idx[i + 1, j]], 1,
                     [(xs[i], ys[j]), (xs[i], ys[j + 1]), (xs[i + 1], ys[j + 1]), (xs[i + 1], ys[j])])

    # side walls, seven ply bands per side, plus end caps
    for i in range(nx):
        for side, j in ((0, 0), (1, ny)):
            for k in range(7):
                z0a = deck_z(xs[i], ys[j]) + DECK_T * k / 7
                z1a = deck_z(xs[i], ys[j]) + DECK_T * (k + 1) / 7
                z0b = deck_z(xs[i + 1], ys[j]) + DECK_T * k / 7
                z1b = deck_z(xs[i + 1], ys[j]) + DECK_T * (k + 1) / 7
                base = len(verts)
                y = ys[j]
                if side == 0:
                    verts.extend([(xs[i], y, z0a), (xs[i], y, z1a),
                                  (xs[i + 1], y, z1b), (xs[i + 1], y, z0b)])
                else:
                    verts.extend([(xs[i], y, z0a), (xs[i + 1], y, z0b),
                                  (xs[i + 1], y, z1b), (xs[i], y, z1a)])
                add_face([base, base + 1, base + 2, base + 3], 2 + k)

    for end, i in ((0, 0), (1, nx)):
        base = len(verts)
        for j in range(ny + 1):
            y = ys[j]
            verts.append((xs[i], y, deck_z(xs[i], y)))
            verts.append((xs[i], y, deck_z(xs[i], y) + DECK_T))
        for j in range(ny):
            add_face([base + 2 * j, base + 2 * j + 1, base + 2 * j + 3, base + 2 * j + 2], 5)

    me = bpy.data.meshes.new("deck")
    me.from_pydata(verts, [], faces)
    me.validate()
    for mat in mats:
        me.materials.append(mat)
    for poly, uv in zip(me.polygons, uv_faces):
        poly.material_index = 0
    # material index assignment: rebuild by face order convention
    idx = 0
    nxny = nx * ny
    for i in range(nx):
        for j in range(ny):
            me.polygons[2 * (i * ny + j)].material_index = 0          # top grip
            me.polygons[2 * (i * ny + j) + 1].material_index = 1      # bottom graphic
    offset = 2 * nxny
    sides = []
    for i in range(nx):
        for k in range(7):
            sides.append((offset, 2 + k))
            offset += 1
        for k in range(7):
            sides.append((offset, 2 + k))
            offset += 1
    for poly_index, mat_index in sides:
        me.polygons[poly_index].material_index = mat_index
    for poly_index in range(offset, len(me.polygons)):
        me.polygons[poly_index].material_index = 5

    uv_layer = me.uv_layers.new(name="UVMap")
    for poly, uv in zip(me.polygons, uv_faces):
        if uv is None:
            for li in poly.loop_indices:
                vert = me.vertices[me.loops[li].vertex_index].co
                uv_layer.data[li].uv = ((vert.x - X0) / DECK_L, (vert.y + DECK_W / 2) / DECK_W)
        else:
            for li, (x, y) in zip(poly.loop_indices, uv):
                # The graphic is printed on the underside: flip U so the wordmark
                # reads correctly when the board is seen from below.
                uv_layer.data[li].uv = (1.0 - (x - X0) / DECK_L, (y + DECK_W / 2) / DECK_W)

    ob = bpy.data.objects.new("deck", me)
    link(ob)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    return ob


def cylinder(name, centre, radius, depth, axis='Y', segments=32, bevel=0.0):
    ob = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    link(ob)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius, depth=depth)
    if axis == 'Y':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    elif axis == 'X':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(90), 3, 'Y'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(centre))
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2,
                        affect='EDGES', clamp_overlap=True)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def box(name, centre, dims, bevel=0.002):
    ob = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    link(ob)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2,
                        affect='EDGES', clamp_overlap=True)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(centre))
    bm.to_mesh(ob.data)
    bm.free()
    return ob


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


def build_trucks(aluminium):
    trucks = []
    for tag, x in (("front", WHEELBASE), ("rear", 0.0)):
        plate = box(f"truck_{tag}_plate", (x, 0, DECK_Z - 0.003), (0.090, 0.060, 0.006))
        hanger = box(f"truck_{tag}_hanger", (x, 0, 0.012), (0.052, 0.055, 0.024), bevel=0.004)
        axle = cylinder(f"truck_{tag}_axle", (x, 0, 0.0), 0.004, AXLE_LEN, axis='Y', segments=24)
        truck = join([plate, hanger, axle], f"truck_{tag}")
        truck.data.materials.clear()
        truck.data.materials.append(aluminium)
        trucks.append(truck)
    return trucks


def build_wheels(wheel_mat, steel):
    wheels = []
    positions = [(WHEELBASE, -0.074, "01"), (WHEELBASE, 0.074, "02"),
                 (0.0, -0.074, "03"), (0.0, 0.074, "04")]
    for x, y, tag in positions:
        tyre = cylinder(f"wheel_{tag}", (x, y, 0.0), WHEEL_R, WHEEL_W, axis='Y', segments=40, bevel=0.004)
        tyre.data.materials.append(wheel_mat)
        wheels.append(tyre)
    bearings = []
    for x in (0.0, WHEELBASE):
        for y in (-0.074, 0.074):
            for side in (-1, 1):
                b = cylinder(f"bearing_tmp_{len(bearings)}",
                             (x, y + side * (WHEEL_W / 2 - 0.004), 0.0),
                             0.011, 0.006, axis='Y', segments=20)
                bearings.append(b)
    bearing_ob = join(bearings, "bearings")
    bearing_ob.data.materials.clear()
    bearing_ob.data.materials.append(steel)
    return wheels, bearing_ob


def build_stage():
    def area(name, loc, energy, size, colour=(1, 1, 1), target=(0.22, 0, 0.03)):
        lamp = bpy.data.lights.new(name, 'AREA')
        lamp.energy = energy
        lamp.size = size
        lamp.color = colour
        o = bpy.data.objects.new(name, lamp)
        o.location = loc
        d = Vector(target) - o.location
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        return link(o)

    area("light_key", (0.9, -0.7, 1.1), 140.0, 1.2, (1.0, 0.97, 0.92))
    area("light_fill", (-0.5, -0.9, 0.5), 45.0, 1.4, (0.85, 0.9, 1.0))
    area("light_rim", (0.1, 0.9, 0.7), 70.0, 1.0, (1.0, 0.95, 0.88))
    area("light_top", (0.22, 0.0, 1.4), 60.0, 0.8, (1.0, 1.0, 1.0))
    area("light_bounce", (0.22, 0.0, -0.45), 45.0, 1.0, (1.0, 0.94, 0.86),
         target=(0.22, 0.0, 0.02))

    def camera(name, loc, target, lens):
        cam = bpy.data.cameras.new(name)
        cam.lens = lens
        o = link(bpy.data.objects.new(name, cam))
        o.location = loc
        d = Vector(target) - Vector(loc)
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        return o

    camera("cam_three_quarter", (1.12, -0.786, 0.8), (0.22, 0.0, 0.045), 35.0)
    cam_bottom = bpy.data.cameras.new("cam_bottom")
    cam_bottom.type = 'ORTHO'
    cam_bottom.ortho_scale = 0.90
    cb = link(bpy.data.objects.new("cam_bottom", cam_bottom))
    cb.location = (0.22, 0.0, -0.5)
    cb.rotation_euler = (math.pi, 0, 0)   # look up the +Z axis
    camera("cam_edge", (0.22, 0.35, 0.065), (0.22, 0.1, 0.037), 100.0)


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
    reset_scene()
    graphic = image_material("mat_deck_graphic", os.path.join(MATERIALS, "spec", "deck_graphic.png"))
    aluminium = plain("mat_aluminium", (0.72, 0.73, 0.75), 0.34, 0.9)
    wheel = plain("mat_pu_wheel", (0.86, 0.82, 0.70), 0.65, 0.0)
    steel = plain("mat_steel", (0.62, 0.62, 0.65), 0.25, 1.0)

    deck = build_deck(graphic)
    trucks = build_trucks(aluminium)
    wheels, bearings = build_wheels(wheel, steel)
    build_stage()

    bpy.context.view_layer.objects.active = deck
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "skateboard.blend"))

    # export only the board
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [deck, bearings] + trucks + wheels:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = deck
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "skateboard.glb"),
                              export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True,
                              export_cameras=False, export_lights=False)
    log("exported glb")

    render("cam_three_quarter", os.path.join(OUT, "render_three_quarter.png"), 1600, 1200)
    render("cam_bottom", os.path.join(OUT, "render_bottom.png"), 1600, 900)
    render("cam_edge", os.path.join(OUT, "render_edge.png"), 1600, 1200)

    manifest = {
        "schemaVersion": 1,
        "units": "meters",
        "blenderVersion": bpy.app.version_string,
        "assets": [
            {"path": "spec/deck_graphic.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
        ],
        "renders": [
            {"file": "render_three_quarter.png", "camera": "cam_three_quarter",
             "resolution": [1600, 1200], "samples": 64},
            {"file": "render_bottom.png", "camera": "cam_bottom",
             "resolution": [1600, 900], "samples": 64},
            {"file": "render_edge.png", "camera": "cam_edge",
             "resolution": [1600, 1200], "samples": 64},
        ],
    }
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    log("done", len(deck.data.polygons))


if __name__ == "__main__":
    main()
