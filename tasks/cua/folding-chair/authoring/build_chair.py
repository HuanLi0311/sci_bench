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


def bar(name, hinge_pos, angle, length, x):
    """A leg bar whose origin is on the hinge axis."""
    ob = box(name, (0, 0, 0), (BAR_T, BAR_T, length), 0.002)
    ob.data.transform(Matrix.Rotation(angle, 4, 'X'))
    ob.location = (x, hinge_pos[0], hinge_pos[1])
    return ob


def empty(name, loc):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'ARROWS'
    e.empty_display_size = 0.06
    e.location = loc
    bpy.context.collection.objects.link(e)
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
    hinges = {}
    bars = {}
    for side, x in (("l", -W / 2 + BAR_T / 2), ("r", W / 2 - BAR_T / 2)):
        h = empty(f"hinge_0{1 if side == 'l' else 2}", (x, 0.0, HINGE_Z))
        h.parent = root
        hinges[side] = h
        # bar A leans back, bar B leans forward; both pivot on the hinge axis
        a = bar(f"lower_leg_{side}_a", (0.0, HINGE_Z), +ALPHA, BAR_LEN, x)
        b = bar(f"lower_leg_{side}_b", (0.0, HINGE_Z), -ALPHA, BAR_LEN, x)
        for ob in (a, b):
            ob.parent = h
            ob.matrix_parent_inverse = Matrix.Identity(4)
            ob.location = (x, 0.0, HINGE_Z)
        bars[side] = (a, b)

    # seat: 0.58 x 0.62, top at 0.45, hinged to bar A's top on the left side
    seat = box("seat", (0, 0, SEAT_Z - PANEL_T / 2), (W - 0.02, D, PANEL_T), 0.003)
    hinge3 = empty("hinge_03", (-W / 2 + BAR_T / 2, D / 2, SEAT_Z - PANEL_T / 2))
    hinge3.parent = bars["l"][0]
    hinge3.location = (-W / 2 + BAR_T / 2, D / 2, 0.0)
    hinge3.rotation_mode = 'XYZ'
    seat.parent = hinge3
    seat.location = (W / 2 - BAR_T / 2, -D / 2, 0.0)

    # back: hinged at the seat's rear edge
    back = box("back", (0, 0, 0), (W - 0.02, PANEL_T, H - SEAT_Z - 0.02), 0.003)
    hinge4 = empty("hinge_04", (0, D / 2, SEAT_Z))
    hinge4.parent = seat
    hinge4.location = (0, D / 2, PANEL_T / 2)
    back.parent = hinge4
    back.location = (0, 0, (H - SEAT_Z) / 2)

    # lock pin, only visible in the locked state
    pin = box("lock_pin", (-W / 2 + BAR_T / 2, D / 2 - 0.05, SEAT_Z + 0.03),
              (0.02, 0.02, 0.12), 0.002)
    pin.parent = hinge3
    pin.location = (0, -0.05, 0.03)

    for ob in [*bars["l"], *bars["r"], seat, back, pin]:
        ob.data.materials.append(
            material("mat_oak", (0.30, 0.22, 0.14, 1), 0.55) if ob in (seat, back)
            else material("mat_steel", (0.35, 0.36, 0.38, 1), 0.35, 1.0))

    return root, hinges, bars, seat, back, hinge3, hinge4, pin


def animate(hinges, bars, seat, back, hinge3, hinge4, pin):
    """Frame 0 unfolded, 60 folded; hinges carry the rotation."""
    sc = bpy.context.scene
    for side, h in hinges.items():
        h.rotation_mode = 'XYZ'
    # quaternions per bar (their own origins are on the hinge axis)
    for side, (a, b) in bars.items():
        a.rotation_mode = b.rotation_mode = 'XYZ'
    hinge3.rotation_mode = 'XYZ'
    hinge4.rotation_mode = 'XYZ'

    def key(frame, bar_rot, seat_rot, back_rot, pin_hide):
        sc.frame_set(frame)
        for side, (a, b) in bars.items():
            a.rotation_euler = (bar_rot, 0, 0)
            b.rotation_euler = (-bar_rot, 0, 0)
            a.keyframe_insert("rotation_euler", frame=frame)
            b.keyframe_insert("rotation_euler", frame=frame)
        hinge3.rotation_euler = (seat_rot, 0, 0)
        hinge3.keyframe_insert("rotation_euler", frame=frame)
        hinge4.rotation_euler = (back_rot, 0, 0)
        hinge4.keyframe_insert("rotation_euler", frame=frame)

    # bar A leans +ALPHA; rotating it by -ALPHA makes it vertical, and bar B
    # needs +ALPHA. The seat swings up about its hinge, the back folds onto it.
    key(0, 0.0, 0.0, 0.0, False)
    key(20, -ALPHA * 0.5, math.radians(-45), math.radians(35), False)
    key(40, -ALPHA, math.radians(-80), math.radians(80), False)
    key(60, -ALPHA, math.radians(-90), math.radians(90), False)
    # pin hidden in every rendered state except the locked one (frame 0)
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
    floor = box("stage_floor", (0, 0, -0.01), (3, 3, 0.02))
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
