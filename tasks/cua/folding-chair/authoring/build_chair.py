"""Authoring tool: builds the reference folding chair + fold animation.

    blender -b -P build_chair.py -- <out_dir> <materials_dir>

Mechanism: each side is a scissor pair of legs pinned at a real hinge. The
bars' origins sit on the hinge axis, so rotating either bar about the hinge
keeps their joint coincident; both bars are parented to the hinge empty. The
seat is hinged to the top of the left scissor bar, and the back is hinged to
the rear edge of the seat, so the whole chair folds flat.
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector, Matrix

W, D, H = 0.62, 0.58, 0.82
SEAT_Z = 0.45
BAR_T = 0.03
PANEL_T = 0.02
HINGE_Z = 0.225
BAR_LEN = math.hypot(D, 2 * HINGE_Z)          # floor to seat-underside diagonal
ALPHA = math.atan2(D, 2 * HINGE_Z)            # angle from vertical, radians


def log(*a):
    print("[chair]", *a, flush=True)


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
    sc.view_settings.view_transform = 'AgX'
    sc.render.fps = 24
    sc.frame_start = 0
    sc.frame_end = 60


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


def parent_keep(ob, parent):
    """Parent without moving the object in world space."""
    bpy.context.view_layer.update()
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()


def bar(name, hinge, angle, length):
    """Leg bar whose midpoint (the pivot) sits on the hinge axis."""
    ob = box(name, (0, 0, 0), (BAR_T, BAR_T, length), 0.002)
    ob.data.transform(Matrix.Rotation(angle, 4, 'X'))
    ob.location = hinge.location.copy()
    parent_keep(ob, hinge)
    return ob


def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'ARROWS'
    e.empty_display_size = 0.06
    e.location = loc
    bpy.context.collection.objects.link(e)
    if parent is not None:
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
    root = empty("chair_root", (0, 0, 0))
    hinges, bars = {}, {}
    for side, x in (("l", -W / 2 + BAR_T / 2), ("r", W / 2 - BAR_T / 2)):
        h = empty(f"hinge_0{1 if side == 'l' else 2}", (x, 0.0, HINGE_Z), root)
        hinges[side] = h
        a = bar(f"lower_leg_{side}_a", h, -ALPHA, BAR_LEN)
        b = bar(f"lower_leg_{side}_b", h, +ALPHA, BAR_LEN)
        bars[side] = (a, b)

    # seat: 0.62 x 0.58, top at 0.45; pivots at its rear edge on bar A's top
    seat = box("seat", (0, 0, SEAT_Z - PANEL_T / 2), (W - 0.02, D, PANEL_T), 0.003)
    hinge3 = empty("hinge_03", (-W / 2 + BAR_T / 2, D / 2, SEAT_Z - PANEL_T), bars["l"][0])
    parent_keep(seat, hinge3)

    # back: stands on the seat's rear edge, pivots there
    back = box("back", (0, 0, 0), (W - 0.02, PANEL_T, H - SEAT_Z - 0.02), 0.003)
    back.location = (0, D / 2 - PANEL_T / 2, (SEAT_Z + H) / 2 - 0.01)
    hinge4 = empty("hinge_04", (0, D / 2, SEAT_Z + PANEL_T + 0.005), seat)
    parent_keep(back, hinge4)

    # lock pin: only shown in the locked state
    pin = box("lock_pin", (-W / 2 + BAR_T / 2, D / 2 - 0.06, SEAT_Z + 0.02),
              (0.02, 0.02, 0.1), 0.002)
    parent_keep(pin, hinge3)

    mat_oak = material("mat_oak", (0.30, 0.22, 0.14, 1), 0.55)
    mat_steel = material("mat_steel", (0.35, 0.36, 0.38, 1), 0.35, 1.0)
    for ob in [*bars["l"], *bars["r"]]:
        ob.data.materials.append(mat_steel)
    for ob in (seat, back):
        ob.data.materials.append(mat_oak)
    pin.data.materials.append(mat_steel)

    return root, hinges, bars, seat, back, hinge3, hinge4, pin


def animate(hinges, bars, seat, back, hinge3, hinge4, pin):
    sc = bpy.context.scene
    for side, (a, b) in bars.items():
        a.rotation_mode = b.rotation_mode = 'XYZ'
    hinge3.rotation_mode = 'XYZ'
    hinge4.rotation_mode = 'XYZ'

    def key(frame, bar_rot, seat_target, back_rel):
        """bar_rot folds the legs; seat_target is the seat's world pitch;
        back_rel is the back's rotation relative to the seat."""
        sc.frame_set(frame)
        for side, (a, b) in bars.items():
            a.rotation_euler = (+bar_rot, 0, 0)
            b.rotation_euler = (-bar_rot, 0, 0)
            a.keyframe_insert("rotation_euler", frame=frame)
            b.keyframe_insert("rotation_euler", frame=frame)
        hinge3.rotation_euler = (seat_target - bar_rot, 0, 0)
        hinge3.keyframe_insert("rotation_euler", frame=frame)
        hinge4.rotation_euler = (back_rel, 0, 0)
        hinge4.keyframe_insert("rotation_euler", frame=frame)

    key(0, 0.0, 0.0, 0.0)
    key(20, ALPHA * 0.5, math.radians(-45), math.radians(45))
    key(40, ALPHA, math.radians(-80), math.radians(85))
    key(60, ALPHA, math.radians(-90), math.radians(90))
    sc.frame_set(0)

    for f, hidden in ((0, False), (1, True), (59, True), (60, True)):
        sc.frame_set(f)
        pin.hide_render = hidden
        pin.keyframe_insert("hide_render", frame=f)
    sc.frame_set(0)


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def build_stage():
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.05, 0.05, 0.055, 1)
    bg.inputs["Strength"].default_value = 0.4

    # floor
    floor = box("stage_floor", (0, 0, -0.31), (3, 3, 0.02))
    floor.data.materials.append(material("mat_floor", (0.18, 0.18, 0.19, 1), 0.6))

    for name, loc, power, size in (("key", (1.2, -1.4, 1.8), 250, 1.2),
                                   ("fill", (-1.4, -0.6, 1.0), 80, 1.6),
                                   ("rim", (0.2, 1.6, 1.6), 120, 1.0)):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = power
        ld.size = size
        ob = bpy.data.objects.new("light_" + name, ld)
        ob.location = loc
        look_at(ob, (0, 0, 0.4))
        bpy.context.collection.objects.link(ob)


def cameras():
    cd = bpy.data.cameras.new("cam_states")
    cd.lens = 50
    cam = bpy.data.objects.new("cam_states", cd)
    cam.location = (1.9, -2.1, 1.25)
    bpy.context.collection.objects.link(cam)
    look_at(cam, (0, 0, 0.42))
    bpy.context.scene.camera = cam
    return cam


def render_states(out_dir):
    sc = bpy.context.scene
    sc.render.resolution_x = 1200
    sc.render.resolution_y = 1200
    sc.render.resolution_percentage = 100
    for fname, frame in (("render_unfolded", 0), ("render_half", 20),
                         ("render_folded", 60), ("render_locked", 0)):
        sc.frame_set(frame)
        if fname == "render_locked":
            bpy.data.objects["lock_pin"].hide_render = False
        else:
            bpy.data.objects["lock_pin"].hide_render = (fname != "render_locked")
        sc.render.filepath = os.path.join(out_dir, fname + ".png")
        bpy.ops.render.render(write_still=True)
        log("rendered", fname)
    sc.frame_set(0)


def write_manifest(out_dir):
    import json
    man = {
        "schemaVersion": 1,
        "units": "meters",
        "blenderVersion": bpy.app.version_string,
        "assets": [
            {"path": "textures/oak_basecolor.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
            {"path": "textures/steel_basecolor.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
        ],
        "renders": [
            {"file": f + ".png", "camera": "cam_states", "resolution": [1200, 1200],
             "samples": 64}
            for f in ("render_unfolded", "render_half", "render_folded", "render_locked")
        ],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=2)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_dir = argv[0]
    os.makedirs(out_dir, exist_ok=True)
    reset_scene()
    root, hinges, bars, seat, back, hinge3, hinge4, pin = build()
    build_stage()
    cameras()
    animate(hinges, bars, seat, back, hinge3, hinge4, pin)
    render_states(out_dir)
    write_manifest(out_dir)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "folding_chair.blend"),
                                compress=True)
    log("saved")


if __name__ == "__main__":
    main()
